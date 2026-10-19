"""Deterministic 1h candle indicators and hourly funding context.

Candle conventions (closed 1h candles only; units caller-asserted):
* ATR = simple mean of the last ``atr_period`` true ranges, TR = max(high-low,
  |high-prev_close|, |low-prev_close|). Needs atr_period + 1 candles.
* Realized volatility = sample standard deviation (n-1) of the last n
  close-to-close log returns ln(close_t / close_t-1), per 1h bar, NOT annualized.
  Needs n + 1 candles.
* Session VWAP = sum(typical_price * volume) / sum(volume) over closed candles
  from ``session_start``, typical price = (high + low + close) / 3. This is a
  CANDLE APPROXIMATION, not trade-level VWAP. Volume is read as base-asset volume
  (it reconciled with the provider's 24h base volume, but the provider docs do
  not state the unit). The first session candle must start at ``session_start``.
* Momentum(k) = close_latest / close_(latest-k bars) - 1 (simple return, signed).
Every window must be consecutive hourly candles; a gap makes that metric
unavailable. Too little history reports WARMING_UP, never zero.

Funding: the signed decimal fraction paid per 1h interval, as reported
(positive = longs pay shorts per the provider docs). Hyperliquid funding settles
hourly (docs; ``fundingHistory`` observed on the hour; predictedFundings reports
fundingIntervalHours = 1). Cumulative funding over the lookback is the plain sum
of the hourly rates; nothing is annualized, projected or assumed constant. Rates
beyond the documented 4%/hour cap are rejected.

Timing: a record received after ``evaluation_time`` is counted and never read.
A candle received before it closed is an incomplete observation and is excluded.
Freshness is interval-aware and independent of the C05 thresholds, which are not
changed: the newest expected observation at ``evaluation_time`` is the one whose
hour closed at least C06's 60 s availability offset earlier. LIVE = that
observation is present, DELAYED = one hour behind, STALE = more. Coverage,
continuity and recovery degrade state exactly as in C05. Untrusted quality
withholds every number. Identity: candles by (source, symbol, start), funding by
(source, symbol, UTC hour); identical repeats count once, different content under
one identity makes the section unavailable. One provenance source per input set.

Open interest and basis are never computed: OI units, aggregation and timing are
unverified and the asset context carries no timestamp; no canonical mark/oracle
price pair exists.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, DecimalException, ROUND_HALF_EVEN, localcontext
import hashlib
import json

from pydantic import Field, field_validator, model_validator

from traid.domain.models import Candle, CanonicalModel, DataQualityState, FundingSnapshot, SourceProvenance
from traid.exchange import Capability, CapabilityAvailability, CapabilityCoverage
from traid.historical.models import CANDLE_OFFSET_SECONDS, FUNDING_OFFSET_SECONDS
from traid.liquidity import Metric
from traid.quality import (
    ContinuityStatus, FreshnessBasis, ProvenanceQuality, QualityAssessment, RecoveryStatus,
)

FORMULA_VERSION = "c09-derivatives-1"
FRESHNESS_POLICY_VERSION = "c09-hourly-freshness-1"
CANDLE_DIGEST = "sha256-canonical-candles-v1"
FUNDING_DIGEST = "sha256-canonical-funding-v1"
CONTEXT = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
LOG_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
OUTPUT = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
ZERO = Decimal(0)
HOUR = timedelta(hours=1)
MILLISECOND = timedelta(milliseconds=1)
CANDLE_SPAN = HOUR - MILLISECOND  # provider's inclusive final millisecond
CANDLE_OFFSET = timedelta(seconds=CANDLE_OFFSET_SECONDS)
FUNDING_OFFSET = timedelta(seconds=FUNDING_OFFSET_SECONDS)
FUNDING_CAP = Decimal("0.04")  # documented cap, fraction per hour
MAX_RECORDS = 10000
RATE_UNIT = "fraction per 1h interval (positive: longs pay shorts)"
UNIT_LIMITATION = "UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED"
OI_REASON = "OPEN_INTEREST_UNVERIFIED_UNIT_AGGREGATION_AND_TIMING"
BASIS_REASON = "BASIS_CANONICAL_PRICE_PAIR_AND_PROVENANCE_NOT_ESTABLISHED"
GAP_REASONS = ("GAP_IN_LOOKBACK", "GAP_IN_SESSION", "SESSION_START_NOT_COVERED")
_RANK = {DataQualityState.LIVE: 0, DataQualityState.DELAYED: 1,
         DataQualityState.STALE: 2, DataQualityState.UNAVAILABLE: 3}


def _bounded(value: Decimal) -> bool:
    return (value.is_finite() and len(value.as_tuple().digits) <= 50
            and (value == 0 or -1000 <= value.adjusted() <= 1000))


def _utc(value, name: str) -> datetime:
    if isinstance(value, str):  # JSON round trip
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _floor_hour(value: datetime) -> datetime:
    return value.replace(minute=0, second=0, microsecond=0)


def _expected_hour(evaluation_time: datetime, offset: timedelta) -> datetime:
    """Start of the newest hour whose observation is expected available."""
    return _floor_hour(evaluation_time - offset) - HOUR


def _num(value: Decimal) -> str:
    return format(CONTEXT.normalize(value), "f")


class DerivativesConfig(CanonicalModel):
    """Explicit units, periods and (optional) hour-aligned VWAP session start."""
    symbol: str
    base_asset: str = Field(min_length=1)
    quote_currency: str = Field(min_length=1)
    atr_period: int = Field(ge=1, le=200)
    volatility_period: int = Field(ge=2, le=500)
    momentum_lookbacks: tuple[int, ...] = Field(min_length=1, max_length=8)
    funding_lookback_hours: int = Field(ge=1, le=720)
    session_start: datetime | None = None

    @field_validator("session_start", mode="before")
    @classmethod
    def session_start_aware(cls, value):
        return None if value is None else _utc(value, "session_start")

    @model_validator(mode="after")
    def valid(self):
        if not self.base_asset.strip() or not self.quote_currency.strip():
            raise ValueError("units must be explicit")
        if tuple(sorted(set(self.momentum_lookbacks))) != self.momentum_lookbacks:
            raise ValueError("momentum lookbacks must be unique and increasing")
        if not all(1 <= k <= 500 for k in self.momentum_lookbacks):
            raise ValueError("momentum lookbacks must be 1..500 bars")
        if self.session_start is not None and self.session_start != _floor_hour(self.session_start):
            raise ValueError("session_start must be aligned to a UTC hour")
        return self


class InputProvenance(CanonicalModel):
    """Compact, bounded reference to the records behind a section."""
    source: str
    source_types: tuple[str, ...]
    contributing_count: int = Field(ge=1)
    earliest_time: datetime
    latest_time: datetime
    newest_record_provenance: SourceProvenance
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    digest_algorithm: str


class MomentumMetric(CanonicalModel):
    lookback_bars: int
    simple_return: Metric


class _Section(CanonicalModel):
    quality: QualityAssessment | None
    provenance: InputProvenance | None
    trusted_for_current_use: bool
    reasons: tuple[str, ...]
    input_count: int
    duplicate_count: int
    not_yet_received_count: int
    retained_count: int
    latest_start: datetime | None
    bars_behind: int | None

    def _metrics(self) -> tuple[Metric, ...]:
        raise NotImplementedError

    @model_validator(mode="after")
    def explicit(self):
        if self.provenance is None and any(m.value is not None for m in self._metrics()):
            raise ValueError("available metrics require contributing-record provenance")
        if self.trusted_for_current_use and (
                self.quality is None or not self.quality.trusted_for_current_use or self.reasons):
            raise ValueError("trusted section requires trusted quality and no degradation reasons")
        return self


class CandleIndicators(_Section):
    interval: str = "1h"
    incomplete_count: int
    atr: Metric
    realized_volatility: Metric
    vwap: Metric
    vwap_session_volume: Metric
    momentum: tuple[MomentumMetric, ...]

    def _metrics(self):
        return (self.atr, self.realized_volatility, self.vwap, self.vwap_session_volume,
                *(m.simple_return for m in self.momentum))


class FundingContext(_Section):
    interval: str = "1h"
    latest_rate: Metric
    cumulative_funding: Metric
    mean_hourly_funding: Metric
    lookback_hours: int

    def _metrics(self):
        return (self.latest_rate, self.cumulative_funding, self.mean_hourly_funding)


class DerivativesReport(CanonicalModel):
    formula_version: str = FORMULA_VERSION
    symbol: str
    evaluation_time: datetime
    config: DerivativesConfig
    candles: CandleIndicators
    funding: FundingContext
    open_interest: Metric
    basis: Metric
    units_provider_verified: bool = False
    limitations: tuple[str, ...] = (
        UNIT_LIMITATION,
        "VWAP_IS_CANDLE_HLC3_APPROXIMATION_NOT_TRADE_VWAP",
        "CANDLE_VOLUME_READ_AS_BASE_ASSET_PROVIDER_DOCS_SILENT",
        "VOLATILITY_PER_1H_BAR_NOT_ANNUALIZED",
        "FUNDING_NOT_ANNUALIZED_NOT_PROJECTED",
        "CANDLE_FINALITY_NOT_PROVEN_BY_RECEIPT_AFTER_CLOSE",
        "NO_BACKFILL_INTERPOLATION_OR_GAP_REPAIR",
        "INDICATORS_ARE_NOT_DIRECTION_OR_SIGNAL",
    )

    @model_validator(mode="after")
    def never_fabricated(self):
        if self.units_provider_verified:
            raise ValueError("units are never provider verified")
        if UNIT_LIMITATION not in self.limitations:
            raise ValueError("caller-asserted unit limitation must remain explicit")
        if self.open_interest.value is not None or self.basis.value is not None:
            raise ValueError("open interest and basis are unavailable in C09")
        return self


def _split_known(items, expected_type, evaluation_time):
    """Receipt-time filter first: later records are counted, never read."""
    known, later = [], 0
    for item in items:
        if not isinstance(item, expected_type) or not isinstance(item.provenance, SourceProvenance):
            raise ValueError("canonical record required")
        received = item.provenance.received_timestamp
        if not isinstance(received, datetime) or received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("canonical record required")
        if received > evaluation_time:
            later += 1
        else:
            known.append(item)
    return known, later


def _assess(capability, anchor, received, behind, coverage, continuity, recovery, evaluation_time):
    """C05-compatible assessment with interval-aware freshness (C05 thresholds untouched)."""
    if not isinstance(coverage, CapabilityCoverage) or coverage.capability is not capability:
        raise ValueError("coverage capability does not match the section")
    if not isinstance(continuity, ContinuityStatus) or not isinstance(recovery, RecoveryStatus):
        raise ValueError("unknown continuity or recovery status")
    reasons: list[str] = []
    state = DataQualityState.LIVE
    if behind == 1:
        state, reasons = DataQualityState.DELAYED, ["ONE_INTERVAL_BEHIND"]
    elif behind > 1:
        state, reasons = DataQualityState.STALE, [f"{behind}_INTERVALS_BEHIND"]

    def worse(new):
        return new if _RANK[new] > _RANK[state] else state
    if coverage.availability is CapabilityAvailability.UNAVAILABLE:
        reasons.append(coverage.limitation)
        state = DataQualityState.UNAVAILABLE
    elif coverage.availability is CapabilityAvailability.LIMITED:
        reasons.append(coverage.limitation)
        state = worse(DataQualityState.DELAYED)
    if continuity is ContinuityStatus.UNKNOWN:
        reasons.append("CONTINUITY_NOT_PROVEN")
        state = worse(DataQualityState.DELAYED)
    elif continuity is ContinuityStatus.GAP_RISK:
        reasons.append("GAP_OR_CONTINUITY_RISK")
        state = worse(DataQualityState.STALE)
    if recovery is RecoveryStatus.RECOVERING:
        reasons.append("RECOVERY_IN_PROGRESS_NO_REPLAY_CLAIM")
        state = worse(DataQualityState.STALE)
    elif recovery is RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF:
        reasons.append("RECOVERY_OBSERVED_REPLAY_NOT_PROVEN")
        state = worse(DataQualityState.DELAYED)
    trusted = (state is DataQualityState.LIVE and coverage.availability is CapabilityAvailability.SUPPORTED
               and continuity is ContinuityStatus.PROVEN and recovery is RecoveryStatus.NONE)
    return QualityAssessment(
        capability=capability, state=state, coverage_availability=coverage.availability,
        coverage_limitation=coverage.limitation or None, provenance_quality=ProvenanceQuality.COMPLETE,
        freshness_basis=FreshnessBasis.SOURCE_TIMESTAMP, source_age=evaluation_time - anchor,
        receipt_age=evaluation_time - received, evaluation_time=evaluation_time,
        policy_version=FRESHNESS_POLICY_VERSION, continuity=continuity, recovery=recovery,
        reasons=tuple(reasons) or ("QUALITY_WITHIN_POLICY",), trusted_for_current_use=trusted)


def _provenance(records, rows, times, digest_algorithm) -> InputProvenance:
    """records: the retained items sorted by time; rows: their canonical field lists."""
    newest = records[-1].provenance
    return InputProvenance(
        source=newest.source, source_types=tuple(sorted({r.provenance.source_type for r in records})),
        contributing_count=len(records), earliest_time=times[0], latest_time=times[-1],
        newest_record_provenance=newest,
        input_digest=hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest(),
        digest_algorithm=digest_algorithm)


def _na(unit, reason):
    return Metric(value=None, unit=unit, reason=reason)


def _dedupe(records, key, content, blocking, conflict_reason):
    unique, duplicates = {}, 0
    for record in records:
        k = key(record)
        kept = unique.get(k)
        if kept is None:
            unique[k] = record
        elif content(kept) != content(record):
            blocking.add(conflict_reason)
        else:
            duplicates += 1
            if (record.provenance.received_timestamp, record.provenance.source_type) < (
                    kept.provenance.received_timestamp, kept.provenance.source_type):
                unique[k] = record
    return unique, duplicates


def _tail(series, count, step, start_of):
    """Last `count` records as a consecutive hourly run, or (None, reason)."""
    if len(series) < count:
        return None, f"WARMING_UP_NEED_{count}_HAVE_{len(series)}"
    tail = series[-count:]
    if any(start_of(b) - start_of(a) != step for a, b in zip(tail, tail[1:])):
        return None, "GAP_IN_LOOKBACK"
    return tail, None


def _candle_section(candles, config, coverage, evaluation_time, continuity, recovery):
    known, later = _split_known(candles, Candle, evaluation_time)
    checked = []
    for candle in known:
        candle = Candle.model_validate(candle.model_dump())
        if candle.symbol != config.symbol:
            raise ValueError("INSTRUMENT_IDENTITY_MISMATCH")
        checked.append(candle)
    # A candle observed before it closed is an incomplete snapshot, not a closed bar.
    closed = [c for c in checked if c.provenance.received_timestamp >= c.end_timestamp + MILLISECOND]
    incomplete = len(checked) - len(closed)
    blocking: set[str] = set()
    if len({c.provenance.source for c in closed}) > 1:
        blocking.add("MIXED_CANDLE_SOURCES")
    for c in closed:
        if c.end_timestamp - c.start_timestamp != CANDLE_SPAN or c.start_timestamp != _floor_hour(c.start_timestamp):
            blocking.add("CANDLE_INTERVAL_INVALID")
        if c.provenance.source_timestamp != c.start_timestamp:
            blocking.add("CANDLE_TIMESTAMP_PROVENANCE_MISMATCH")
        if not all(_bounded(v) for v in (c.open, c.high, c.low, c.close, c.volume)):
            blocking.add("NUMERIC_RANGE_UNSUPPORTED")
    unique, duplicates = {}, 0
    if not blocking:
        unique, duplicates = _dedupe(
            closed, lambda c: c.start_timestamp,
            lambda c: (c.end_timestamp, c.open, c.high, c.low, c.close, c.volume), blocking, "CANDLE_CONFLICT")
    series = sorted(unique.values(), key=lambda c: c.start_timestamp)
    unit_price = f"{config.quote_currency}"

    def section(quality, reasons, metrics, momentum, provenance=None, behind=None):
        reasons = tuple(dict.fromkeys(reasons))
        trusted = quality is not None and quality.trusted_for_current_use and not reasons
        return CandleIndicators(
            quality=quality, provenance=provenance, trusted_for_current_use=trusted, reasons=reasons,
            input_count=len(candles), duplicate_count=duplicates, not_yet_received_count=later,
            retained_count=len(series), latest_start=series[-1].start_timestamp if series else None,
            bars_behind=behind, incomplete_count=incomplete, atr=metrics[0], realized_volatility=metrics[1],
            vwap=metrics[2], vwap_session_volume=metrics[3], momentum=momentum)

    def withheld(reason):
        return (_na(unit_price, reason), _na("ln ratio per 1h bar", reason), _na(unit_price, reason),
                _na(config.base_asset, reason)), tuple(MomentumMetric(
                    lookback_bars=k, simple_return=_na("fraction", reason)) for k in config.momentum_lookbacks)

    if blocking:
        reason = sorted(blocking)[0]
        return section(None, sorted(blocking), *withheld(reason))
    if not series:
        return section(None, ["NO_CLOSED_CANDLES"], *withheld("NO_CLOSED_CANDLES"))

    latest = series[-1]
    behind = max(0, int((_expected_hour(evaluation_time, CANDLE_OFFSET) - latest.start_timestamp) / HOUR))
    quality = _assess(Capability.CANDLES, latest.end_timestamp + MILLISECOND, latest.provenance.received_timestamp,
                      behind, coverage, continuity, recovery, evaluation_time)
    rows = [[c.symbol, c.provenance.source, c.provenance.source_type, c.provenance.source_id,
             c.start_timestamp.isoformat(), c.end_timestamp.isoformat(),
             c.provenance.source_timestamp.isoformat(), c.provenance.received_timestamp.isoformat(),
             _num(c.open), _num(c.high), _num(c.low), _num(c.close), _num(c.volume)] for c in series]
    provenance = _provenance(series, rows, [c.start_timestamp for c in series], CANDLE_DIGEST)
    if not quality.trusted_for_current_use:
        return section(quality, ["DATA_QUALITY_NOT_TRUSTED", *quality.reasons],
                       *withheld("DATA_QUALITY_NOT_TRUSTED"), provenance, behind)

    start_of = lambda c: c.start_timestamp  # noqa: E731
    reasons: list[str] = []
    unit_vol = "ln(price ratio) per 1h bar, not annualized"
    try:
        with localcontext(CONTEXT):
            tail, why = _tail(series, config.atr_period + 1, HOUR, start_of)
            if tail is None:
                atr = _na(unit_price, why)
            else:
                ranges = [max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close)) for a, b in zip(tail, tail[1:])]
                atr = Metric(value=OUTPUT.plus(sum(ranges, ZERO) / config.atr_period), unit=unit_price)

            tail, why = _tail(series, config.volatility_period + 1, HOUR, start_of)
            if tail is None:
                vol = _na(unit_vol, why)
            else:
                with localcontext(LOG_CONTEXT):
                    returns = [(b.close / a.close).ln() for a, b in zip(tail, tail[1:])]
                    mean = sum(returns, ZERO) / len(returns)
                    variance = sum(((r - mean) ** 2 for r in returns), ZERO) / (len(returns) - 1)
                    vol = Metric(value=OUTPUT.plus(variance.sqrt()), unit=unit_vol)

            if config.session_start is None:
                vwap, svol = _na(unit_price, "SESSION_NOT_CONFIGURED"), _na(config.base_asset, "SESSION_NOT_CONFIGURED")
            else:
                session = [c for c in series if c.start_timestamp >= config.session_start]
                if not session:
                    vwap = _na(unit_price, "SESSION_HAS_NO_CLOSED_CANDLES")
                    svol = _na(config.base_asset, "SESSION_HAS_NO_CLOSED_CANDLES")
                elif session[0].start_timestamp != config.session_start:
                    vwap, svol = _na(unit_price, "SESSION_START_NOT_COVERED"), _na(config.base_asset, "SESSION_START_NOT_COVERED")
                elif _tail(session, len(session), HOUR, start_of)[0] is None:
                    vwap, svol = _na(unit_price, "GAP_IN_SESSION"), _na(config.base_asset, "GAP_IN_SESSION")
                else:
                    total = sum((c.volume for c in session), ZERO)
                    svol = Metric(value=OUTPUT.plus(total), unit=config.base_asset)
                    if total == 0:
                        vwap = _na(unit_price, "ZERO_SESSION_VOLUME")
                    else:
                        notional = sum((((c.high + c.low + c.close) / 3) * c.volume for c in session), ZERO)
                        vwap = Metric(value=OUTPUT.plus(notional / total), unit=unit_price)

            momentum = []
            for k in config.momentum_lookbacks:
                tail, why = _tail(series, k + 1, HOUR, start_of)
                momentum.append(MomentumMetric(lookback_bars=k, simple_return=_na("fraction", why) if tail is None else
                                               Metric(value=OUTPUT.plus(tail[-1].close / tail[0].close - 1), unit="fraction")))
    except DecimalException:
        return section(quality, ["NUMERIC_CALCULATION_UNAVAILABLE"],
                       *withheld("NUMERIC_CALCULATION_UNAVAILABLE"), provenance, behind)
    metrics = (atr, vol, vwap, svol)
    # Warm-up is an explicit metric state, not a data-quality failure; a gap is.
    if any(m.reason in GAP_REASONS for m in (*metrics, *(x.simple_return for x in momentum))):
        reasons.append("CANDLE_GAP_DETECTED")
    return section(quality, reasons, metrics, tuple(momentum), provenance, behind)


def _funding_section(funding, config, coverage, evaluation_time, continuity, recovery):
    known, later = _split_known(funding, FundingSnapshot, evaluation_time)
    checked = []
    for item in known:
        item = FundingSnapshot.model_validate(item.model_dump())
        if item.symbol != config.symbol:
            raise ValueError("INSTRUMENT_IDENTITY_MISMATCH")
        checked.append(item)
    blocking: set[str] = set()
    if len({f.provenance.source for f in checked}) > 1:
        blocking.add("MIXED_FUNDING_SOURCES")
    for f in checked:
        if f.provenance.source_timestamp != f.timestamp:
            blocking.add("FUNDING_TIMESTAMP_PROVENANCE_MISMATCH")
        if not timedelta(0) <= (f.timestamp - _floor_hour(f.timestamp)) < FUNDING_OFFSET:
            blocking.add("FUNDING_TIMESTAMP_OFF_HOURLY_SCHEDULE")
        if not _bounded(f.funding_rate):
            blocking.add("NUMERIC_RANGE_UNSUPPORTED")
        elif abs(f.funding_rate) > FUNDING_CAP:
            blocking.add("FUNDING_RATE_EXCEEDS_DOCUMENTED_CAP")
    unique, duplicates = {}, 0
    if not blocking:
        unique, duplicates = _dedupe(
            checked, lambda f: _floor_hour(f.timestamp), lambda f: (f.timestamp, f.funding_rate),
            blocking, "FUNDING_CONFLICT")
    series = sorted(unique.values(), key=lambda f: f.timestamp)
    hours = [_floor_hour(f.timestamp) for f in series]
    n = config.funding_lookback_hours

    def section(quality, reasons, metrics, provenance=None, behind=None):
        reasons = tuple(dict.fromkeys(reasons))
        trusted = quality is not None and quality.trusted_for_current_use and not reasons
        return FundingContext(
            quality=quality, provenance=provenance, trusted_for_current_use=trusted, reasons=reasons,
            input_count=len(funding), duplicate_count=duplicates, not_yet_received_count=later,
            retained_count=len(series), latest_start=hours[-1] if hours else None, bars_behind=behind,
            latest_rate=metrics[0], cumulative_funding=metrics[1], mean_hourly_funding=metrics[2],
            lookback_hours=n)

    def withheld(reason):
        return (_na(RATE_UNIT, reason), _na("fraction over lookback", reason), _na(RATE_UNIT, reason))

    if blocking:
        return section(None, sorted(blocking), withheld(sorted(blocking)[0]))
    if not series:
        return section(None, ["NO_FUNDING_OBSERVATIONS"], withheld("NO_FUNDING_OBSERVATIONS"))
    latest = series[-1]
    behind = max(0, int((_expected_hour(evaluation_time, FUNDING_OFFSET) + HOUR - hours[-1]) / HOUR))
    quality = _assess(Capability.FUNDING, hours[-1], latest.provenance.received_timestamp,
                      behind, coverage, continuity, recovery, evaluation_time)
    rows = [[f.symbol, f.provenance.source, f.provenance.source_type, f.provenance.source_id,
             f.timestamp.isoformat(), f.provenance.source_timestamp.isoformat(),
             f.provenance.received_timestamp.isoformat(), _num(f.funding_rate)] for f in series]
    provenance = _provenance(series, rows, [f.timestamp for f in series], FUNDING_DIGEST)
    if not quality.trusted_for_current_use:
        return section(quality, ["DATA_QUALITY_NOT_TRUSTED", *quality.reasons],
                       withheld("DATA_QUALITY_NOT_TRUSTED"), provenance, behind)
    tail, why = _tail(series, n, HOUR, lambda f: _floor_hour(f.timestamp))
    why = None if tail is not None else why
    with localcontext(CONTEXT):
        if tail is None:
            cumulative, mean = _na("fraction over lookback", why), _na(RATE_UNIT, why)
        else:
            total = sum((f.funding_rate for f in tail), ZERO)
            cumulative = Metric(value=OUTPUT.plus(total), unit="fraction of notional over lookback hours")
            mean = Metric(value=OUTPUT.plus(total / n), unit=RATE_UNIT)
        latest_rate = Metric(value=OUTPUT.plus(latest.funding_rate), unit=RATE_UNIT)
    reasons = ["FUNDING_GAP_DETECTED"] if why in GAP_REASONS else []
    return section(quality, reasons, (latest_rate, cumulative, mean), provenance, behind)


def analyze_derivatives(
    candles: tuple[Candle, ...], funding: tuple[FundingSnapshot, ...], *, config: DerivativesConfig,
    candle_coverage: CapabilityCoverage, funding_coverage: CapabilityCoverage,
    evaluation_time: datetime, continuity: ContinuityStatus, recovery: RecoveryStatus,
) -> DerivativesReport:
    """Closed-candle indicators and hourly funding context at an explicit time.

    Pure and deterministic: no clock, network, I/O, AI or persistent state; input
    order does not matter. Malformed canonical input, a wrong instrument or a bad
    evaluation time raises; analytically unusable input yields explicit
    unavailable metrics. ``continuity``/``recovery`` describe both input sets.
    At most 10000 records per category; larger input is rejected.
    """
    if not isinstance(candles, tuple) or not isinstance(funding, tuple) or not isinstance(config, DerivativesConfig):
        raise ValueError("tuples of canonical records and DerivativesConfig required")
    if len(candles) > MAX_RECORDS or len(funding) > MAX_RECORDS:
        raise ValueError("too many records for one analysis")
    # Revalidation also rejects model_construct/model_copy validation bypasses.
    config = DerivativesConfig.model_validate(config.model_dump())
    evaluation_time = _utc(evaluation_time, "evaluation_time")
    if config.session_start is not None and config.session_start > evaluation_time:
        raise ValueError("SESSION_START_AFTER_EVALUATION")
    return DerivativesReport(
        symbol=config.symbol, evaluation_time=evaluation_time, config=config,
        candles=_candle_section(candles, config, candle_coverage, evaluation_time, continuity, recovery),
        funding=_funding_section(funding, config, funding_coverage, evaluation_time, continuity, recovery),
        open_interest=_na("UNVERIFIED", OI_REASON), basis=_na("UNVERIFIED", BASIS_REASON))
