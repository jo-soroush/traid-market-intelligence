"""Deterministic C11 whale intelligence over a curated BTC watchlist.

Separation of evidence (guardrails §23-24, G16):

* Lifecycle comes from each fill's provider ``startPosition`` and signed size
  (side B adds, A subtracts): OPEN (0 -> non-zero), INCREASE, REDUCE, CLOSE
  (-> 0) and FLIP (sign change) are position effects. LIQUIDATION is a label
  applied only when the provider's fill ``liquidation`` marker names this wallet
  as the liquidated user; the size effect is kept beside it. A marker without a
  liquidated user is UNKNOWN; one naming another account is a counterparty fill.
  Nothing is inferred from an estimated liquidation price. OPEN therefore always
  means the provider reported a zero start, never "first fill we happened to see".
* Fills sharing one millisecond are ordered by their own startPosition chain (the
  provider ``tid`` is not chronological); a fill whose start differs from the
  previous end is a continuity gap. The provider ``dir`` text is display-only and
  only cross-checked: a contradiction makes the wallet's lifecycle CONTRADICTORY.
* Current exposure comes only from the newest snapshot received by evaluation time
  and fresh under ``max_snapshot_age``. Recent activity and realized evidence come
  only from fills inside explicit windows whose coverage a COMPLETE fill history
  proves; otherwise totals are withheld. History is never inferred from a snapshot.
* Notional is the provider ``positionValue`` (price basis undocumented); an
  entry-price notional is computed separately and labelled as C11-derived.
* Realized evidence keeps closedPnl, fees and funding apart. No combined net PnL is
  formed: their accounting composition is not verified.
* Smart Money evidence is a versioned, inspectable methodology over past closing-fill
  outcomes only. Exposure, size and notional are never inputs. Without the configured
  minimum evidence the result is INSUFFICIENT_EVIDENCE; contradictory evidence is
  UNKNOWN; a numeric score exists only with caller-configured weights (no defaults).
  It describes observed past outcomes, not predictive skill, and authorizes nothing.

Point-in-time: one explicit evaluation time T. Observations received after T are
counted and never otherwise read. Pure: no clock, network, randomness or ambient
Decimal context.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from decimal import (
    Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, localcontext,
)
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from traid.domain.models import SourceProvenance
from traid.liquidity import Metric
from traid.whales.models import (
    VERSION_PATTERN, AccountRole, Completeness, FillHistory, FundingHistory, PositionSnapshot,
    WalletFill, Watchlist, WhaleModel, canonical_json, digest, utc,
)

ENGINE_VERSION = "c11-whale-intelligence-1"
EXACT = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                traps=[Inexact, InvalidOperation, Overflow, DivisionByZero])
OUTPUT = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
MAX_OBSERVATIONS = 10000
ZERO = Decimal(0)
QUOTE = "USDC"
BASE = "BTC"
INTERPRETATION = "DESCRIBES_PAST_OBSERVED_CLOSING_FILL_OUTCOMES_NOT_PREDICTIVE_SKILL"


# ------------------------------------------------------------------------------ rules
class ScoreComponent(StrEnum):
    # wins / (wins + losses) over closing fills with non-zero closedPnl; in [0, 1]
    CLOSING_FILL_WIN_RATE = "CLOSING_FILL_WIN_RATE"
    # sum(positive closedPnl) / (sum(positive) + |sum(negative)|) over closing fills; in [0, 1]
    CLOSED_PNL_GAIN_SHARE = "CLOSED_PNL_GAIN_SHARE"


NORMALIZATION = {
    ScoreComponent.CLOSING_FILL_WIN_RATE: "wins/(wins+losses) over closing fills with non-zero closedPnl; range [0,1]",
    ScoreComponent.CLOSED_PNL_GAIN_SHARE: "sum(closedPnl>0)/(sum(closedPnl>0)+|sum(closedPnl<0)|); range [0,1]",
}


class ScoreWeight(WhaleModel):
    component: ScoreComponent
    weight: Decimal = Field(gt=0)


class SmartMoneyRules(WhaleModel):
    """Explicit methodology configuration. No weight or minimum has a default."""
    methodology_version: str = Field(min_length=1, max_length=64, pattern=VERSION_PATTERN)
    evaluation_window: timedelta = Field(gt=timedelta(0))
    min_closing_fills: int = Field(ge=1)
    weights: tuple[ScoreWeight, ...] = ()  # empty: methodology evidence only, no numeric score

    @model_validator(mode="after")
    def unique(self):
        names = [w.component.value for w in self.weights]
        if names != sorted(set(names)):
            raise ValueError("score weights must name each component once, in order")
        return self


class WhaleRules(WhaleModel):
    rules_version: str = Field(min_length=1, max_length=64, pattern=VERSION_PATTERN)
    calibration_status: Literal["UNCALIBRATED"] = "UNCALIBRATED"
    max_snapshot_age: timedelta = Field(gt=timedelta(0))
    max_history_age: timedelta = Field(gt=timedelta(0))
    activity_window: timedelta = Field(gt=timedelta(0))
    smart_money: SmartMoneyRules


# ----------------------------------------------------------------------------- output
class PositionEffect(StrEnum):
    OPEN = "OPEN"
    INCREASE = "INCREASE"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    FLIP = "FLIP"


class LifecycleLabel(StrEnum):
    OPEN = "OPEN"
    INCREASE = "INCREASE"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    FLIP = "FLIP"
    LIQUIDATION = "LIQUIDATION"
    UNKNOWN = "UNKNOWN"


class LiquidationAttribution(StrEnum):
    NONE = "NONE"                    # no provider marker
    OWN_ACCOUNT = "OWN_ACCOUNT"      # marker names this wallet as liquidated
    COUNTERPARTY = "COUNTERPARTY"    # marker names another account
    UNATTRIBUTED = "UNATTRIBUTED"    # marker without a liquidated user


class LabelCheck(StrEnum):
    CONSISTENT = "CONSISTENT"
    CONTRADICTORY = "CONTRADICTORY"
    UNRECOGNIZED = "UNRECOGNIZED"


class Continuity(StrEnum):
    FIRST_OBSERVED = "FIRST_OBSERVED"
    CHAINED = "CHAINED"
    GAP_BEFORE = "GAP_BEFORE"


class LifecycleEvent(WhaleModel):
    time: datetime
    tid: int
    oid: int
    side: Literal["B", "A"]
    size: Decimal
    price: Decimal
    start_position: Decimal
    end_position: Decimal
    position_effect: PositionEffect
    label: LifecycleLabel
    liquidation_attribution: LiquidationAttribution
    liquidation_method: Literal["market", "backstop"] | None
    provider_direction_label: str
    direction_label_check: LabelCheck
    continuity: Continuity
    closed_pnl: Decimal
    fee: Decimal
    fee_token: str

    @model_validator(mode="after")
    def label_follows_evidence(self):
        expected = {LiquidationAttribution.OWN_ACCOUNT: LifecycleLabel.LIQUIDATION,
                    LiquidationAttribution.UNATTRIBUTED: LifecycleLabel.UNKNOWN}.get(
            self.liquidation_attribution, LifecycleLabel(self.position_effect.value))
        if self.label != expected:
            raise ValueError("lifecycle label must follow the size effect and provider liquidation marker")
        if (self.liquidation_attribution is LiquidationAttribution.NONE) != (self.liquidation_method is None):
            raise ValueError("liquidation method exists exactly when a provider marker exists")
        return self


class LifecycleStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    CONTRADICTORY = "CONTRADICTORY"
    CONFLICT = "CONFLICT"
    NO_HISTORY = "NO_HISTORY"


class LifecycleEvidence(WhaleModel):
    status: LifecycleStatus
    events: tuple[LifecycleEvent, ...]
    history_completeness: Completeness | None
    history_reasons: tuple[str, ...]
    coverage_start: datetime | None        # proven only by a COMPLETE latest history
    observed_through: datetime | None      # receipt of the latest history's final page
    history_fresh: bool
    duplicate_count: int = Field(ge=0)
    continuity_gap_count: int = Field(ge=0)
    contradictory_label_count: int = Field(ge=0)
    unattributed_liquidation_count: int = Field(ge=0)
    reasons: tuple[str, ...]


class ReconciliationStatus(StrEnum):
    RECONCILED = "RECONCILED"
    UNRECONCILED = "UNRECONCILED"
    NOT_CHECKABLE = "NOT_CHECKABLE"


class Reconciliation(WhaleModel):
    status: ReconciliationStatus
    snapshot_size: Decimal | None
    implied_before: Decimal | None   # end of the last covered fill before the snapshot
    implied_after: Decimal | None    # start of the first covered fill after the snapshot
    reasons: tuple[str, ...]


class SnapshotStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class WalletExposure(WhaleModel):
    status: SnapshotStatus
    snapshot_time: datetime | None
    side: Side | None
    size: Metric
    provider_notional: Metric        # positionValue as reported; price basis undocumented
    entry_notional: Metric           # C11-derived |size| x entryPx
    unrealized_pnl: Metric           # provider-reported, as of snapshot_time
    liquidation_price_estimate: Metric
    leverage_type: Literal["cross", "isolated"] | None
    leverage: int | None
    reasons: tuple[str, ...]


class LabelCount(WhaleModel):
    label: LifecycleLabel
    count: int = Field(ge=0)


class Coverage(StrEnum):
    # COMPLETE: a fresh COMPLETE fill history proves every fill from the window start through
    # observed_through (its final page receipt); fills after observed_through are not yet known.
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class ActivitySummary(WhaleModel):
    window_start: datetime           # exclusive
    observed_through: datetime | None
    coverage: Coverage
    observed_event_counts: tuple[LabelCount, ...]  # events seen in the window (a lower bound if INCOMPLETE)
    buy_volume: Metric
    sell_volume: Metric
    traded_notional: Metric          # C11-derived sum(price x size)
    reasons: tuple[str, ...]


class PerformanceEvidence(WhaleModel):
    window_start: datetime
    coverage: Coverage
    funding_coverage: Coverage
    unrealized_pnl: Metric
    unrealized_as_of: datetime | None
    closed_pnl: Metric
    fees: Metric
    funding: Metric
    combined_net_pnl: Metric
    closing_fill_count: int | None
    winning_closing_fills: int | None
    losing_closing_fills: int | None
    flat_closing_fills: int | None
    positive_closed_pnl: Metric
    negative_closed_pnl: Metric
    reasons: tuple[str, ...]


class SmartMoneyStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class ScoreStatus(StrEnum):
    SCORED = "SCORED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class ComponentValue(WhaleModel):
    component: ScoreComponent
    value: Decimal = Field(ge=0, le=1)
    weight: Decimal | None
    normalization: str


class SmartMoneyEvidence(WhaleModel):
    methodology_version: str
    window_start: datetime
    status: SmartMoneyStatus
    components: tuple[ComponentValue, ...]
    score: Metric
    score_status: ScoreStatus
    interpretation: Literal["DESCRIBES_PAST_OBSERVED_CLOSING_FILL_OUTCOMES_NOT_PREDICTIVE_SKILL"] = INTERPRETATION
    reasons: tuple[str, ...]

    @model_validator(mode="after")
    def earned(self):
        if (self.status is SmartMoneyStatus.ELIGIBLE) != bool(self.components):
            raise ValueError("components exist exactly for eligible evidence")
        if (self.score_status is ScoreStatus.SCORED) != (self.score.value is not None):
            raise ValueError("a score value exists exactly when scored")
        if self.score_status is ScoreStatus.SCORED and (
                self.status is not SmartMoneyStatus.ELIGIBLE or any(c.weight is None for c in self.components)):
            raise ValueError("only eligible evidence with configured weights can be scored")
        if self.status is not SmartMoneyStatus.ELIGIBLE and not self.reasons:
            raise ValueError("ineligible evidence requires a reason")
        return self


class WalletReport(WhaleModel):
    address: str
    label: str
    account_role: AccountRole | None
    snapshot_status: SnapshotStatus
    snapshot: PositionSnapshot | None
    exposure: WalletExposure
    lifecycle: LifecycleEvidence
    reconciliation: Reconciliation
    activity: ActivitySummary
    performance: PerformanceEvidence
    smart_money: SmartMoneyEvidence


class AggregateExposure(WhaleModel):
    scope: Literal["CURATED_WATCHLIST_SAMPLE"] = "CURATED_WATCHLIST_SAMPLE"
    coverage: Literal["COMPLETE", "PARTIAL", "NONE"]
    watchlist_size: int
    wallets_available: int
    wallets_stale: int
    wallets_missing: int
    wallets_conflict: int
    long_wallets: int                # informational counts; never a capital weight
    short_wallets: int
    flat_wallets: int
    long_size: Metric
    short_size: Metric
    long_notional: Metric            # sums of provider positionValue over AVAILABLE wallets
    short_notional: Metric
    gross_notional: Metric
    net_notional: Metric
    largest_wallet_share: Metric
    concentration_hhi: Metric
    earliest_snapshot_time: datetime | None
    latest_snapshot_time: datetime | None
    reasons: tuple[str, ...]


class ExcludedCounts(WhaleModel):
    """Observations received after the evaluation time: counted, never read."""
    snapshots: int = Field(ge=0)
    fill_histories: int = Field(ge=0)
    funding_histories: int = Field(ge=0)


class WhaleReport(WhaleModel):
    engine_version: str = ENGINE_VERSION
    evaluation_time: datetime
    watchlist_version: str
    watchlist_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    rules: WhaleRules
    rules_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    wallets: tuple[WalletReport, ...]
    aggregate: AggregateExposure
    excluded_after_evaluation: ExcludedCounts
    limitations: tuple[str, ...] = (
        "NOT_TRADE_AUTHORIZATION_OR_SIGNAL",
        "CURATED_SAMPLE_NOT_EXCHANGE_TOTAL",
        "LARGE_WALLET_IS_NOT_SMART_MONEY",
        "PAST_OUTCOMES_ARE_NOT_PREDICTIVE_SKILL",
        "PNL_COMPONENTS_NOT_COMBINED_ACCOUNTING_COMPOSITION_UNVERIFIED",
        "PROVIDER_EXPOSES_ONLY_10000_MOST_RECENT_FILLS",
        "LIQUIDATION_ONLY_FROM_PROVIDER_FILL_MARKER_NEVER_FROM_ESTIMATED_PRICE",
        "NOTIONAL_IS_PROVIDER_POSITION_VALUE_PRICE_BASIS_UNDOCUMENTED",
        "QUOTE_UNITS_USDC_MARGINED_PERP_NOT_DOCUMENTED_PER_FIELD",
        "THRESHOLDS_AND_WEIGHTS_UNCALIBRATED_CALLER_CONFIGURED",
    )

    @model_validator(mode="after")
    def bound(self):
        if self.rules_digest != digest(self.rules):
            raise ValueError("rules digest does not match the rules")
        addresses = [w.address for w in self.wallets]
        if addresses != sorted(set(addresses)) or len(addresses) != self.aggregate.watchlist_size:
            raise ValueError("one report per watchlist wallet, ordered by address")
        return self


# ---------------------------------------------------------------------------- helpers
def _na(unit, reason) -> Metric:
    return Metric(value=None, unit=unit, reason=reason)


def _m(value, unit) -> Metric:
    return Metric(value=value, unit=unit)


def _sum(values) -> Decimal:
    with localcontext(EXACT):
        return sum(values, ZERO)


def _received(obj, cls) -> datetime:
    """Only the receipt time is read before deciding whether an observation was knowable."""
    p = getattr(obj, "provenance", None)
    received = getattr(p, "received_timestamp", None)
    if type(obj) is not cls or type(p) is not SourceProvenance or not isinstance(received, datetime) \
            or received.tzinfo is None or received.utcoffset() is None:
        raise ValueError(f"canonical {cls.__name__} with a timezone-aware receipt time required")
    return received


def _effect(start: Decimal, end: Decimal) -> PositionEffect:
    if start == 0:
        return PositionEffect.OPEN
    if end == 0:
        return PositionEffect.CLOSE
    if (start > 0) != (end > 0):
        return PositionEffect.FLIP
    return PositionEffect.INCREASE if end.copy_abs() > start.copy_abs() else PositionEffect.REDUCE


# Provider `dir` text (observed live: Open/Close Long/Short, "Long > Short", "Short > Long").
_DIRECTION = {
    "Open Long": lambda s, e: s >= 0 and e > 0,
    "Open Short": lambda s, e: s <= 0 and e < 0,
    "Close Long": lambda s, e: s > 0 and e >= 0,
    "Close Short": lambda s, e: s < 0 and e <= 0,
    "Long > Short": lambda s, e: s > 0 and e < 0,
    "Short > Long": lambda s, e: s < 0 and e > 0,
}


def _attribution(fill: WalletFill) -> LiquidationAttribution:
    if fill.liquidation is None:
        return LiquidationAttribution.NONE
    if fill.liquidation.liquidated_user is None:
        return LiquidationAttribution.UNATTRIBUTED
    if fill.liquidation.liquidated_user == fill.address:
        return LiquidationAttribution.OWN_ACCOUNT
    return LiquidationAttribution.COUNTERPARTY


def _chain_order(fills: list[WalletFill]) -> list[WalletFill]:
    """Time order; within one millisecond, follow the startPosition chain (tid is not chronological)."""
    ordered: list[WalletFill] = []
    current = None
    by_time: dict[datetime, list[WalletFill]] = {}
    for f in fills:
        by_time.setdefault(f.time, []).append(f)
    for t in sorted(by_time):
        remaining = sorted(by_time[t], key=lambda f: (f.tid, f.oid))
        while remaining:
            pick = next((f for f in remaining if current is not None and f.start_position == current), None)
            if pick is None:
                ends = {f.end_position for f in remaining}
                heads = [f for f in remaining if f.start_position not in ends]
                pick = (heads or remaining)[0]
            ordered.append(pick)
            remaining.remove(pick)
            current = pick.end_position
    return ordered


def _latest(histories):
    return max(histories, key=lambda h: (h.provenance.received_timestamp, canonical_json(h.model_dump(mode="python"))))


# -------------------------------------------------------------------------- lifecycle
def _lifecycle(histories: list[FillHistory], T, rules: WhaleRules) -> LifecycleEvidence:
    if not histories:
        return LifecycleEvidence(
            status=LifecycleStatus.NO_HISTORY, events=(), history_completeness=None, history_reasons=(),
            coverage_start=None, observed_through=None, history_fresh=False, duplicate_count=0,
            continuity_gap_count=0, contradictory_label_count=0, unattributed_liquidation_count=0,
            reasons=("NO_FILL_HISTORY_KNOWN_AT_EVALUATION",))
    latest = _latest(histories)
    received = latest.provenance.received_timestamp
    fresh = T - received <= rules.max_history_age
    complete = latest.completeness is Completeness.COMPLETE
    groups: dict[tuple[int, int], list[WalletFill]] = {}
    for h in histories:
        for f in h.fills:
            groups.setdefault(f.identity, []).append(f)
    duplicates, conflicted, fills = 0, False, []
    for key in sorted(groups):
        group = groups[key]
        if any(f != group[0] for f in group):   # value equality: 1.0 == 1.00
            conflicted = True
            continue
        duplicates += len(group) - 1
        fills.append(min(group, key=lambda f: canonical_json(f.model_dump(mode="python"))))
    common = dict(history_completeness=latest.completeness, history_reasons=latest.reasons,
                  coverage_start=latest.requested_start if complete else None, observed_through=received,
                  history_fresh=fresh, duplicate_count=duplicates)
    if conflicted:
        return LifecycleEvidence(status=LifecycleStatus.CONFLICT, events=(), continuity_gap_count=0,
                                 contradictory_label_count=0, unattributed_liquidation_count=0,
                                 reasons=("CONFLICTING_FILLS_FOR_ONE_IDENTITY",), **common)
    ordered = _chain_order(fills)
    events, previous = [], None
    for f in ordered:
        end = f.end_position
        effect = _effect(f.start_position, end)
        attribution = _attribution(f)
        rule = _DIRECTION.get(f.direction_label)
        check = (LabelCheck.UNRECOGNIZED if rule is None else
                 LabelCheck.CONSISTENT if rule(f.start_position, end) else LabelCheck.CONTRADICTORY)
        continuity = (Continuity.FIRST_OBSERVED if previous is None else
                      Continuity.CHAINED if f.start_position == previous else Continuity.GAP_BEFORE)
        label = {LiquidationAttribution.OWN_ACCOUNT: LifecycleLabel.LIQUIDATION,
                 LiquidationAttribution.UNATTRIBUTED: LifecycleLabel.UNKNOWN}.get(attribution, LifecycleLabel(effect.value))
        events.append(LifecycleEvent(
            time=f.time, tid=f.tid, oid=f.oid, side=f.side, size=f.size, price=f.price,
            start_position=f.start_position, end_position=end, position_effect=effect, label=label,
            liquidation_attribution=attribution,
            liquidation_method=None if f.liquidation is None else f.liquidation.method,
            provider_direction_label=f.direction_label, direction_label_check=check, continuity=continuity,
            closed_pnl=f.closed_pnl, fee=f.fee, fee_token=f.fee_token))
        previous = end
    gaps = sum(e.continuity is Continuity.GAP_BEFORE for e in events)
    contradictory = sum(e.direction_label_check is LabelCheck.CONTRADICTORY for e in events)
    unattributed = sum(e.liquidation_attribution is LiquidationAttribution.UNATTRIBUTED for e in events)
    reasons = []
    if contradictory:
        reasons.append(f"PROVIDER_DIRECTION_LABEL_CONTRADICTS_SIZE_CHANGE:{contradictory}")
    if gaps:
        reasons.append(f"CONTINUITY_GAPS:{gaps}")
    if unattributed:
        reasons.append(f"LIQUIDATION_MARKER_WITHOUT_LIQUIDATED_USER:{unattributed}")
    if not complete:
        reasons.append("FILL_HISTORY_INCOMPLETE")
    if not fresh:
        reasons.append("FILL_HISTORY_STALE")
    if any(e.direction_label_check is LabelCheck.UNRECOGNIZED for e in events):
        reasons.append("PROVIDER_DIRECTION_LABEL_UNRECOGNIZED")
    status = LifecycleStatus.CONTRADICTORY if contradictory else LifecycleStatus.AVAILABLE
    return LifecycleEvidence(status=status, events=tuple(events), continuity_gap_count=gaps,
                             contradictory_label_count=contradictory, unattributed_liquidation_count=unattributed,
                             reasons=tuple(reasons), **common)


def _covers(lifecycle: LifecycleEvidence, start: datetime) -> bool:
    """A window (start, T] is covered only by a fresh COMPLETE history that began at or before start."""
    return (lifecycle.status in (LifecycleStatus.AVAILABLE, LifecycleStatus.CONTRADICTORY)
            and lifecycle.coverage_start is not None and lifecycle.coverage_start <= start and lifecycle.history_fresh)


def _reconcile(snapshot: PositionSnapshot | None, lifecycle: LifecycleEvidence) -> Reconciliation:
    def unknown(reason, size=None):
        return Reconciliation(status=ReconciliationStatus.NOT_CHECKABLE, snapshot_size=size, implied_before=None,
                              implied_after=None, reasons=(reason,))
    if snapshot is None:
        return unknown("NO_SNAPSHOT")
    size = ZERO if snapshot.btc_position is None else snapshot.btc_position.size
    if lifecycle.status not in (LifecycleStatus.AVAILABLE, LifecycleStatus.CONTRADICTORY):
        return unknown(f"LIFECYCLE_{lifecycle.status.value}", size)
    ts = snapshot.snapshot_time
    if lifecycle.coverage_start is None or not lifecycle.coverage_start <= ts <= lifecycle.observed_through:
        return unknown("SNAPSHOT_OUTSIDE_COMPLETE_FILL_COVERAGE", size)
    covered = [e for e in lifecycle.events if lifecycle.coverage_start <= e.time <= lifecycle.observed_through]
    if any(e.time == ts for e in covered):
        return unknown("FILL_AT_SNAPSHOT_MILLISECOND_ORDER_UNKNOWN", size)
    before = [e for e in covered if e.time < ts]
    after = [e for e in covered if e.time > ts]
    implied_before = before[-1].end_position if before else None
    implied_after = after[0].start_position if after else None
    if implied_before is None and implied_after is None:
        return unknown("NO_COVERED_FILLS_AROUND_SNAPSHOT", size)
    mismatched = [v for v in (implied_before, implied_after) if v is not None and v != size]
    return Reconciliation(
        status=ReconciliationStatus.UNRECONCILED if mismatched else ReconciliationStatus.RECONCILED,
        snapshot_size=size, implied_before=implied_before, implied_after=implied_after,
        reasons=("SNAPSHOT_SIZE_DIFFERS_FROM_FILL_CHAIN",) if mismatched else ())


# --------------------------------------------------------------------------- exposure
def _select_snapshot(snapshots: list[PositionSnapshot], T, rules: WhaleRules):
    if not snapshots:
        return SnapshotStatus.MISSING, None, ("NO_SNAPSHOT_KNOWN_AT_EVALUATION",)
    newest = max(s.snapshot_time for s in snapshots)
    group = [s for s in snapshots if s.snapshot_time == newest]
    if len({canonical_json(s.model_dump(mode="python", exclude={"provenance"})) for s in group}) > 1:
        return SnapshotStatus.CONFLICT, None, ("CONFLICTING_SNAPSHOTS_AT_ONE_PROVIDER_TIME",)
    chosen = min(group, key=lambda s: (s.provenance.received_timestamp, canonical_json(s.model_dump(mode="python"))))
    if T - newest > rules.max_snapshot_age:
        return SnapshotStatus.STALE, chosen, ("SNAPSHOT_STALE",)
    return SnapshotStatus.FRESH, chosen, ()


def _exposure(status, snapshot, reasons) -> WalletExposure:
    if status is not SnapshotStatus.FRESH:
        why = reasons[0]
        return WalletExposure(
            status=status, snapshot_time=None if snapshot is None else snapshot.snapshot_time, side=None,
            size=_na(BASE, why), provider_notional=_na(QUOTE, why), entry_notional=_na(QUOTE, why),
            unrealized_pnl=_na(QUOTE, why), liquidation_price_estimate=_na(f"{QUOTE}/{BASE}", why),
            leverage_type=None, leverage=None, reasons=reasons)
    p = snapshot.btc_position
    if p is None:
        flat = "NO_BTC_POSITION_REPORTED"
        return WalletExposure(
            status=status, snapshot_time=snapshot.snapshot_time, side=Side.FLAT, size=_m(ZERO, BASE),
            provider_notional=_m(ZERO, QUOTE), entry_notional=_m(ZERO, QUOTE), unrealized_pnl=_m(ZERO, QUOTE),
            liquidation_price_estimate=_na(f"{QUOTE}/{BASE}", flat), leverage_type=None, leverage=None, reasons=())
    with localcontext(EXACT):
        entry = p.size.copy_abs() * p.entry_price
    return WalletExposure(
        status=status, snapshot_time=snapshot.snapshot_time, side=Side.LONG if p.size > 0 else Side.SHORT,
        size=_m(p.size, BASE), provider_notional=_m(p.position_value, QUOTE),
        entry_notional=_m(entry, f"{QUOTE} at entry price (C11-derived)"),
        unrealized_pnl=_m(p.unrealized_pnl, QUOTE),
        liquidation_price_estimate=(_na(f"{QUOTE}/{BASE}", "PROVIDER_REPORTED_NO_LIQUIDATION_PRICE")
                                    if p.liquidation_price is None else _m(p.liquidation_price, f"{QUOTE}/{BASE} (provider estimate)")),
        leverage_type=p.leverage_type, leverage=p.leverage, reasons=())


def _aggregate(watchlist: Watchlist, wallets: list[WalletReport]) -> AggregateExposure:
    statuses = Counter(w.exposure.status for w in wallets)
    available = [w.exposure for w in wallets if w.exposure.status is SnapshotStatus.FRESH]
    longs = [e for e in available if e.side is Side.LONG]
    shorts = [e for e in available if e.side is Side.SHORT]
    reasons = []
    if not available:
        reasons.append("NO_FRESH_WALLET_SNAPSHOT")
        none = "NO_FRESH_WALLET_SNAPSHOT"
        metrics = dict(long_size=_na(BASE, none), short_size=_na(BASE, none), long_notional=_na(QUOTE, none),
                       short_notional=_na(QUOTE, none), gross_notional=_na(QUOTE, none), net_notional=_na(QUOTE, none),
                       largest_wallet_share=_na("fraction of sample gross notional", none),
                       concentration_hhi=_na("sum of squared shares", none))
    else:
        long_n = _sum(e.provider_notional.value for e in longs)
        short_n = _sum(e.provider_notional.value for e in shorts)
        with localcontext(EXACT):
            gross, net = long_n + short_n, long_n - short_n
        metrics = dict(long_size=_m(_sum(e.size.value for e in longs), BASE),
                       short_size=_m(_sum(e.size.value for e in shorts), BASE),
                       long_notional=_m(long_n, QUOTE), short_notional=_m(short_n, QUOTE),
                       gross_notional=_m(gross, QUOTE), net_notional=_m(net, QUOTE))
        if gross == 0:
            why = "NO_GROSS_EXPOSURE_IN_SAMPLE"
            metrics.update(largest_wallet_share=_na("fraction of sample gross notional", why),
                           concentration_hhi=_na("sum of squared shares", why))
        else:
            with localcontext(OUTPUT):
                shares = [e.provider_notional.value / gross for e in available]
                hhi = sum((s * s for s in shares), ZERO)
            metrics.update(largest_wallet_share=_m(max(shares), "fraction of sample gross notional"),
                           concentration_hhi=_m(hhi, "sum of squared shares"))
    if len(available) < len(wallets):
        reasons.append("PARTIAL_WATCHLIST_COVERAGE")
    times = [e.snapshot_time for e in available]
    return AggregateExposure(
        coverage="COMPLETE" if len(available) == len(wallets) else "PARTIAL" if available else "NONE",
        watchlist_size=len(watchlist.entries), wallets_available=len(available),
        wallets_stale=statuses[SnapshotStatus.STALE], wallets_missing=statuses[SnapshotStatus.MISSING],
        wallets_conflict=statuses[SnapshotStatus.CONFLICT], long_wallets=len(longs), short_wallets=len(shorts),
        flat_wallets=sum(e.side is Side.FLAT for e in available),
        earliest_snapshot_time=min(times) if times else None, latest_snapshot_time=max(times) if times else None,
        reasons=tuple(reasons), **metrics)


# ------------------------------------------------------------------ activity and PnL
def _window(events, start, T):
    return [e for e in events if start < e.time <= T]


def _activity(lifecycle: LifecycleEvidence, T, rules: WhaleRules) -> ActivitySummary:
    start = T - rules.activity_window
    events = _window(lifecycle.events, start, T)
    counts = Counter(e.label for e in events)
    observed = tuple(LabelCount(label=label, count=counts[label]) for label in LifecycleLabel)
    covered = _covers(lifecycle, start)
    reasons = [] if covered else ["FILL_HISTORY_DOES_NOT_COVER_WINDOW"]
    if covered:
        buy = _sum(e.size for e in events if e.side == "B")
        sell = _sum(e.size for e in events if e.side == "A")
        with localcontext(EXACT):
            notional = _sum(e.price * e.size for e in events)
        volumes = (_m(buy, BASE), _m(sell, BASE), _m(notional, f"{QUOTE} (C11-derived price x size)"))
    else:
        why = reasons[0]
        volumes = (_na(BASE, why), _na(BASE, why), _na(QUOTE, why))
    return ActivitySummary(window_start=start, observed_through=lifecycle.observed_through,
                           coverage=Coverage.COMPLETE if covered else Coverage.INCOMPLETE,
                           observed_event_counts=observed, buy_volume=volumes[0], sell_volume=volumes[1],
                           traded_notional=volumes[2], reasons=tuple(reasons))


CLOSING = (PositionEffect.REDUCE, PositionEffect.CLOSE, PositionEffect.FLIP)


def _performance(lifecycle, funding_histories: list[FundingHistory], exposure: WalletExposure, T,
                 rules: WhaleRules) -> PerformanceEvidence:
    start = T - rules.smart_money.evaluation_window
    covered = _covers(lifecycle, start)
    reasons = []
    unrealized = exposure.unrealized_pnl
    if covered:
        events = _window(lifecycle.events, start, T)
        closing = [e for e in events if e.position_effect in CLOSING]
        positive = [e.closed_pnl for e in closing if e.closed_pnl > 0]
        negative = [e.closed_pnl for e in closing if e.closed_pnl < 0]
        closed = _m(_sum(e.closed_pnl for e in events), f"{QUOTE} (provider closedPnl; fee treatment unverified)")
        fee_tokens = {e.fee_token for e in events}
        fees = (_m(_sum(e.fee for e in events), f"{QUOTE} (provider fee; negative is rebate)")
                if fee_tokens <= {QUOTE} else _na(QUOTE, "MIXED_OR_NON_USDC_FEE_TOKENS"))
        counts = dict(closing_fill_count=len(closing), winning_closing_fills=len(positive),
                      losing_closing_fills=len(negative), flat_closing_fills=len(closing) - len(positive) - len(negative))
        pos, neg = _m(_sum(positive), QUOTE), _m(_sum(negative), QUOTE)
    else:
        why = "FILL_HISTORY_DOES_NOT_COVER_WINDOW"
        reasons.append(why)
        closed, fees, pos, neg = _na(QUOTE, why), _na(QUOTE, why), _na(QUOTE, why), _na(QUOTE, why)
        counts = dict(closing_fill_count=None, winning_closing_fills=None, losing_closing_fills=None,
                      flat_closing_fills=None)
    funding_covered = False
    if funding_histories:
        latest = _latest(funding_histories)
        funding_covered = (latest.completeness is Completeness.COMPLETE and latest.requested_start <= start
                           and T - latest.provenance.received_timestamp <= rules.max_history_age)
    by_time: dict[datetime, list] = {}
    for h in funding_histories:
        for f in h.funding:
            by_time.setdefault(f.time, []).append(f)
    conflicting = any(any(f != group[0] for f in group) for group in by_time.values())
    if funding_covered and conflicting:
        funding = _na(QUOTE, "CONFLICTING_FUNDING_ENTRIES")
        reasons.append("CONFLICTING_FUNDING_ENTRIES")
    elif funding_covered:  # one settlement per provider time; equal repeats count once
        funding = _m(_sum(group[0].usdc for t, group in by_time.items() if start < t <= T),
                     f"{QUOTE} (provider userFunding usdc, sign as reported)")
    else:
        funding = _na(QUOTE, "FUNDING_HISTORY_DOES_NOT_COVER_WINDOW")
        reasons.append("FUNDING_HISTORY_DOES_NOT_COVER_WINDOW")
    return PerformanceEvidence(
        window_start=start, coverage=Coverage.COMPLETE if covered else Coverage.INCOMPLETE,
        funding_coverage=Coverage.COMPLETE if funding_covered else Coverage.INCOMPLETE,
        unrealized_pnl=unrealized, unrealized_as_of=exposure.snapshot_time if unrealized.value is not None else None,
        closed_pnl=closed, fees=fees, funding=funding,
        combined_net_pnl=_na(QUOTE, "ACCOUNTING_COMPOSITION_UNVERIFIED"),
        positive_closed_pnl=pos, negative_closed_pnl=neg, reasons=tuple(reasons), **counts)


def _smart_money(lifecycle, reconciliation, performance: PerformanceEvidence, T, rules: WhaleRules) -> SmartMoneyEvidence:
    sm = rules.smart_money
    start = T - sm.evaluation_window
    weights = {w.component: w.weight for w in sm.weights}

    def result(status, reasons, components=(), score=None):
        score_status = (ScoreStatus.SCORED if score is not None else
                        ScoreStatus.NOT_CONFIGURED if status is SmartMoneyStatus.ELIGIBLE else ScoreStatus.NOT_ELIGIBLE)
        unit = "weighted mean of normalized components in [0,1]; methodology output, not truth"
        return SmartMoneyEvidence(
            methodology_version=sm.methodology_version, window_start=start, status=status,
            components=tuple(components), score=_m(score, unit) if score is not None else _na(unit, (
                reasons[0] if reasons else "NO_WEIGHTS_CONFIGURED")),
            score_status=score_status, reasons=tuple(reasons))
    if lifecycle.status in (LifecycleStatus.CONFLICT, LifecycleStatus.CONTRADICTORY):
        return result(SmartMoneyStatus.UNKNOWN, [f"LIFECYCLE_{lifecycle.status.value}"])
    if reconciliation.status is ReconciliationStatus.UNRECONCILED:
        return result(SmartMoneyStatus.UNKNOWN, ["POSITION_SNAPSHOT_UNRECONCILED_WITH_FILLS"])
    if performance.coverage is not Coverage.COMPLETE:
        return result(SmartMoneyStatus.INSUFFICIENT_EVIDENCE, ["FILL_HISTORY_DOES_NOT_COVER_EVALUATION_WINDOW"])
    if performance.closing_fill_count < sm.min_closing_fills:
        return result(SmartMoneyStatus.INSUFFICIENT_EVIDENCE,
                      [f"CLOSING_FILLS_BELOW_MINIMUM:{performance.closing_fill_count}<{sm.min_closing_fills}"])
    wins, losses = performance.winning_closing_fills, performance.losing_closing_fills
    gains, loss_total = performance.positive_closed_pnl.value, performance.negative_closed_pnl.value.copy_abs()
    if wins + losses == 0:
        return result(SmartMoneyStatus.INSUFFICIENT_EVIDENCE, ["NO_CLOSING_FILL_WITH_NONZERO_CLOSED_PNL"])
    with localcontext(OUTPUT):
        values = {ScoreComponent.CLOSING_FILL_WIN_RATE: Decimal(wins) / Decimal(wins + losses),
                  ScoreComponent.CLOSED_PNL_GAIN_SHARE: gains / (gains + loss_total)}
    components = [ComponentValue(component=c, value=values[c], weight=weights.get(c), normalization=NORMALIZATION[c])
                  for c in ScoreComponent]
    score = None
    if weights:
        with localcontext(OUTPUT):
            score = sum((values[c] * w for c, w in weights.items()), ZERO) / sum(weights.values(), ZERO)
    return result(SmartMoneyStatus.ELIGIBLE, [], components, score)


# -------------------------------------------------------------------------------- API
def analyze_whales(
    *, evaluation_time: datetime, watchlist: Watchlist, rules: WhaleRules,
    snapshots: tuple[PositionSnapshot, ...] = (), fill_histories: tuple[FillHistory, ...] = (),
    funding_histories: tuple[FundingHistory, ...] = (),
) -> WhaleReport:
    """Whale state, lifecycle, exposure, activity and methodology evidence at time T.

    Observations received after T are counted and never otherwise read; the rest are
    revalidated and must belong to watchlist wallets. Malformed input raises.
    """
    if type(watchlist) is not Watchlist or type(rules) is not WhaleRules:
        raise ValueError("Watchlist and WhaleRules required")
    for items in (snapshots, fill_histories, funding_histories):
        if not isinstance(items, tuple) or len(items) > MAX_OBSERVATIONS:
            raise ValueError("bounded tuples of observations required")
    T = utc(evaluation_time, "evaluation_time")
    watchlist = Watchlist.model_validate(watchlist.model_dump())
    rules = WhaleRules.model_validate(rules.model_dump())
    members = {e.address for e in watchlist.entries}
    known: dict[type, dict[str, list]] = {}
    excluded = Counter()
    for cls, items in ((PositionSnapshot, snapshots), (FillHistory, fill_histories), (FundingHistory, funding_histories)):
        per_wallet = known.setdefault(cls, {a: [] for a in members})
        for item in items:
            if _received(item, cls) > T:
                excluded[cls] += 1
                continue
            item = cls.model_validate(item.model_dump())
            if item.address not in members:
                raise ValueError("WALLET_NOT_IN_WATCHLIST")
            per_wallet[item.address].append(item)

    wallets = []
    for entry in watchlist.entries:
        a = entry.address
        status, snapshot, snap_reasons = _select_snapshot(known[PositionSnapshot][a], T, rules)
        exposure = _exposure(status, snapshot, snap_reasons)
        lifecycle = _lifecycle(known[FillHistory][a], T, rules)
        reconciliation = _reconcile(snapshot if status is not SnapshotStatus.CONFLICT else None, lifecycle)
        performance = _performance(lifecycle, known[FundingHistory][a], exposure, T, rules)
        smart = _smart_money(lifecycle, reconciliation, performance, T, rules)
        wallets.append(WalletReport(
            address=a, label=entry.label, account_role=entry.account_role, snapshot_status=status,
            snapshot=snapshot, exposure=exposure, lifecycle=lifecycle, reconciliation=reconciliation,
            activity=_activity(lifecycle, T, rules), performance=performance, smart_money=smart))
    return WhaleReport(
        evaluation_time=T, watchlist_version=watchlist.watchlist_version, watchlist_digest=watchlist.digest(),
        rules=rules, rules_digest=digest(rules), wallets=tuple(wallets), aggregate=_aggregate(watchlist, wallets),
        excluded_after_evaluation=ExcludedCounts(snapshots=excluded[PositionSnapshot],
                                                 fill_histories=excluded[FillHistory],
                                                 funding_histories=excluded[FundingHistory]))
