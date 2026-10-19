"""Deterministic aggressor-side trade flow and CVD over canonical trades.

Units: every volume is in ``base_asset`` (displayed trade quantity); price is
used only for canonical validity. Buy = buy aggressor (taker bought), sell =
sell aggressor. Net delta = buy - sell. Side is provider-reported; it is never
inferred from price movement, and a trade without a side makes the report
unavailable.

Two aggregates are kept apart:
* window delta: trades with event time in [evaluation_time - window,
  evaluation_time], inclusive at both ends (rolling);
* session CVD: cumulative net delta over [session_start, evaluation_time],
  inclusive at both ends. ``session_start`` is an explicit caller input; nothing
  is carried across it and no hidden state or wall clock is used.

Identity: a trade is identified by ``(symbol, tid)`` where tid is
``provenance.source_id``. Hyperliquid documents tid as a 50-bit hash of the
buyer/seller order ids (neither monotonic nor guaranteed unique) and recommends
(block_time, coin, tid) for a globally unique id. The payload carries no
``block_time`` field and ``time`` is NOT assumed to equal it, so ``time`` is
not a key component: an identical full record (time, side, price, quantity)
under the same (symbol, tid) is an exact duplicate (counted once), while any
difference is a conflict that makes the report unavailable. tid is never used
for ordering except as a deterministic tie-break.

Event time is ``MarketTrade.timestamp`` (provider ``time``) and must equal
``provenance.source_timestamp``. A trade dated after the evaluation time is
future-dated and excluded; a trade received after the evaluation time is
excluded as not yet known (no lookahead). A trade received more than
``late_tolerance`` after its event time is late: it stays in its event-time
window but the result is not trusted. Nothing is interpolated or backfilled.

Quality: provenance and identity are checked for every input trade; C05
freshness, coverage, continuity and recovery are assessed on the newest
retained trade. A quiet market with no recent trade therefore fails closed.

Arithmetic is exact (8192-digit context over bounded inputs); reported values
round once to 50 significant digits.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, DecimalException, ROUND_HALF_EVEN, localcontext

from pydantic import Field, field_validator, model_validator

from traid.domain.models import AggressorSide, CanonicalModel, MarketTrade, SourceProvenance
from traid.exchange import Capability, CapabilityCoverage
from traid.liquidity import Metric
from traid.quality import (
    ContinuityStatus, QualityAssessment, QualityPolicy, RecoveryStatus, assess_quality,
)

FORMULA_VERSION = "c08-trade-flow-1"
CONTEXT = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
OUTPUT = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
ZERO = Decimal(0)
MAX_TRADES = 100000
UNIT_LIMITATION = "UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED"


def _bounded(value: Decimal) -> bool:
    return (value.is_finite() and len(value.as_tuple().digits) <= 50
            and (value == 0 or -1000 <= value.adjusted() <= 1000))


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


class FlowConfig(CanonicalModel):
    """Explicit units, rolling window, session start and lateness tolerance."""
    symbol: str
    base_asset: str = Field(min_length=1)
    window: timedelta
    session_start: datetime
    late_tolerance: timedelta

    @field_validator("session_start", mode="before")
    @classmethod
    def session_start_aware(cls, value):
        if isinstance(value, str):  # JSON round trip
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _utc(value, "session_start")

    @model_validator(mode="after")
    def valid(self):
        if not self.base_asset.strip():
            raise ValueError("units must be explicit")
        if self.window <= timedelta(0):
            raise ValueError("window must be positive")
        if self.late_tolerance < timedelta(0):
            raise ValueError("late_tolerance cannot be negative")
        return self


class FlowReport(CanonicalModel):
    formula_version: str = FORMULA_VERSION
    symbol: str
    evaluation_time: datetime
    window_start: datetime
    session_start: datetime
    config: FlowConfig
    # None when no retained trade existed or input integrity failed first.
    quality: QualityAssessment | None
    # True only if C05 trusts the input set and no late/future-dated trade was seen.
    trusted_for_current_use: bool
    reasons: tuple[str, ...]
    window_buy_volume: Metric
    window_sell_volume: Metric
    window_net_delta: Metric
    session_buy_volume: Metric
    session_sell_volume: Metric
    session_cvd: Metric
    window_trade_count: int | None
    session_trade_count: int | None
    input_trade_count: int
    duplicate_count: int
    late_count: int
    future_dated_count: int
    not_yet_received_count: int
    units_provider_verified: bool = False
    limitations: tuple[str, ...] = (
        UNIT_LIMITATION,
        "AGGRESSOR_SIDE_PROVIDER_REPORTED_NOT_INFERRED",
        "TRADE_IDENTITY_SYMBOL_AND_TID_FULL_RECORD_MATCH_BLOCK_TIME_UNVERIFIED",
        "FRESHNESS_FROM_NEWEST_RETAINED_TRADE_QUIET_MARKET_FAILS_CLOSED",
        "NO_BACKFILL_INTERPOLATION_OR_GAP_REPAIR",
        "FLOW_IS_NOT_DIRECTION_OR_SIGNAL",
    )

    @model_validator(mode="after")
    def explicit(self):
        if self.units_provider_verified:
            raise ValueError("flow units are never provider verified")
        if UNIT_LIMITATION not in self.limitations:
            raise ValueError("caller-asserted unit limitation must remain explicit")
        if self.trusted_for_current_use:
            if self.quality is None or not self.quality.trusted_for_current_use or self.reasons:
                raise ValueError("trusted flow requires trusted quality and no degradation reasons")
            if any(m.value is None for m in self._metrics()):
                raise ValueError("trusted flow requires every metric")
        return self

    def _metrics(self) -> tuple[Metric, ...]:
        return (self.window_buy_volume, self.window_sell_volume, self.window_net_delta,
                self.session_buy_volume, self.session_sell_volume, self.session_cvd)


def analyze_flow(
    trades: tuple[MarketTrade, ...], *, config: FlowConfig, coverage: CapabilityCoverage,
    evaluation_time: datetime, policy: QualityPolicy, continuity: ContinuityStatus,
    recovery: RecoveryStatus,
) -> FlowReport:
    """Aggregate trades at an explicit evaluation time; never reads a clock.

    Malformed canonical input or a wrong instrument raises. Structurally valid
    but analytically unusable input (missing side/identity, conflicting
    duplicates, no trades, untrusted C05 quality) returns explicit unavailable
    metrics. Late or future-dated trades keep values available but untrusted.
    Input order does not matter. At most 100000 trades; larger input is rejected.
    """
    if not isinstance(trades, tuple) or not isinstance(config, FlowConfig):
        raise ValueError("tuple of canonical trades and FlowConfig required")
    if len(trades) > MAX_TRADES:
        raise ValueError("too many trades for one analysis")
    # Revalidation also rejects model_construct/model_copy validation bypasses.
    config = FlowConfig.model_validate(config.model_dump())
    evaluation_time = _utc(evaluation_time, "evaluation_time")
    if config.session_start > evaluation_time:
        raise ValueError("SESSION_START_AFTER_EVALUATION")
    window_start = evaluation_time - config.window
    checked = []
    for trade in trades:
        if not isinstance(trade, MarketTrade):
            raise ValueError("canonical MarketTrade required")
        trade = MarketTrade.model_validate(trade.model_dump())
        if trade.symbol != config.symbol:
            raise ValueError("INSTRUMENT_IDENTITY_MISMATCH")
        checked.append(trade)

    blocking: set[str] = set()
    for trade in checked:
        provenance = trade.provenance
        if trade.side is None:
            blocking.add("AGGRESSOR_SIDE_UNKNOWN")
        if provenance.source_id is None:
            blocking.add("TRADE_ID_MISSING")
        if provenance.source_timestamp is None or provenance.source_timestamp != trade.timestamp:
            blocking.add("TRADE_TIMESTAMP_PROVENANCE_MISMATCH")
        if not (_bounded(trade.price) and _bounded(trade.quantity)):
            blocking.add("NUMERIC_RANGE_UNSUPPORTED")

    unique: dict[str, MarketTrade] = {}
    duplicates = 0
    if not blocking:
        for trade in checked:
            tid = trade.provenance.source_id
            kept = unique.get(tid)
            if kept is None:
                unique[tid] = trade
                continue
            if (kept.timestamp, kept.side, kept.price, kept.quantity) != (
                    trade.timestamp, trade.side, trade.price, trade.quantity):
                blocking.add("TRADE_IDENTITY_CONFLICT")
                continue
            duplicates += 1
            if (trade.provenance.received_timestamp, trade.provenance.source_type) < (
                    kept.provenance.received_timestamp, kept.provenance.source_type):
                unique[tid] = trade

    lower = min(window_start, config.session_start)
    future = not_yet = late = 0
    retained: list[MarketTrade] = []
    for tid in sorted(unique):
        trade = unique[tid]
        if trade.timestamp > evaluation_time:
            future += 1
        elif trade.provenance.received_timestamp > evaluation_time:
            not_yet += 1
        elif trade.timestamp >= lower:
            retained.append(trade)
            if trade.provenance.received_timestamp - trade.timestamp > config.late_tolerance:
                late += 1
    retained.sort(key=lambda t: (t.timestamp, t.provenance.source_id))

    def report(quality, reasons, metrics, window_count, session_count):
        reasons = tuple(dict.fromkeys(reasons))
        trusted = (quality is not None and quality.trusted_for_current_use and not reasons
                   and all(m.value is not None for m in metrics))
        return FlowReport(
            symbol=config.symbol, evaluation_time=evaluation_time, window_start=window_start,
            session_start=config.session_start, config=config, quality=quality,
            trusted_for_current_use=trusted, reasons=reasons,
            window_buy_volume=metrics[0], window_sell_volume=metrics[1], window_net_delta=metrics[2],
            session_buy_volume=metrics[3], session_sell_volume=metrics[4], session_cvd=metrics[5],
            window_trade_count=window_count, session_trade_count=session_count,
            input_trade_count=len(checked), duplicate_count=duplicates, late_count=late,
            future_dated_count=future, not_yet_received_count=not_yet)

    def unavailable(reason):
        return (Metric(value=None, unit=config.base_asset, reason=reason),) * 6

    if blocking:
        return report(None, sorted(blocking), unavailable(sorted(blocking)[0]), None, None)
    if not retained:
        reasons = ["NO_TRADES_IN_RANGE"] + (["FUTURE_DATED_TRADES_EXCLUDED"] if future else [])
        return report(None, reasons, unavailable("NO_TRADES_IN_RANGE"), None, None)

    newest = retained[-1]
    quality = assess_quality(
        capability=Capability.TRADES, provenance=newest.provenance, coverage=coverage,
        evaluation_time=evaluation_time, policy=policy, continuity=continuity,
        recovery=recovery, canonical_valid=True)
    if not quality.trusted_for_current_use:
        return report(quality, ["DATA_QUALITY_NOT_TRUSTED", *quality.reasons],
                      unavailable("DATA_QUALITY_NOT_TRUSTED"), None, None)

    reasons = []
    if late:
        reasons.append("LATE_TRADES_PRESENT")
    if future:
        reasons.append("FUTURE_DATED_TRADES_EXCLUDED")
    window = [t for t in retained if t.timestamp >= window_start]
    session = [t for t in retained if t.timestamp >= config.session_start]
    unit = config.base_asset

    def volumes(items, label):
        if not items:
            return (Metric(value=None, unit=unit, reason=f"NO_TRADES_IN_{label}"),) * 3
        try:
            with localcontext(CONTEXT):
                buy = sum((t.quantity for t in items if t.side is AggressorSide.BUY), ZERO)
                sell = sum((t.quantity for t in items if t.side is AggressorSide.SELL), ZERO)
                delta = buy - sell
                return tuple(Metric(value=OUTPUT.plus(v), unit=unit) for v in (buy, sell, delta))
        except DecimalException:
            return (Metric(value=None, unit=unit, reason="NUMERIC_CALCULATION_UNAVAILABLE"),) * 3

    w, s = volumes(window, "WINDOW"), volumes(session, "SESSION")
    if any(m.value is None for m in (*w, *s)):
        reasons.append("AGGREGATE_UNAVAILABLE")
    return report(quality, reasons, (*w, *s), len(window), len(session))
