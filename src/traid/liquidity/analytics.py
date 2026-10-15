"""Snapshot-only liquidity formulas; never order execution or directional advice.

Bands are cumulative inclusive distances in bps from each side's best price.
Depth is displayed base quantity and quote notional, not full market liquidity.
HHI = sum((level quantity / band quantity)**2), dimensionless (0, 1].
Ring density = incremental base depth / incremental band width (base/bps).
Decay ratio = current ring density / previous ring density: <1 means decay;
this is a spatial ratio, not a time forecast. Zero previous density is undefined.
Slippage is adverse VWAP displacement from the consumed side's best price;
buy consumes asks, sell consumes bids. No fees, latency, replenishment or fills
are inferred. Partial VWAP describes only displayed filled quantity; full-size
slippage is unavailable when displayed liquidity is insufficient.

Arithmetic uses an independent 8192-digit ROUND_HALF_EVEN Decimal context
for bounded inputs (50 input digits, adjusted exponents +/-1000, at most
100000 levels). Reported metrics round once to 50 significant digits.
No tick-size quantization or exact-execution precision is claimed.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Context, Decimal, DecimalException, ROUND_HALF_EVEN, localcontext
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from traid.domain.models import CanonicalModel, DataQualityState, OrderBookSnapshot, SourceProvenance
from traid.exchange import Capability, CapabilityCoverage
from traid.quality import (
    ContinuityStatus, QualityAssessment, QualityPolicy, RecoveryStatus, assess_quality,
)

FORMULA_VERSION = "c07-liquidity-1"
CONTEXT = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
ZERO = Decimal(0)
BPS = Decimal(10000)
MAX_BANDS = 8
MAX_ORDERS = 16
UNIT_LIMITATION = "UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED"


def _bounded(value: Decimal) -> bool:
    return (value.is_finite() and len(value.as_tuple().digits) <= 50
            and (value == 0 or -1000 <= value.adjusted() <= 1000))


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderRequest(CanonicalModel):
    side: Side
    quantity: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def bounded(self):
        if not _bounded(self.quantity):
            raise ValueError("hypothetical quantity exceeds supported numeric range")
        return self


class LiquidityConfig(CanonicalModel):
    """Explicit units; symbol is an identifier, never a unit inference rule."""
    symbol: str  # Same canonical representation/validator as OrderBookSnapshot.
    base_asset: str = Field(min_length=1)
    quote_currency: str = Field(min_length=1)
    bands_bps: tuple[Decimal, ...] = Field(min_length=1, max_length=MAX_BANDS)
    orders: tuple[OrderRequest, ...] = Field(default=(), max_length=MAX_ORDERS)

    @field_validator("symbol", mode="before")
    @classmethod
    def symbol_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("canonical instrument identity must be a nonempty string")
        return value

    @model_validator(mode="after")
    def valid(self):
        if not self.base_asset.strip() or not self.quote_currency.strip():
            raise ValueError("units must be explicit")
        if not self.bands_bps or any(not _bounded(b) or not ZERO < b < BPS for b in self.bands_bps):
            raise ValueError("bands must be finite positive bps below 10000")
        if tuple(sorted(set(self.bands_bps))) != self.bands_bps:
            raise ValueError("bands must be unique and strictly increasing")
        return self


class Metric(CanonicalModel):
    value: Decimal | None
    unit: str
    reason: str | None = None

    @model_validator(mode="after")
    def explicit(self):
        if (self.value is None) != (self.reason is not None):
            raise ValueError("unavailable metric requires a reason; available metric cannot have one")
        if self.value is not None and not self.value.is_finite():
            raise ValueError("metric must be finite")
        return self


class BandMetrics(CanonicalModel):
    width_bps: Decimal
    bid_base: Metric
    ask_base: Metric
    bid_quote: Metric
    ask_quote: Metric
    imbalance: Metric
    bid_concentration_hhi: Metric
    ask_concentration_hhi: Metric
    bid_ring_density: Metric
    ask_ring_density: Metric
    bid_decay_ratio: Metric
    ask_decay_ratio: Metric


class ExecutionEstimate(CanonicalModel):
    request: OrderRequest
    hypothetical: bool = True
    reference_price: Metric
    displayed_filled_base: Metric
    displayed_quote: Metric
    partial_vwap: Metric
    full_size_slippage_absolute: Metric
    full_size_slippage_bps: Metric
    complete: bool
    reason: str | None


class LiquidityReport(CanonicalModel):
    formula_version: str = FORMULA_VERSION
    symbol: str
    snapshot_timestamp: datetime
    provenance: SourceProvenance
    quality: QualityAssessment
    config: LiquidityConfig
    # C05 observation trust does not attest financial-unit semantics.
    units_provider_verified: Literal[False] = False
    best_bid: Metric
    best_ask: Metric
    mid: Metric
    spread_absolute: Metric
    spread_bps: Metric
    bands: tuple[BandMetrics, ...]
    executions: tuple[ExecutionEstimate, ...]
    limitations: tuple[str, ...] = (
        UNIT_LIMITATION,
        "DISPLAYED_SNAPSHOT_ONLY_NO_COMPLETENESS_CLAIM",
        "HYPOTHETICAL_NO_FEES_LATENCY_REPLENISHMENT_OR_ACTUAL_FILL",
        "DECIMAL_8192_INTERMEDIATE_50_OUTPUT_HALF_EVEN_NO_TICK_PRECISION_CLAIM",
        "IMBALANCE_IS_NOT_DIRECTION_OR_PROBABILITY",
    )

    @model_validator(mode="after")
    def unit_disclosure(self):
        if UNIT_LIMITATION not in self.limitations:
            raise ValueError("caller-asserted unit limitation must remain explicit")
        return self


def analyze_book(
    book: OrderBookSnapshot, *, config: LiquidityConfig, coverage: CapabilityCoverage,
    evaluation_time: datetime, policy: QualityPolicy, continuity: ContinuityStatus,
    recovery: RecoveryStatus,
) -> LiquidityReport:
    """Reclassify C05 quality at explicit evaluation time; never trust a stale label.

    Invalid canonical construction raises at the typed boundary. Structurally
    valid but analytically invalid books return explicit unavailable metrics.
    Degraded observations retain the full C05 assessment and no numerical values.
    Canonical symbol equality binds the requested instrument, not quote/base
    semantics. Units remain caller assertions; units_provider_verified is always
    false even when C05 trusts the observation. No symbol parsing or conversion.
    Eight bands and sixteen independent hypothetical orders bound repeated
    snapshot scans; oversized configurations are rejected, never truncated.
    """
    if not isinstance(book, OrderBookSnapshot) or not isinstance(config, LiquidityConfig):
        raise ValueError("canonical book and LiquidityConfig required")
    # Revalidation also rejects model_construct/model_copy validation bypasses.
    book = OrderBookSnapshot.model_validate(book.model_dump())
    config = LiquidityConfig.model_validate(config.model_dump())
    if config.symbol != book.symbol:
        raise ValueError("INSTRUMENT_IDENTITY_MISMATCH")
    quality = assess_quality(
        capability=Capability.ORDER_BOOK, provenance=book.provenance, coverage=coverage,
        evaluation_time=evaluation_time, policy=policy, continuity=continuity,
        recovery=recovery, canonical_valid=True,
    )
    with localcontext(CONTEXT):
        try:
            return _analyze(book, config, quality)
        except DecimalException:
            return _analyze(book, config, quality, "NUMERIC_CALCULATION_UNAVAILABLE")


def _analyze(book, config, quality, numeric_failure=None):
    base, quote = config.base_asset, config.quote_currency
    price_unit = f"{quote}/{base}"
    reason = numeric_failure
    levels = book.bids + book.asks
    if reason is None:
        if len(levels) > 100000:
            reason = "BOOK_LEVEL_LIMIT_EXCEEDED"
        elif any(not _bounded(l.price) or not _bounded(l.quantity) for l in levels):
            reason = "NUMERIC_RANGE_UNSUPPORTED"
        elif any(l.quantity <= 0 for l in levels):
            reason = "NONPOSITIVE_LEVEL_SIZE"
        elif any(len({l.price for l in side}) != len(side) for side in (book.bids, book.asks)):
            reason = "DUPLICATE_PRICE_LEVEL"
        elif book.bids and book.asks and max(l.price for l in book.bids) >= min(l.price for l in book.asks):
            reason = "CROSSED_OR_LOCKED_BOOK"
        elif book.provenance.source_timestamp != book.timestamp:
            reason = "SNAPSHOT_SOURCE_TIMESTAMP_MISMATCH"
        elif not quality.trusted_for_current_use:
            reason = "QUALITY_NOT_TRUSTED:" + ",".join(quality.reasons)
    if reason and not reason.startswith("QUALITY_NOT_TRUSTED:"):
        facts = quality.model_dump()
        facts.update(state=DataQualityState.UNAVAILABLE, trusted_for_current_use=False,
                     reasons=quality.reasons + ("DATA_INVALID:" + reason,))
        quality = QualityAssessment.model_validate(facts)
    bids = sorted(book.bids, key=lambda l: l.price, reverse=True)
    asks = sorted(book.asks, key=lambda l: l.price)

    def metric(value, unit, unavailable=None):
        why = reason or unavailable
        with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)):
            return Metric(value=None if why else +value, unit=unit, reason=why)

    bid = bids[0].price if bids else None
    ask = asks[0].price if asks else None
    both_reason = None if bid is not None and ask is not None else "TWO_SIDED_BOOK_REQUIRED"
    # Do not perform arithmetic on inputs already classified as invalid.
    if reason:
        bid = ask = None
    mid = (bid + ask) / 2 if bid is not None and ask is not None else None
    spread = ask - bid if mid is not None else None
    bands = []
    previous = [ZERO, ZERO]
    band_quantities = [ZERO, ZERO]
    previous_density = [None, None]
    previous_width = ZERO
    for width in config.bands_bps:
        values = []
        for i, side in enumerate((bids, asks)):
            if reason or not side:
                why = reason or "SIDE_UNAVAILABLE"
                values.append([metric(None, u, why) for u in (base, quote, "1", f"{base}/bps", "1")])
                continue
            best = side[0].price
            selected = [l for l in side if abs(l.price - best) * BPS <= best * width]
            quantity = sum((l.quantity for l in selected), ZERO)
            notional = sum((l.price * l.quantity for l in selected), ZERO)
            hhi = sum(((l.quantity / quantity) ** 2 for l in selected), ZERO)
            density = (quantity - previous[i]) / (width - previous_width)
            prior = previous_density[i]
            decay_reason = "FIRST_BAND_NO_PREDECESSOR" if prior is None else "ZERO_PREVIOUS_DENSITY" if prior == 0 else None
            decay = density / prior if prior else None
            values.append([metric(quantity, base), metric(notional, quote), metric(hhi, "1"),
                           metric(density, f"{base}/bps"), metric(decay, "1", decay_reason)])
            previous[i], previous_density[i] = quantity, density
            band_quantities[i] = quantity
        b, a = values
        imbalance = None if reason or both_reason else (band_quantities[0] - band_quantities[1]) / (band_quantities[0] + band_quantities[1])
        bands.append(BandMetrics(width_bps=width, bid_base=b[0], ask_base=a[0], bid_quote=b[1], ask_quote=a[1],
                     imbalance=metric(imbalance, "1", both_reason), bid_concentration_hhi=b[2], ask_concentration_hhi=a[2],
                     bid_ring_density=b[3], ask_ring_density=a[3], bid_decay_ratio=b[4], ask_decay_ratio=a[4]))
        previous_width = width
    executions = []
    for request in config.orders:
        side = asks if request.side is Side.BUY else bids
        why = reason or ("SIDE_UNAVAILABLE" if not side else None)
        filled = cost = ZERO
        if not why:
            for level in side:
                take = min(request.quantity - filled, level.quantity)
                filled += take
                cost += take * level.price
                if filled == request.quantity:
                    break
        complete = not why and filled == request.quantity
        partial = cost / filled if filled else None
        full_reason = why or (None if complete else "INSUFFICIENT_DISPLAYED_DEPTH")
        displacement = None
        if complete:
            displacement = partial - side[0].price if request.side is Side.BUY else side[0].price - partial
        executions.append(ExecutionEstimate(
            request=request, reference_price=metric(side[0].price if side else None, price_unit, why),
            displayed_filled_base=metric(filled, base, why), displayed_quote=metric(cost, quote, why),
            partial_vwap=metric(partial, price_unit, why or ("NO_DISPLAYED_LIQUIDITY" if not filled else None)),
            full_size_slippage_absolute=metric(displacement, price_unit, full_reason),
            full_size_slippage_bps=metric(displacement / side[0].price * BPS if complete else None, "bps", full_reason),
            complete=bool(complete), reason=full_reason,
        ))
    return LiquidityReport(
        symbol=book.symbol, snapshot_timestamp=book.timestamp, provenance=book.provenance, quality=quality, config=config,
        best_bid=metric(bid, price_unit, None if bid is not None else "BID_UNAVAILABLE"),
        best_ask=metric(ask, price_unit, None if ask is not None else "ASK_UNAVAILABLE"),
        mid=metric(mid, price_unit, both_reason), spread_absolute=metric(spread, price_unit, both_reason),
        spread_bps=metric(spread / mid * BPS if mid is not None else None, "bps", both_reason),
        bands=tuple(bands), executions=tuple(executions),
    )
