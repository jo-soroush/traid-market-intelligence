"""Deterministic C10 market-state evidence over the C07, C08 and C09 reports.

C10 interprets; it never recomputes an upstream indicator, fills a missing value,
forecasts direction or scores confidence. Each dimension is classified separately
from only the report sections it reads, with its own input trust:

* direction  - C09 closed-1h-candle momentum (signed simple returns, "fraction") at the
  configured lookbacks. RANGING when every |return| <= range_max_abs_return; else
  non-zero returns of both signs are CONTRADICTORY_MOMENTUM; TRENDING_UP/DOWN when
  every |return| >= trend_min_abs_return with one sign; otherwise no rule matched.
  Lookbacks share closes, so agreement is a consistency check, never independent
  confirmation, and nothing is counted or weighted.
* volatility - C09 realized volatility: HIGH when >= high_min_realized_volatility,
  else NOT_HIGH. ATR is reported as a fact only (it reads the same candles).
* liquidity  - C07 displayed snapshot: THIN when spread_bps >= thin_min_spread_bps or
  the shallower side of one configured band has quote depth <= thin_max_band_quote_depth.
  Every configured criterion must be available, else UNKNOWN.
* flow       - C08 trade window: BUY/SELL_DOMINANT when |net delta| >=
  dominant_min_net_share * (buy + sell), else BALANCED. Session CVD is a fact only.
* funding    - polarity of the latest settled C09 hourly rate under the provider's
  documented sign convention. No threshold; it is not positioning evidence.
* crowding   - always UNKNOWN: open interest and basis are unavailable in C09.
* liquidation - AUTHORITATIVE_LIQUIDATION_EVENT only from caller-supplied canonical
  LiquidationEvents whose (source, source_type) the rules name as verified, that carry
  source id and source timestamp, were received by evaluation time and fall inside the
  configured window. HEURISTIC_LIQUIDATION_PRESSURE is not activated by this rules
  engine (no defensible thresholds, no temporally compatible inputs), and absent events
  prove nothing, so the label is otherwise UNKNOWN. No flow or liquidity evidence is read.
* regime     - composite of direction and volatility only: HIGH_VOLATILITY when
  volatility is HIGH, else the direction state; UNKNOWN unless both are classified.
  Liquidity, flow and funding are never averaged into it.

Every threshold is optional with no default; an unconfigured one yields UNKNOWN with
THRESHOLD_NOT_CONFIGURED while the observable facts are still reported. Thresholds are
uncalibrated in this version. Comparisons are exact: ``>=``/``<=`` boundaries are
inclusive as stated per rule, and ambient Decimal context never matters.

Timing: one caller-provided evaluation time T. Every report must have been evaluated at
exactly T (C07 through its C05 assessment); a mismatch, a symbol mismatch, an unsupported
formula version or conflicting asserted base/quote units raise. Upstream evidence
observed or received after T is excluded, never read. No timestamp is shifted: each
fact keeps the real window of its source (book instant, trade window, closed candles,
funding settlement hours).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import (
    Context, Decimal, DecimalException, DivisionByZero, Inexact, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, localcontext,
)
from enum import StrEnum
import hashlib
import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from traid.derivatives import FORMULA_VERSION as C09_VERSION, DerivativesReport
from traid.derivatives.analytics import RATE_UNIT
from traid.domain.models import CanonicalModel, DataQualityState, LiquidationEvent, SourceProvenance
from traid.flow import FORMULA_VERSION as C08_VERSION, FlowReport
from traid.liquidity import FORMULA_VERSION as C07_VERSION, LiquidityReport, Metric

ENGINE_VERSION = "c10-market-state-1"
DIGEST_ALGORITHM = "sha256-canonical-rules-v1"
# Exact arithmetic: an inexact product would make a boundary decision unreliable.
EXACT = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                traps=[Inexact, InvalidOperation, Overflow, DivisionByZero])
OUTPUT = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
HOUR = timedelta(hours=1)
MAX_LIQUIDATION_EVENTS = 10000
MOMENTUM_UNIT = "fraction"
VOLATILITY_UNIT = "ln(price ratio) per 1h bar, not annualized"
SPREAD_UNIT = "bps"
OI_REASON = "OPEN_INTEREST_UNAVAILABLE"
BASIS_REASON = "BASIS_UNAVAILABLE"
FUNDING_NOT_POSITIONING = "FUNDING_POLARITY_IS_NOT_POSITIONING_EVIDENCE"
HEURISTIC_NOT_ACTIVATED = "HEURISTIC_LIQUIDATION_PRESSURE_NOT_ACTIVATED"
ABSENCE_NOT_PROVEN = "NO_VERIFIED_LIQUIDATION_EVENT_ABSENCE_NOT_PROVEN"
FUTURE_EXCLUDED = "FUTURE_EVIDENCE_EXCLUDED"
NOT_CONFIGURED = "THRESHOLD_NOT_CONFIGURED"


def _utc(value, name: str) -> datetime:
    if isinstance(value, str):  # JSON round trip
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


# ------------------------------------------------------------------------------ rules
class DirectionRules(CanonicalModel):
    """Momentum lookbacks (C09 bars) and |simple return| thresholds as fractions."""
    momentum_lookbacks: tuple[int, ...] = ()
    trend_min_abs_return: Decimal | None = Field(default=None, gt=0)
    range_max_abs_return: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valid(self):
        if tuple(sorted(set(self.momentum_lookbacks))) != self.momentum_lookbacks:
            raise ValueError("momentum lookbacks must be unique and increasing")
        if any(k < 1 for k in self.momentum_lookbacks):
            raise ValueError("momentum lookbacks must be positive bar counts")
        configured = self.trend_min_abs_return is not None or self.range_max_abs_return is not None
        if configured and not self.momentum_lookbacks:
            raise ValueError("direction thresholds require momentum lookbacks")
        if (self.trend_min_abs_return is not None and self.range_max_abs_return is not None
                and not self.range_max_abs_return < self.trend_min_abs_return):
            raise ValueError("range bound must be below the trend threshold")
        return self


class VolatilityRules(CanonicalModel):
    high_min_realized_volatility: Decimal | None = Field(default=None, gt=0)


class LiquidityRules(CanonicalModel):
    thin_min_spread_bps: Decimal | None = Field(default=None, gt=0)
    depth_band_bps: Decimal | None = Field(default=None, gt=0)
    thin_max_band_quote_depth: Decimal | None = Field(default=None, gt=0)
    depth_quote_currency: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def valid(self):
        depth = (self.depth_band_bps, self.thin_max_band_quote_depth, self.depth_quote_currency)
        if any(v is None for v in depth) and any(v is not None for v in depth):
            raise ValueError("band depth rule needs band, threshold and quote currency together")
        return self


class FlowRules(CanonicalModel):
    """Share of window volume that |net delta| must reach to be dominant."""
    dominant_min_net_share: Decimal | None = Field(default=None, gt=0, le=1)


class VerifiedLiquidationSource(CanonicalModel):
    source: str = Field(min_length=1)
    source_type: str = Field(min_length=1)


class LiquidationRules(CanonicalModel):
    verified_sources: tuple[VerifiedLiquidationSource, ...] = ()
    window: timedelta | None = Field(default=None, gt=timedelta(0))

    @model_validator(mode="after")
    def valid(self):
        keys = [(s.source, s.source_type) for s in self.verified_sources]
        if keys != sorted(set(keys)):
            raise ValueError("verified sources must be unique and sorted")
        return self


class MarketStateRules(CanonicalModel):
    """Explicit, versioned rule configuration. No threshold has a default value."""
    rules_version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    calibration_status: Literal["UNCALIBRATED"] = "UNCALIBRATED"
    direction: DirectionRules = DirectionRules()
    volatility: VolatilityRules = VolatilityRules()
    liquidity: LiquidityRules = LiquidityRules()
    flow: FlowRules = FlowRules()
    liquidation: LiquidationRules = LiquidationRules()


def _canonical(value):
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, Decimal):  # equal values share one identity, whatever the exponent
        return format(value.normalize(EXACT), "f")
    if isinstance(value, timedelta):
        return f"{value // timedelta(microseconds=1)}us"
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def rules_digest(rules: MarketStateRules) -> str:
    """Deterministic identity of a rule configuration, version string included."""
    rules = MarketStateRules.model_validate(rules.model_dump())
    text = json.dumps(_canonical(rules.model_dump(mode="python")), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode()).hexdigest()


# ----------------------------------------------------------------------------- output
class DirectionState(StrEnum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    UNKNOWN = "UNKNOWN"


class VolatilityState(StrEnum):
    HIGH = "HIGH"
    NOT_HIGH = "NOT_HIGH"
    UNKNOWN = "UNKNOWN"


class LiquidityState(StrEnum):
    THIN = "THIN"
    NOT_THIN = "NOT_THIN"
    UNKNOWN = "UNKNOWN"


class FlowState(StrEnum):
    BUY_DOMINANT = "BUY_DOMINANT"
    SELL_DOMINANT = "SELL_DOMINANT"
    BALANCED = "BALANCED"
    UNKNOWN = "UNKNOWN"


class FundingPolarity(StrEnum):
    LONGS_PAY_SHORTS = "LONGS_PAY_SHORTS"
    SHORTS_PAY_LONGS = "SHORTS_PAY_LONGS"
    ZERO = "ZERO"
    UNKNOWN = "UNKNOWN"


class CrowdingState(StrEnum):
    UNKNOWN = "UNKNOWN"  # no positioning evidence exists until OI/basis are verified


class LiquidationLabel(StrEnum):
    AUTHORITATIVE_LIQUIDATION_EVENT = "AUTHORITATIVE_LIQUIDATION_EVENT"
    HEURISTIC_LIQUIDATION_PRESSURE = "HEURISTIC_LIQUIDATION_PRESSURE"
    UNKNOWN = "UNKNOWN"


class RegimeState(StrEnum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNKNOWN = "UNKNOWN"


class WindowKind(StrEnum):
    BOOK_SNAPSHOT = "BOOK_SNAPSHOT"            # one displayed book instant
    TRADE_WINDOW = "TRADE_WINDOW"              # C08 [window_start, evaluation_time]
    TRADE_SESSION = "TRADE_SESSION"            # C08 [session_start, evaluation_time]
    CLOSED_1H_CANDLES = "CLOSED_1H_CANDLES"    # first to last candle close involved
    FUNDING_SETTLEMENT_HOURS = "FUNDING_SETTLEMENT_HOURS"  # first to last UTC settlement hour
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SourceRef(CanonicalModel):
    """One upstream report section: version, quality, provenance and reasons verbatim."""
    source: Literal["C07.book", "C08.flow", "C09.candles", "C09.funding"]
    formula_version: str
    quality_state: DataQualityState | None
    quality_policy_version: str | None
    upstream_trusted: bool
    excluded_reason: str | None = None
    trusted_for_current_use: bool
    input_digest: str | None
    digest_algorithm: str | None
    newest_provenance: SourceProvenance | None
    upstream_reasons: tuple[str, ...]

    @model_validator(mode="after")
    def no_borrowed_trust(self):
        if self.trusted_for_current_use != (self.upstream_trusted and self.excluded_reason is None):
            raise ValueError("source trust is upstream trust minus C10 exclusion")
        return self


class Fact(CanonicalModel):
    """An upstream metric (or one C10-derived ratio) with its real observation window."""
    source: str
    field: str
    metric: Metric
    window_kind: WindowKind
    window_start: datetime | None
    window_end: datetime | None

    @field_validator("window_start", "window_end", mode="before")
    @classmethod
    def aware(cls, value):
        return None if value is None else _utc(value, "window")


class AppliedThreshold(CanonicalModel):
    name: str
    value: Decimal
    unit: str
    rule: str


class _Dimension(CanonicalModel):
    inputs_trusted: bool
    sources: tuple[SourceRef, ...]
    facts: tuple[Fact, ...]
    thresholds: tuple[AppliedThreshold, ...]
    reasons: tuple[str, ...]

    @model_validator(mode="after")
    def classified_only_when_earned(self):
        if self.inputs_trusted != (bool(self.sources) and all(s.trusted_for_current_use for s in self.sources)):
            raise ValueError("dimension trust must equal the trust of every source it reads")
        if self.state != "UNKNOWN":
            if not self.inputs_trusted or self.reasons:
                raise ValueError("a classified dimension requires trusted inputs and no reasons")
        elif not self.reasons:
            raise ValueError("UNKNOWN requires an explicit reason")
        return self


class DirectionResult(_Dimension):
    state: DirectionState

    @model_validator(mode="after")
    def thresholds_behind_state(self):
        if self.state != DirectionState.UNKNOWN and not self.thresholds:
            raise ValueError("direction classification requires configured thresholds")
        return self


class VolatilityResult(_Dimension):
    state: VolatilityState

    @model_validator(mode="after")
    def thresholds_behind_state(self):
        if self.state != VolatilityState.UNKNOWN and not self.thresholds:
            raise ValueError("volatility classification requires a configured threshold")
        return self


class LiquidityResult(_Dimension):
    state: LiquidityState

    @model_validator(mode="after")
    def thresholds_behind_state(self):
        if self.state != LiquidityState.UNKNOWN and not self.thresholds:
            raise ValueError("liquidity classification requires configured thresholds")
        return self


class FlowResult(_Dimension):
    state: FlowState

    @model_validator(mode="after")
    def thresholds_behind_state(self):
        if self.state != FlowState.UNKNOWN and not self.thresholds:
            raise ValueError("flow classification requires a configured threshold")
        return self


class FundingResult(_Dimension):
    state: FundingPolarity
    interval: Literal["1h"] = "1h"


class CrowdingResult(_Dimension):
    state: CrowdingState


class LiquidationContext(CanonicalModel):
    label: LiquidationLabel
    authoritative_events: tuple[LiquidationEvent, ...]
    window_start: datetime | None
    window_end: datetime
    supplied_count: int = Field(ge=0)
    not_yet_received_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    heuristic_pressure: Literal["NOT_ACTIVATED"] = "NOT_ACTIVATED"
    reasons: tuple[str, ...]

    @field_validator("window_start", "window_end", mode="before")
    @classmethod
    def aware(cls, value):
        return None if value is None else _utc(value, "window")

    @model_validator(mode="after")
    def truth_labels_kept_apart(self):
        if self.label is LiquidationLabel.HEURISTIC_LIQUIDATION_PRESSURE:
            raise ValueError("heuristic liquidation pressure is not activated in this engine")
        if (self.label is LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT) != bool(self.authoritative_events):
            raise ValueError("the authoritative label exists exactly when verified events were accepted")
        if HEURISTIC_NOT_ACTIVATED not in self.reasons:
            raise ValueError("the inactive heuristic must remain explicit")
        return self


class RegimeResult(CanonicalModel):
    state: RegimeState
    direction: DirectionState
    volatility: VolatilityState
    inputs_trusted: bool
    reasons: tuple[str, ...]

    @model_validator(mode="after")
    def conservative(self):
        known = self.direction != DirectionState.UNKNOWN and self.volatility != VolatilityState.UNKNOWN
        if self.state == RegimeState.UNKNOWN:
            if known or not self.reasons:
                raise ValueError("composite UNKNOWN only when a component is UNKNOWN, with reasons")
        else:
            expected = (RegimeState.HIGH_VOLATILITY if self.volatility == VolatilityState.HIGH
                        else RegimeState(self.direction.value)) if known else None
            if self.state != expected or not self.inputs_trusted or self.reasons:
                raise ValueError("composite must follow its documented rule from trusted components")
        return self


class MarketStateReport(CanonicalModel):
    engine_version: str = ENGINE_VERSION
    symbol: str
    evaluation_time: datetime
    rules: MarketStateRules
    rules_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    digest_algorithm: str = DIGEST_ALGORITHM
    direction: DirectionResult
    volatility: VolatilityResult
    liquidity: LiquidityResult
    flow: FlowResult
    funding: FundingResult
    crowding: CrowdingResult
    liquidation: LiquidationContext
    regime: RegimeResult
    limitations: tuple[str, ...] = (
        "NOT_A_FORECAST_PROBABILITY_OR_TRADING_SIGNAL",
        "THRESHOLDS_UNCALIBRATED_CALLER_CONFIGURED",
        "MOMENTUM_LOOKBACKS_SHARE_CLOSES_NOT_INDEPENDENT_CONFIRMATION",
        "DIMENSIONS_DESCRIBE_DIFFERENT_WINDOWS_NOT_SYNCHRONIZED",
        "NO_OVERALL_TRUST_EACH_DIMENSION_CARRIES_ITS_OWN",
        "CROWDING_UNKNOWN_OPEN_INTEREST_AND_BASIS_UNAVAILABLE",
        "ABSENCE_OF_LIQUIDATION_EVENTS_IS_NOT_EVIDENCE_OF_NONE",
        "UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED",
    )

    @field_validator("evaluation_time", mode="before")
    @classmethod
    def aware(cls, value):
        return _utc(value, "evaluation_time")

    @model_validator(mode="after")
    def bound_to_rules(self):
        if self.rules_digest != rules_digest(self.rules):
            raise ValueError("rules digest does not match the rules")
        if self.regime.direction != self.direction.state or self.regime.volatility != self.volatility.state:
            raise ValueError("composite must reflect the reported components")
        return self


# ----------------------------------------------------------------------------- inputs
def _revalidated(value, cls, version):
    if value is None:
        return None
    if type(value) is not cls:
        raise ValueError(f"{cls.__name__} required")
    # Revalidation also rejects model_construct/model_copy validation bypasses.
    value = cls.model_validate(value.model_dump())
    if value.formula_version != version:
        raise ValueError("UNSUPPORTED_FORMULA_VERSION")
    return value


def _ref(source, formula_version, quality, upstream_trusted, provenance_obj, newest, reasons, excluded):
    return SourceRef(
        source=source, formula_version=formula_version,
        quality_state=None if quality is None else quality.state,
        quality_policy_version=None if quality is None else quality.policy_version,
        upstream_trusted=upstream_trusted, excluded_reason=excluded,
        trusted_for_current_use=upstream_trusted and excluded is None,
        input_digest=None if provenance_obj is None else provenance_obj.input_digest,
        digest_algorithm=None if provenance_obj is None else provenance_obj.digest_algorithm,
        newest_provenance=newest, upstream_reasons=reasons)


def _after(t: datetime | None, evaluation_time: datetime) -> bool:
    return t is not None and t > evaluation_time


def _book_ref(book: LiquidityReport, T):
    p = book.provenance
    future = (_after(book.snapshot_timestamp, T) or _after(p.received_timestamp, T)
              or _after(p.source_timestamp, T))
    return _ref("C07.book", book.formula_version, book.quality, book.quality.trusted_for_current_use,
                None, p, book.quality.reasons, FUTURE_EXCLUDED if future else None)


def _flow_ref(flow: FlowReport, T):
    p = flow.provenance
    future = _after(flow.window_start, T) or _after(flow.session_start, T) or (p is not None and (
        _after(p.latest_event_time, T) or _after(p.newest_trade_provenance.received_timestamp, T)))
    return _ref("C08.flow", flow.formula_version, flow.quality, flow.trusted_for_current_use, p,
                None if p is None else p.newest_trade_provenance, flow.reasons,
                FUTURE_EXCLUDED if future else None)


def _section_ref(name, report: DerivativesReport, section, T, closes_after_start: bool):
    p = section.provenance
    # A candle is only known once closed; a funding hour once settled.
    known_at = None if section.latest_start is None else section.latest_start + (HOUR if closes_after_start else timedelta(0))
    future = _after(known_at, T) or (p is not None and (
        _after(p.latest_time, T) or _after(p.newest_record_provenance.received_timestamp, T)))
    return _ref(name, report.formula_version, section.quality, section.trusted_for_current_use, p,
                None if p is None else p.newest_record_provenance, section.reasons,
                FUTURE_EXCLUDED if future else None)


def _not_trusted(ref: SourceRef) -> list[str]:
    if ref.excluded_reason:
        return [f"{ref.source}:{ref.excluded_reason}"]
    return [] if ref.trusted_for_current_use else [f"{ref.source}:NOT_TRUSTED"]


def _threshold(name, value, unit, rule):
    return AppliedThreshold(name=name, value=value, unit=unit, rule=rule)


def _metric_problem(field, metric: Metric, unit: str) -> str | None:
    if metric.value is None:
        return f"METRIC_UNAVAILABLE:{field}:{metric.reason}"
    if metric.unit != unit:
        return f"UNIT_MISMATCH:{field}"
    return None


# ------------------------------------------------------------------------- dimensions
def _closed_window(latest_start, bars):
    """Close instants of the first and last candles a k-bar change spans."""
    if latest_start is None:
        return None, None
    return latest_start - (bars - 1) * HOUR, latest_start + HOUR


def _candle_facts(section):
    def fact(field, metric, bars):
        start, end = _closed_window(section.latest_start, bars) if metric.value is not None else (None, None)
        return Fact(source="C09.candles", field=field, metric=metric,
                    window_kind=WindowKind.CLOSED_1H_CANDLES, window_start=start, window_end=end)
    return fact


def _direction(report: DerivativesReport | None, T, rules: DirectionRules) -> DirectionResult:
    thresholds = []
    if rules.trend_min_abs_return is not None:
        thresholds.append(_threshold("trend_min_abs_return", rules.trend_min_abs_return, MOMENTUM_UNIT,
                                     "TRENDING when every |return| >= value with one sign"))
    if rules.range_max_abs_return is not None:
        thresholds.append(_threshold("range_max_abs_return", rules.range_max_abs_return, MOMENTUM_UNIT,
                                     "RANGING when every |return| <= value"))
    if report is None:
        return DirectionResult(state=DirectionState.UNKNOWN, inputs_trusted=False, sources=(), facts=(),
                               thresholds=tuple(thresholds), reasons=("C09_REPORT_NOT_PROVIDED",))
    section = report.candles
    ref = _section_ref("C09.candles", report, section, T, True)
    reasons = _not_trusted(ref)
    facts, values = [], []
    if not ref.excluded_reason:
        fact = _candle_facts(section)
        facts = [fact(f"candles.momentum[{m.lookback_bars}].simple_return", m.simple_return, m.lookback_bars)
                 for m in section.momentum]
        by_k = {m.lookback_bars: m.simple_return for m in section.momentum}
        for k in rules.momentum_lookbacks:
            if k not in by_k:
                reasons.append(f"MOMENTUM_LOOKBACK_NOT_IN_REPORT:{k}")
            elif problem := _metric_problem(f"momentum[{k}]", by_k[k], MOMENTUM_UNIT):
                reasons.append(problem)
            else:
                values.append(by_k[k])
    if not rules.momentum_lookbacks:
        reasons.append(f"{NOT_CONFIGURED}:direction")
    state = DirectionState.UNKNOWN
    if not reasons:
        returns = [m.value for m in values]
        trend, band = rules.trend_min_abs_return, rules.range_max_abs_return
        if not thresholds:
            reasons.append(f"{NOT_CONFIGURED}:direction")
        elif band is not None and all(r.copy_abs() <= band for r in returns):
            state = DirectionState.RANGING
        elif any(r > 0 for r in returns) and any(r < 0 for r in returns):
            reasons.append("CONTRADICTORY_MOMENTUM")
        elif trend is not None and all(r.copy_abs() >= trend for r in returns):
            state = DirectionState.TRENDING_UP if returns[0] > 0 else DirectionState.TRENDING_DOWN
        else:
            reasons.append("NO_DIRECTION_RULE_MATCHED")
    return DirectionResult(state=state, inputs_trusted=ref.trusted_for_current_use, sources=(ref,),
                           facts=tuple(facts), thresholds=tuple(thresholds), reasons=tuple(reasons))


def _volatility(report: DerivativesReport | None, T, rules: VolatilityRules) -> VolatilityResult:
    t = rules.high_min_realized_volatility
    thresholds = () if t is None else (_threshold(
        "high_min_realized_volatility", t, VOLATILITY_UNIT, "HIGH when value >= threshold, else NOT_HIGH"),)
    if report is None:
        return VolatilityResult(state=VolatilityState.UNKNOWN, inputs_trusted=False, sources=(), facts=(),
                                thresholds=thresholds, reasons=("C09_REPORT_NOT_PROVIDED",))
    section, cfg = report.candles, report.config
    ref = _section_ref("C09.candles", report, section, T, True)
    reasons = _not_trusted(ref)
    facts = []
    if not ref.excluded_reason:
        fact = _candle_facts(section)
        facts = [fact("candles.realized_volatility", section.realized_volatility, cfg.volatility_period),
                 fact("candles.atr", section.atr, cfg.atr_period)]
        if problem := _metric_problem("realized_volatility", section.realized_volatility, VOLATILITY_UNIT):
            reasons.append(problem)
    if t is None:
        reasons.append(f"{NOT_CONFIGURED}:volatility")
    state = VolatilityState.UNKNOWN
    if not reasons:
        state = VolatilityState.HIGH if section.realized_volatility.value >= t else VolatilityState.NOT_HIGH
    return VolatilityResult(state=state, inputs_trusted=ref.trusted_for_current_use, sources=(ref,),
                            facts=tuple(facts), thresholds=thresholds, reasons=tuple(reasons))


def _liquidity(book: LiquidityReport | None, T, rules: LiquidityRules) -> LiquidityResult:
    thresholds = []
    if rules.thin_min_spread_bps is not None:
        thresholds.append(_threshold("thin_min_spread_bps", rules.thin_min_spread_bps, SPREAD_UNIT,
                                     "THIN when spread_bps >= value"))
    if rules.thin_max_band_quote_depth is not None:
        thresholds.append(_threshold(
            f"thin_max_band_quote_depth[{format(rules.depth_band_bps, 'f')}bps]",
            rules.thin_max_band_quote_depth, rules.depth_quote_currency,
            "THIN when the shallower side's quote depth in the band <= value"))
    if book is None:
        return LiquidityResult(state=LiquidityState.UNKNOWN, inputs_trusted=False, sources=(), facts=(),
                               thresholds=tuple(thresholds), reasons=("C07_REPORT_NOT_PROVIDED",))
    ref = _book_ref(book, T)
    reasons = _not_trusted(ref)
    facts, thin = [], []
    if not ref.excluded_reason:
        def fact(field, metric):
            return Fact(source="C07.book", field=field, metric=metric, window_kind=WindowKind.BOOK_SNAPSHOT,
                        window_start=book.snapshot_timestamp, window_end=book.snapshot_timestamp)
        facts.append(fact("spread_bps", book.spread_bps))
        for band in book.bands:
            w = format(band.width_bps, "f")
            facts += [fact(f"bands[{w}].bid_quote", band.bid_quote), fact(f"bands[{w}].ask_quote", band.ask_quote),
                      fact(f"bands[{w}].imbalance", band.imbalance)]
        if rules.thin_min_spread_bps is not None:
            if problem := _metric_problem("spread_bps", book.spread_bps, SPREAD_UNIT):
                reasons.append(problem)
            else:
                thin.append(book.spread_bps.value >= rules.thin_min_spread_bps)
        if rules.depth_band_bps is not None:
            band = next((b for b in book.bands if b.width_bps == rules.depth_band_bps), None)
            if band is None:
                reasons.append(f"BAND_NOT_IN_REPORT:{format(rules.depth_band_bps, 'f')}")
            else:
                problems = [p for p in (_metric_problem("band.bid_quote", band.bid_quote, rules.depth_quote_currency),
                                        _metric_problem("band.ask_quote", band.ask_quote, rules.depth_quote_currency)) if p]
                if problems:
                    reasons += problems
                else:
                    thin.append(min(band.bid_quote.value, band.ask_quote.value) <= rules.thin_max_band_quote_depth)
    if not thresholds:
        reasons.append(f"{NOT_CONFIGURED}:liquidity")
    state = LiquidityState.UNKNOWN
    if not reasons:
        state = LiquidityState.THIN if any(thin) else LiquidityState.NOT_THIN
    return LiquidityResult(state=state, inputs_trusted=ref.trusted_for_current_use, sources=(ref,),
                           facts=tuple(facts), thresholds=tuple(thresholds), reasons=tuple(reasons))


def _flow(flow: FlowReport | None, T, rules: FlowRules) -> FlowResult:
    share = rules.dominant_min_net_share
    thresholds = () if share is None else (_threshold(
        "dominant_min_net_share", share, "fraction of window volume",
        "DOMINANT when |net delta| >= value * (buy + sell), else BALANCED"),)
    if flow is None:
        return FlowResult(state=FlowState.UNKNOWN, inputs_trusted=False, sources=(), facts=(),
                          thresholds=thresholds, reasons=("C08_REPORT_NOT_PROVIDED",))
    ref = _flow_ref(flow, T)
    reasons = _not_trusted(ref)
    facts = []
    state = FlowState.UNKNOWN
    if not ref.excluded_reason:
        unit = flow.config.base_asset
        def fact(field, metric, kind=WindowKind.TRADE_WINDOW, start=flow.window_start, source="C08.flow"):
            return Fact(source=source, field=field, metric=metric, window_kind=kind, window_start=start, window_end=T)
        buy, sell, net = flow.window_buy_volume, flow.window_sell_volume, flow.window_net_delta
        facts = [fact("window_buy_volume", buy), fact("window_sell_volume", sell), fact("window_net_delta", net),
                 fact("session_cvd", flow.session_cvd, WindowKind.TRADE_SESSION, flow.session_start)]
        problems = [p for p in (_metric_problem("window_buy_volume", buy, unit),
                                _metric_problem("window_sell_volume", sell, unit),
                                _metric_problem("window_net_delta", net, unit)) if p]
        reasons += problems
        if not problems:  # the observable share is reported even when upstream trust is missing
            try:
                with localcontext(EXACT):
                    total = buy.value + sell.value
                    if total <= 0:
                        reasons.append("NO_WINDOW_VOLUME")
                    else:
                        with localcontext(OUTPUT):
                            ratio = Metric(value=net.value / total, unit="fraction of window volume")
                        facts.append(fact("window_net_delta / (window_buy_volume + window_sell_volume)", ratio,
                                          source="C10.derived"))
                        if share is not None and not reasons:
                            dominant = net.value.copy_abs() >= share * total  # exact, inclusive boundary
                            state = (FlowState.BALANCED if not dominant else
                                     FlowState.BUY_DOMINANT if net.value > 0 else FlowState.SELL_DOMINANT)
            except DecimalException:
                reasons.append("NUMERIC_CALCULATION_UNAVAILABLE")
    if share is None:
        reasons.append(f"{NOT_CONFIGURED}:flow")
    if reasons:
        state = FlowState.UNKNOWN
    return FlowResult(state=state, inputs_trusted=ref.trusted_for_current_use, sources=(ref,),
                      facts=tuple(facts), thresholds=thresholds, reasons=tuple(reasons))


def _funding(report: DerivativesReport | None, T) -> FundingResult:
    if report is None:
        return FundingResult(state=FundingPolarity.UNKNOWN, inputs_trusted=False, sources=(), facts=(),
                             thresholds=(), reasons=("C09_REPORT_NOT_PROVIDED",))
    section = report.funding
    ref = _section_ref("C09.funding", report, section, T, False)
    reasons = _not_trusted(ref)
    facts = []
    state = FundingPolarity.UNKNOWN
    if not ref.excluded_reason:
        last = section.latest_start
        def fact(field, metric, hours):
            known = metric.value is not None and last is not None
            return Fact(source="C09.funding", field=field, metric=metric,
                        window_kind=WindowKind.FUNDING_SETTLEMENT_HOURS,
                        window_start=last - (hours - 1) * HOUR if known else None, window_end=last if known else None)
        facts = [fact("funding.latest_rate", section.latest_rate, 1),
                 fact("funding.cumulative_funding", section.cumulative_funding, section.lookback_hours),
                 fact("funding.mean_hourly_funding", section.mean_hourly_funding, section.lookback_hours)]
        if problem := _metric_problem("funding.latest_rate", section.latest_rate, RATE_UNIT):
            reasons.append(problem)
        if not reasons:
            rate = section.latest_rate.value
            state = (FundingPolarity.LONGS_PAY_SHORTS if rate > 0 else
                     FundingPolarity.SHORTS_PAY_LONGS if rate < 0 else FundingPolarity.ZERO)
    return FundingResult(state=state, inputs_trusted=ref.trusted_for_current_use, sources=(ref,),
                         facts=tuple(facts), thresholds=(), reasons=tuple(reasons))


def _crowding(report: DerivativesReport | None) -> CrowdingResult:
    reasons = [OI_REASON, BASIS_REASON, FUNDING_NOT_POSITIONING]
    facts = ()
    if report is None:
        reasons.insert(0, "C09_REPORT_NOT_PROVIDED")
    else:
        none = dict(window_kind=WindowKind.NOT_APPLICABLE, window_start=None, window_end=None)
        facts = (Fact(source="C09", field="open_interest", metric=report.open_interest, **none),
                 Fact(source="C09", field="basis", metric=report.basis, **none))
    # No source is read for a classification, so crowding never claims trusted inputs.
    return CrowdingResult(state=CrowdingState.UNKNOWN, inputs_trusted=False, sources=(), facts=facts,
                          thresholds=(), reasons=tuple(reasons))


def _liquidations(events, T, rules: LiquidationRules) -> LiquidationContext:
    window = rules.window
    start = None if window is None else T - window
    verified = {(s.source, s.source_type) for s in rules.verified_sources}
    later = 0
    rejected: dict[str, int] = {}
    groups: dict[tuple[str, str], list[LiquidationEvent]] = {}
    for e in events:
        p = e.provenance
        if _after(p.received_timestamp, T) or _after(e.timestamp, T):
            later += 1  # counted, never read
            continue
        if (p.source, p.source_type) not in verified:
            why = "LIQUIDATION_SOURCE_NOT_VERIFIED"
        elif p.source_id is None or p.source_timestamp is None:
            why = "LIQUIDATION_POINT_IN_TIME_PROVENANCE_INCOMPLETE"
        elif e.timestamp > p.received_timestamp:
            why = "LIQUIDATION_EVENT_AFTER_RECEIPT"
        elif window is None or not start < e.timestamp <= T:
            why = None if window is None else "LIQUIDATION_OUTSIDE_WINDOW"
        else:
            groups.setdefault((p.source, p.source_id), []).append(e)
            continue
        if why:
            rejected[why] = rejected.get(why, 0) + 1
    reasons = [f"{why}:{n}" for why, n in sorted(rejected.items())]
    if window is None:
        reasons.append(f"{NOT_CONFIGURED}:liquidation_window")
    accepted, duplicates = [], 0
    for key in sorted(groups):
        group = groups[key]
        if len({(e.timestamp, e.price, e.quantity, e.provenance.source_timestamp) for e in group}) > 1:
            reasons.append("CONFLICTING_LIQUIDATION_IDENTITY")
            continue
        duplicates += len(group) - 1
        accepted.append(min(group, key=lambda e: (e.provenance.received_timestamp, e.provenance.source_type)))
    if "CONFLICTING_LIQUIDATION_IDENTITY" in reasons:
        accepted = []  # fail closed: a conflicted feed cannot be authoritative for this window
    accepted.sort(key=lambda e: (e.timestamp, e.provenance.source, e.provenance.source_id))
    if not accepted:
        reasons.append(ABSENCE_NOT_PROVEN)
    reasons.append(HEURISTIC_NOT_ACTIVATED)
    return LiquidationContext(
        label=LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT if accepted else LiquidationLabel.UNKNOWN,
        authoritative_events=tuple(accepted), window_start=start, window_end=T,
        supplied_count=len(events), not_yet_received_count=later, duplicate_count=duplicates,
        reasons=tuple(dict.fromkeys(reasons)))


def _regime(direction: DirectionResult, volatility: VolatilityResult) -> RegimeResult:
    reasons = []
    if direction.state == DirectionState.UNKNOWN:
        reasons.append("DIRECTION_UNKNOWN")
    if volatility.state == VolatilityState.UNKNOWN:
        reasons.append("VOLATILITY_UNKNOWN")
    if reasons:
        state = RegimeState.UNKNOWN
    elif volatility.state == VolatilityState.HIGH:
        state = RegimeState.HIGH_VOLATILITY
    else:
        state = RegimeState(direction.state.value)
    return RegimeResult(state=state, direction=direction.state, volatility=volatility.state,
                        inputs_trusted=direction.inputs_trusted and volatility.inputs_trusted,
                        reasons=tuple(reasons))


# -------------------------------------------------------------------------------- API
def classify_market_state(
    *, evaluation_time: datetime, symbol: str, rules: MarketStateRules,
    liquidity: LiquidityReport | None = None, flow: FlowReport | None = None,
    derivatives: DerivativesReport | None = None,
    liquidations: tuple[LiquidationEvent, ...] = (),
) -> MarketStateReport:
    """Classify each market-state dimension at one explicit evaluation time.

    Pure and deterministic: no clock, network, I/O, AI or persistent state, and
    liquidation input order does not matter. Caller contract violations (wrong
    types, time, symbol, formula version or conflicting asserted units) raise;
    insufficient, untrusted or future evidence yields UNKNOWN with reasons.
    """
    if type(rules) is not MarketStateRules:
        raise ValueError("MarketStateRules required")
    if not isinstance(liquidations, tuple) or len(liquidations) > MAX_LIQUIDATION_EVENTS:
        raise ValueError("a bounded tuple of LiquidationEvent required")
    rules = MarketStateRules.model_validate(rules.model_dump())
    T = _utc(evaluation_time, "evaluation_time")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol required")
    symbol = symbol.strip()
    liquidity = _revalidated(liquidity, LiquidityReport, C07_VERSION)
    flow = _revalidated(flow, FlowReport, C08_VERSION)
    derivatives = _revalidated(derivatives, DerivativesReport, C09_VERSION)
    events = []
    for e in liquidations:
        if type(e) is not LiquidationEvent:
            raise ValueError("LiquidationEvent required")
        events.append(LiquidationEvent.model_validate(e.model_dump()))

    times = []
    if liquidity is not None:
        times.append(liquidity.quality.evaluation_time)
    times += [r.evaluation_time for r in (flow, derivatives) if r is not None]
    if derivatives is not None:
        times += [s.quality.evaluation_time for s in (derivatives.candles, derivatives.funding)
                  if s.quality is not None]
    if any(t != T for t in times):
        raise ValueError("EVALUATION_TIME_MISMATCH")
    names = [r.symbol for r in (liquidity, flow, derivatives) if r is not None]
    names += [r.config.symbol for r in (liquidity, flow, derivatives) if r is not None]
    names += [e.symbol for e in events]
    if any(n != symbol for n in names):
        raise ValueError("INSTRUMENT_IDENTITY_MISMATCH")
    bases = {r.config.base_asset for r in (liquidity, flow, derivatives) if r is not None}
    quotes = {r.config.quote_currency for r in (liquidity, derivatives) if r is not None}
    if len(bases) > 1 or len(quotes) > 1:
        raise ValueError("UNIT_IDENTITY_MISMATCH")

    direction = _direction(derivatives, T, rules.direction)
    volatility = _volatility(derivatives, T, rules.volatility)
    return MarketStateReport(
        symbol=symbol, evaluation_time=T, rules=rules, rules_digest=rules_digest(rules),
        direction=direction, volatility=volatility,
        liquidity=_liquidity(liquidity, T, rules.liquidity), flow=_flow(flow, T, rules.flow),
        funding=_funding(derivatives, T), crowding=_crowding(derivatives),
        liquidation=_liquidations(tuple(events), T, rules.liquidation),
        regime=_regime(direction, volatility))
