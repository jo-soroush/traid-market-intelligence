"""Deterministic evidence selection: from C10-C13 reports at one evaluation time T to one request.

Code decides everything here; the model decides nothing. Per report: exact type and engine version
(R1), ``evaluation_time == T`` including nested C13 times (R2), and identity (R3: C10 symbol exactly
``BTC`` or ``BTC-USD``, ETF asset ``BTC``, C11 BTC by engine constant). Per field: only eligible values
become ``BoundValue``; an ineligible value never enters the request and its item carries only the
reason in ``values_withheld``. Time fields follow one closed classification (F3); a time not listed is
not sent. C11 is released only as one gated gross notional or as the constant
``WHALE_EVIDENCE_NOT_RELEASED`` (F5). Reports are read, never modified.

T1 (BTC market state) is anchored on classified C10 dimensions and the composite regime; T2 (macro
context) on eligible C12 series and a CURRENT FOMC statement, with eligible ETF evidence as optional
context only. No anchor: AI_NOT_REQUESTED, no call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from traid.ai.grammar import Bound, is_literal_candidate
from traid.ai.models import (
    AIInterpretationRequest, Anchor, AssessedClaim, Attribute, BoundValue, Category, CategoryState, CategoryStatus,
    CitationView, EvidenceItem, ExcludedItem, FactEntry, FrameView, HandleSource, PrivateBindings, ReportDigest,
    RequiredSections, TaskId, Tier, TimedValue, TimeKind, UnavailableEntry, aware_utc, render_time,
)
from traid.ai.prompts import PROMPT_DIGEST, PROMPT_ID, SCHEMA_DIGEST, SCHEMA_ID
from traid.macro.etf import ENGINE_VERSION as C12_ETF_VERSION, AssetEtfMapping, EtfEvidenceReport, EtfFund
from traid.macro.evidence import ENGINE_VERSION as C12_MACRO_VERSION, Freshness, MacroEvidenceReport
from traid.macro.models import BLS_SERIES, digest as c12_digest
from traid.news.macro_adapter import SCHEDULE_CONFLICT_PREFIXES
from traid.news.models import ENGINE_VERSION as C13_VERSION, MACRO_FRAMES, FrameType, VerificationReport
from traid.regime.engine import ENGINE_VERSION as C10_VERSION, MarketStateReport
from traid.whales.analytics import ENGINE_VERSION as C11_VERSION, Side, SnapshotStatus, WhaleReport

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")
EXACT = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)

SELECTION_POLICY_ID = "c14-selection-1"
MAX_REQUEST_BYTES = 128 * 1024
MAX_ASSESSED_CLAIMS = 8          # = TaskOutput.claim_notes capacity
MAX_ANCHORS = 6                  # = TaskOutput.anchor_assessments capacity
MIN_WHALE_CONTRIBUTORS = 5
ACCEPTED_C10_SYMBOLS = {"BTC": "BTC", "BTC-USD": "BTC"}     # closed table: no trimming, no case-folding
C10_DIMENSIONS = ("direction", "volatility", "liquidity", "flow", "funding")
WHALE_NOT_RELEASED = "WHALE_EVIDENCE_NOT_RELEASED"
SYNTHETIC_MARKER = "SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED"
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.:/\-]*$")
BTC_FRAMES = frozenset({FrameType.REG_DOC, FrameType.REG_EVENT, FrameType.REG_STATUS_AT,
                        FrameType.REG_CURRENT_STATUS, FrameType.LATEST_IDENTITY})
# C11 limitation strings, copied from the C11 engine's constant default, never from a report instance.
C11_LIMITATIONS = WhaleReport.model_fields["limitations"].default
INTERPRETATION_LIMITATIONS = ("AI_INTERPRETATION_IS_NOT_VERIFIED_FACT", "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION",
                              "NUMERIC_CHECK_IS_LEXICAL_NOT_SEMANTIC")
POLICY = {
    "policy": SELECTION_POLICY_ID, "max_request_bytes": MAX_REQUEST_BYTES, "max_assessed_claims": MAX_ASSESSED_CLAIMS,
    "min_whale_contributors": MIN_WHALE_CONTRIBUTORS, "whale_dominance": "2*max<=gross",
    "c10_symbols": sorted(ACCEPTED_C10_SYMBOLS), "c10_dimensions": list(C10_DIMENSIONS),
    "engines": [C10_VERSION, C11_VERSION, C12_MACRO_VERSION, C12_ETF_VERSION, C13_VERSION],
}
SELECTION_POLICY_DIGEST = hashlib.sha256(json.dumps(POLICY, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class EvidenceInputs:
    """The reports, all evaluated at the same T by their unchanged engines. Any may be absent."""
    market_state: MarketStateReport | None = None
    whales: WhaleReport | None = None
    macro: MacroEvidenceReport | None = None
    etf: EtfEvidenceReport | None = None
    etf_mapping: AssetEtfMapping | None = None
    news: VerificationReport | None = None


@dataclass(frozen=True)
class RequestContext:
    """What validation needs about the request; derived by code, never by the model."""
    task_id: TaskId
    items: dict[str, EvidenceItem]
    claims: dict[str, AssessedClaim]
    facts: dict[str, tuple[str, FactEntry]]
    anchors: dict[str, Anchor]
    values: dict[str, Bound]
    literals: dict[str, frozenset[str]]
    global_literals: frozenset[str]
    categories: dict[Category, CategoryState]
    source_keys: dict[str, frozenset[str]]
    engine_versions: dict[Category, str]
    unavailable: tuple[UnavailableEntry, ...]


@dataclass(frozen=True)
class Selection:
    task_id: str
    evaluation_time: datetime | None
    skip: tuple[str, ...] | None
    request: AIInterpretationRequest | None
    request_json: str | None
    request_sha256: str | None
    excluded: tuple[ExcludedItem, ...]
    bindings: PrivateBindings
    context: RequestContext | None
    released_whale_aggregate: bool = False


class _Rejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def fixed(value: Decimal) -> str:
    """Exact fixed-point rendering; never exponent notation, never rounded."""
    return format(value, "f")


def displays(value: Decimal, unit: str) -> tuple[str, ...]:
    with localcontext(EXACT):
        forms = [fixed(value), fixed(value.normalize())]
    if unit == "percent":
        forms += [f + "%" for f in forms]
    return tuple(dict.fromkeys(forms))


def report_sha256(report) -> str:
    return hashlib.sha256(canonical_json(report.model_dump(mode="json")).encode()).hexdigest()


def session_date(T: datetime) -> date:
    return T.astimezone(NEW_YORK).date()


class _Builder:
    def __init__(self, task: TaskId, T: datetime, inputs: EvidenceInputs) -> None:
        self.task, self.T, self.inputs = task, T, inputs
        self.items: list[EvidenceItem] = []
        self.item_literals: dict[str, set[str]] = {}
        self.source_keys: dict[str, frozenset[str]] = {}
        self.anchors: list[Anchor] = []
        self.claims: list[AssessedClaim] = []
        self.claim_literals: dict[str, set[str]] = {}
        self.unavailable: list[UnavailableEntry] = []
        self.excluded: list[ExcludedItem] = []
        self.statuses: dict[Category, tuple[CategoryState, tuple[str, ...]]] = {}
        self.limitations: list[str] = list(INTERPRETATION_LIMITATIONS)
        self.digests: list[ReportDigest] = []
        self.handle_sources: list[HandleSource] = []
        self.engine_versions: dict[Category, str] = {}
        self.bindings_extra: dict = dict(watchlist_version=None, watchlist_digest=None, whale_rules_digest=None,
                                         whale_contributors=(), whale_gate=None)
        self.c12_values: dict[str, tuple[str, BoundValue]] = {}     # field_path -> (owner, value)
        self.mapping: AssetEtfMapping | None = None
        self.whale_released = False
        self.claim_capacity_exceeded = 0

    # ------------------------------------------------------------------ plumbing
    def handle(self) -> str:
        return f"E{len(self.items) + 1:03d}"

    def add_item(self, item: EvidenceItem, literals: set[str], keys: set[str], locator: str) -> None:
        self.items.append(item)
        # Units are never literals: a unit word after a number must stay checkable (G5).
        lits = {item.evidence_id, item.subject,
                *(a.value for a in item.attributes if a.name != "unit" and is_literal_candidate(a.value)),
                *(t.value for t in item.times)} | literals
        if item.state:
            lits.add(item.state)
        self.item_literals[item.evidence_id] = {x for x in lits if is_literal_candidate(x)}
        self.source_keys[item.evidence_id] = frozenset(keys)
        self.handle_sources.append(HandleSource(ref=item.evidence_id, category=item.category, locator=locator))

    def exclude(self, category: Category, locator: str, reason: str) -> None:
        self.excluded.append(ExcludedItem(category=category, locator=locator, reason=reason))

    def missing(self, category: Category, subject: str, reasons) -> None:
        self.unavailable.append(UnavailableEntry(category=category, subject=subject, reasons=tuple(reasons)))

    def status(self, category: Category, state: CategoryState, reasons=()) -> None:
        self.statuses[category] = (state, tuple(reasons))

    def digest(self, category: Category, report) -> None:
        self.digests.append(ReportDigest(category=category, engine_version=report.engine_version,
                                         sha256=report_sha256(report)))

    def check_report(self, report, cls, version: str, category: Category):
        """R1 and R2; returns the revalidated copy (the caller's object is never touched)."""
        if type(report) is not cls:
            raise _Rejected("REVALIDATION_FAILED")
        try:
            dumped = report.model_dump()
            copy = cls.model_validate(dumped)
        except Exception:
            raise _Rejected("REVALIDATION_FAILED") from None
        if copy.model_dump() != dumped:       # an object that bypassed its own validation (or normalization)
            raise _Rejected("REVALIDATION_FAILED")
        if copy.engine_version != version:
            raise _Rejected("ENGINE_VERSION_NOT_ACCEPTED")
        if copy.evaluation_time != self.T:
            raise _Rejected("EVALUATION_TIME_MISMATCH")
        self.engine_versions[category] = version
        return copy

    def time(self, kind: TimeKind, name: str, value) -> TimedValue | None:
        """F3. Returns None when the value is after T and must not be used."""
        if isinstance(value, datetime):
            value = aware_utc(value)
            if kind in (TimeKind.AVAILABILITY, TimeKind.OBSERVATION_OR_PUBLICATION) and value > self.T:
                return None
            return TimedValue(kind=kind, name=name, value=render_time(value))
        if isinstance(value, date):
            return TimedValue(kind=kind, name=name, value=value.isoformat())
        return TimedValue(kind=kind, name=name, value=str(value))

    def available(self, *times) -> bool:
        """Every given receipt/publication/availability instant is known and at or before T."""
        for when in times:
            if when is None or not isinstance(when, datetime) or aware_utc(when) > self.T:
                return False
        return True

    def provenance_ok(self, prov) -> bool:
        """A provenance record was received (and, if stated, sourced) at or before T."""
        if prov is None:
            return False
        return self.available(prov.received_timestamp) and (
            prov.source_timestamp is None or self.available(prov.source_timestamp))

    def bound(self, owner: str, n: int, path: str, value: Decimal, unit: str, qualifier=None, group=None) -> BoundValue:
        return BoundValue(value_id=f"{owner}.V{n}", field_path=path, value=fixed(value), unit=unit,
                          displays=displays(value, unit), qualifier=qualifier, group=group)

    # ---------------------------------------------------------------------- C10
    def c10(self) -> None:
        report = self.inputs.market_state
        if report is None:
            self.status(Category.C10, CategoryState.NOT_SUPPLIED)
            return
        try:
            r = self.check_report(report, MarketStateReport, C10_VERSION, Category.C10)
            if r.symbol not in ACCEPTED_C10_SYMBOLS:
                raise _Rejected("ASSET_MISMATCH")
        except _Rejected as e:
            self.exclude(Category.C10, "C10", e.reason)
            self.status(Category.C10, CategoryState.REPORT_REJECTED, (e.reason,))
            return
        self.digest(Category.C10, r)
        self.limitations += list(r.limitations)
        partial = False
        late_dims = set()
        for dim in C10_DIMENSIONS:
            d = getattr(r, dim)
            if any(s.newest_provenance is not None and not self.provenance_ok(s.newest_provenance) for s in d.sources):
                late_dims.add(dim)
                partial = True
                self.exclude(Category.C10, f"C10.{dim}", "SOURCE_RECEIVED_AFTER_EVALUATION")
                self.missing(Category.C10, f"C10.{dim}", ("SOURCE_RECEIVED_AFTER_EVALUATION",))
                continue
            if d.state == "UNKNOWN":
                partial = True
                self.exclude(Category.C10, f"C10.{dim}", "C10_DIMENSION_UNKNOWN")
                self.missing(Category.C10, f"C10.{dim}", ("C10_DIMENSION_UNKNOWN", *d.reasons))
                continue
            self._c10_dimension(dim, d)
        partial = True   # crowding is always UNKNOWN: OI and basis are unavailable in C09
        self.exclude(Category.C10, "C10.crowding", "C10_CROWDING_UNAVAILABLE")
        self.missing(Category.C10, "C10.crowding", ("C10_CROWDING_UNAVAILABLE", *r.crowding.reasons))
        if late_dims & {"direction", "volatility"}:
            self.exclude(Category.C10, "C10.regime", "SOURCE_RECEIVED_AFTER_EVALUATION")
            self.missing(Category.C10, "C10.regime", ("SOURCE_RECEIVED_AFTER_EVALUATION",))
        elif r.regime.state == "UNKNOWN":
            self.exclude(Category.C10, "C10.regime", "C10_REGIME_UNKNOWN")
            self.missing(Category.C10, "C10.regime", ("C10_REGIME_UNKNOWN", *r.regime.reasons))
        else:
            eid = self.handle()
            keys = set()
            for item in self.items:
                if item.category is Category.C10 and item.subject in ("direction", "volatility"):
                    keys |= self.source_keys[item.evidence_id]
            keys = keys or {"C09.candles"}
            item = EvidenceItem(
                evidence_id=eid, category=Category.C10, tier=Tier.STRUCTURED, kind="C10_REGIME", subject="regime",
                state=r.regime.state.value,
                attributes=(Attribute(name="direction", value=r.regime.direction.value),
                            Attribute(name="volatility", value=r.regime.volatility.value)),
                reasons=r.regime.reasons)
            self.add_item(item, set(), keys | {"C10.regime"}, "C10.regime")
            self.anchors.append(Anchor(anchor_id=f"A{len(self.anchors) + 1:02d}", evidence_id=eid,
                                       statement=f"C10 composite regime is {r.regime.state.value} at the evaluation time."))
        liq = r.liquidation
        if liq.label.value == "AUTHORITATIVE_LIQUIDATION_EVENT" and all(
                self.provenance_ok(e.provenance) and self.available(e.timestamp) for e in liq.authoritative_events):
            eid = self.handle()
            item = EvidenceItem(evidence_id=eid, category=Category.C10, tier=Tier.CONTEXTUAL, kind="C10_LIQUIDATION",
                                subject="liquidation", state=liq.label.value,
                                attributes=(Attribute(name="heuristic_pressure", value=liq.heuristic_pressure),),
                                reasons=liq.reasons)
            self.add_item(item, set(), {"C10.liquidation"}, "C10.liquidation")
        else:
            partial = True
            self.exclude(Category.C10, "C10.liquidation", "C10_LIQUIDATION_UNKNOWN")
            self.missing(Category.C10, "C10.liquidation", liq.reasons)
        has = any(i.category is Category.C10 for i in self.items)
        self.status(Category.C10, (CategoryState.PARTIAL if partial else CategoryState.INCLUDED) if has
                    else CategoryState.ALL_EXCLUDED,
                    sorted({e.reason for e in self.excluded if e.category is Category.C10}))

    def _c10_dimension(self, dim: str, d) -> None:
        eid = self.handle()
        trusted_sources = {s.source for s in d.sources if s.trusted_for_current_use}
        attributes = []
        for i, s in enumerate(d.sources):
            attributes += [Attribute(name=f"sources[{i}].source", value=s.source),
                           Attribute(name=f"sources[{i}].formula_version", value=s.formula_version),
                           Attribute(name=f"sources[{i}].quality_state",
                                     value=s.quality_state.value if s.quality_state else "NONE")]
        # Thresholds are configuration metadata, not observations: their names are sent, never their numbers.
        attributes += [Attribute(name=f"thresholds[{i}].name", value=t.name) for i, t in enumerate(d.thresholds)]
        literals = set()
        if dim == "funding":
            attributes.append(Attribute(name="interval", value=d.interval))
            literals.add(d.interval)
        values, withheld, times = [], [], []
        for fact in d.facts:
            label = f"{fact.source}:{fact.field}"
            why = None
            if not d.inputs_trusted:
                why = "INPUTS_NOT_TRUSTED"
            elif fact.metric.value is None:
                why = f"VALUE_UNAVAILABLE:{fact.metric.reason}"
            elif fact.source not in trusted_sources:
                why = "SOURCE_NOT_TRUSTED_FOR_CURRENT_USE"
            fact_times = []
            for name in ("window_start", "window_end"):
                when = getattr(fact, name)
                if when is not None:
                    tv = self.time(TimeKind.OBSERVATION_OR_PUBLICATION, name, when)
                    if tv is None:
                        why = why or "OBSERVATION_AFTER_EVALUATION"
                    fact_times.append(tv)
            if why is not None:
                withheld.append(f"{label}:{why}")
                continue
            v = self.bound(eid, len(values) + 1, f"C10.{dim}.{label}", fact.metric.value, fact.metric.unit,
                           qualifier=fact.window_kind.value)
            values.append(v)
            times += [TimedValue(kind=t.kind, name=f"{v.value_id}.{t.name}", value=t.value) for t in fact_times]
        item = EvidenceItem(evidence_id=eid, category=Category.C10, tier=Tier.STRUCTURED, kind="C10_DIMENSION",
                            subject=dim, state=d.state.value, attributes=tuple(attributes), values=tuple(values),
                            values_withheld=tuple(withheld), times=tuple(times), reasons=d.reasons)
        self.add_item(item, literals, {s.source for s in d.sources} | {f"C10.{dim}"}, f"C10.{dim}")
        self.anchors.append(Anchor(anchor_id=f"A{len(self.anchors) + 1:02d}", evidence_id=eid,
                                   statement=f"C10 {dim} is {d.state.value} at the evaluation time."))

    # ---------------------------------------------------------------------- C11
    def c11(self) -> None:
        report = self.inputs.whales
        gate = self._whale_gate(report)
        if gate is not None:
            self.exclude(Category.C11, "C11", gate)
            self.bindings_extra["whale_gate"] = gate
            self.status(Category.C11, CategoryState.NOT_RELEASED, (WHALE_NOT_RELEASED,))
            self.missing(Category.C11, "C11", (WHALE_NOT_RELEASED,))
            return
        r = self._whale_report
        eid = self.handle()
        gross = r.aggregate.gross_notional
        item = EvidenceItem(evidence_id=eid, category=Category.C11, tier=Tier.CONTEXTUAL, kind="C11_AGGREGATE",
                            subject="aggregate.gross_notional", state=None,
                            values=(self.bound(eid, 1, "aggregate.gross_notional", gross.value, gross.unit),),
                            limitations=tuple(C11_LIMITATIONS))
        self.add_item(item, set(), {"C11"}, "C11.aggregate.gross_notional")
        self.bindings_extra["whale_gate"] = "RELEASED_GROSS_ONLY"
        self.status(Category.C11, CategoryState.INCLUDED)
        self.whale_released = True

    def _whale_gate(self, report) -> str | None:
        """None when the gross may be released; otherwise the precise reason, kept in the record only."""
        if report is None:
            return "NOT_SUPPLIED"
        try:
            r = self.check_report(report, WhaleReport, C11_VERSION, Category.C11)
        except _Rejected as e:
            return f"REPORT_REJECTED:{e.reason}"
        self.digest(Category.C11, r)
        self.bindings_extra.update(watchlist_version=r.watchlist_version, watchlist_digest=r.watchlist_digest,
                                   whale_rules_digest=r.rules_digest)
        fresh = [w for w in r.wallets if w.exposure.status is SnapshotStatus.FRESH]
        sided = [w for w in fresh if w.exposure.side in (Side.LONG, Side.SHORT)]
        flats = [w for w in fresh if w.exposure.side is Side.FLAT]
        if any(w.exposure.provider_notional.value is None or w.exposure.provider_notional.value < 0 for w in sided):
            return "INCONSISTENT:SIDED_NOTIONAL"
        if any(w.exposure.provider_notional.value != 0 or w.exposure.size.value != 0 for w in flats):
            return "INCONSISTENT:FLAT_NOT_ZERO"
        if len(fresh) != r.aggregate.wallets_available or len(sided) + len(flats) != len(fresh):
            return "INCONSISTENT:FRESH_COUNT"
        if any(w.snapshot is None or not self.provenance_ok(w.snapshot.provenance)
               or not self.available(w.snapshot.snapshot_time) for w in fresh):
            return "INCONSISTENT:SNAPSHOT_AFTER_EVALUATION"
        P = [w for w in sided if w.exposure.provider_notional.value > 0]
        agg = r.aggregate
        if any(m.value is None for m in (agg.gross_notional, agg.long_notional, agg.short_notional)):
            return "INCONSISTENT:AGGREGATE_UNAVAILABLE"
        with localcontext(EXACT):
            long_sum = sum((w.exposure.provider_notional.value for w in sided if w.exposure.side is Side.LONG), Decimal(0))
            short_sum = sum((w.exposure.provider_notional.value for w in sided if w.exposure.side is Side.SHORT), Decimal(0))
            p_sum = sum((w.exposure.provider_notional.value for w in P), Decimal(0))
            if not (agg.gross_notional.value == agg.long_notional.value + agg.short_notional.value == p_sum
                    and agg.long_notional.value == long_sum and agg.short_notional.value == short_sum):
                return "INCONSISTENT:SUMS"
            self.bindings_extra["whale_contributors"] = tuple(sorted(w.address for w in P))
            if len(P) < MIN_WHALE_CONTRIBUTORS:
                return "FEWER_THAN_MIN_CONTRIBUTORS"
            if 2 * max(w.exposure.provider_notional.value for w in P) > p_sum:
                return "DOMINATED_BY_ONE_CONTRIBUTOR"
        self._whale_report = r
        return None

    # -------------------------------------------------------------------- C12 macro
    def c12_macro(self) -> None:
        report = self.inputs.macro
        if report is None:
            self.status(Category.C12_MACRO, CategoryState.NOT_SUPPLIED)
            return
        try:
            r = self.check_report(report, MacroEvidenceReport, C12_MACRO_VERSION, Category.C12_MACRO)
            marked = self._markers(r)
        except _Rejected as e:
            self.exclude(Category.C12_MACRO, "C12_MACRO", e.reason)
            self.status(Category.C12_MACRO, CategoryState.REPORT_REJECTED, (e.reason,))
            return
        self.digest(Category.C12_MACRO, r)
        self.limitations += list(r.limitations)
        for se in sorted(r.series, key=lambda s: s.series_id):
            self._series(se, marked)
        for ev in r.events:
            if ev.state.value != "SUPPORTED":
                self.exclude(Category.C12_MACRO, f"events[{ev.event_type.value}]", "EVENT_SOURCE_UNAVAILABLE")
                self.missing(Category.C12_MACRO, ev.event_type.value, ev.reasons or ("EVENT_SOURCE_UNAVAILABLE",))
        self.missing(Category.C12_MACRO, "consensus", ("CONSENSUS_UNAVAILABLE_NO_APPROVED_SOURCE_NO_SURPRISE_COMPUTED",))
        self._fomc(r)
        has = any(i.category is Category.C12_MACRO for i in self.items)
        reasons = sorted({e.reason for e in self.excluded if e.category is Category.C12_MACRO})
        withheld = any(i.values_withheld for i in self.items if i.category is Category.C12_MACRO)
        self.status(Category.C12_MACRO, (CategoryState.PARTIAL if reasons or withheld else CategoryState.INCLUDED)
                    if has else CategoryState.ALL_EXCLUDED, reasons)

    def _markers(self, r: MacroEvidenceReport) -> set[str]:
        marked = set()
        for m in r.inconsistent_bls_captures:
            left, sep, right = m.partition("@")
            if not sep:
                raise _Rejected("MALFORMED_CAPTURE_MARKER")
            try:
                when = datetime.fromisoformat(right.replace("Z", "+00:00"))
                aware_utc(when)
            except (ValueError, TypeError):
                raise _Rejected("MALFORMED_CAPTURE_MARKER") from None
            if when > self.T:
                raise _Rejected("MALFORMED_CAPTURE_MARKER")
            marked.add(left)
        return marked

    def _series(self, se, marked: set[str]) -> None:
        sid = se.series_id
        times = []
        for kind, name in ((TimeKind.AVAILABILITY, "first_observed_at"), (TimeKind.AVAILABILITY, "captured_at"),
                           (TimeKind.OBSERVATION_OR_PUBLICATION, "publication_time"),
                           (TimeKind.SCHEDULED, "scheduled_at"), (TimeKind.SCHEDULED, "next_scheduled_at")):
            when = getattr(se, name)
            if when is None:
                continue
            tv = self.time(kind, name, when)
            if tv is None:
                reason = "AVAILABILITY_AFTER_EVALUATION" if kind is TimeKind.AVAILABILITY else "OBSERVATION_AFTER_EVALUATION"
                self.exclude(Category.C12_MACRO, f"series[{sid}]", reason)
                return
            times.append(tv)
        if se.provenance is not None and not self.provenance_ok(se.provenance):
            self.exclude(Category.C12_MACRO, f"series[{sid}]", "AVAILABILITY_AFTER_EVALUATION")
            return
        if se.reference_period is not None:
            times.append(TimedValue(kind=TimeKind.PERIOD_LABEL, name="reference_period", value=se.reference_period))
        withheld = []
        if se.conflicting_receipts:
            withheld.append("CONFLICTING_SOURCE_EVIDENCE")
        if sid in marked:
            withheld.append("C12_INCONSISTENT_CAPTURE")
        if se.freshness is not Freshness.CURRENT:
            withheld.append(se.freshness.value)
        if sid not in BLS_SERIES:
            withheld.append("SERIES_NOT_IN_BLS_REGISTRY")
        eid = self.handle()
        values = []
        if not withheld:
            for name, metric, qualifier in (("known_value", se.known_value, "KNOWN_AT_RECEIPT"),
                                            ("previous_known", se.previous_known, "PREVIOUS_PERIOD_IN_SAME_RECEIPT")):
                if metric.value is not None:
                    values.append(self.bound(eid, len(values) + 1, f"series[{sid}].{name}", metric.value, se.unit, qualifier))
            for i, rev in enumerate(se.revisions):
                if rev.value is None:
                    continue
                tv = self.time(TimeKind.AVAILABILITY, "captured_at", rev.captured_at)
                if tv is None:
                    continue
                v = self.bound(eid, len(values) + 1, f"series[{sid}].revisions[{i}]", rev.value, se.unit,
                               "EARLIER_RECEIPT_VALUE")
                values.append(v)
                times.append(TimedValue(kind=tv.kind, name=f"{v.value_id}.captured_at", value=tv.value))
        attributes = [Attribute(name="event_type", value=se.event_type.value), Attribute(name="unit", value=se.unit),
                      Attribute(name="measure", value=se.measure), Attribute(name="seasonal_adjustment", value=se.seasonal_adjustment),
                      Attribute(name="release_vintage", value=se.release_vintage.value),
                      Attribute(name="revision_count", value=str(len(se.revisions)))]
        if se.receipt_window is not None:
            attributes.append(Attribute(name="receipt_window", value=se.receipt_window.value))
        if se.preliminary is not None and not withheld:
            attributes.append(Attribute(name="preliminary", value="true" if se.preliminary else "false"))
        anchored = not withheld and any(v.field_path.endswith(".known_value") for v in values)
        item = EvidenceItem(evidence_id=eid, category=Category.C12_MACRO,
                            tier=Tier.STRUCTURED if anchored else Tier.CONTEXTUAL, kind="C12_SERIES", subject=sid,
                            state=se.freshness.value, attributes=tuple(attributes), values=tuple(values),
                            values_withheld=tuple(withheld), times=tuple(times), reasons=se.reasons)
        self.add_item(item, set(), {f"C12:series:{sid}"}, f"C12_MACRO.series[{sid}]")
        for v in values:
            self.c12_values[v.field_path] = (eid, v)
        if anchored and self.task is TaskId.MACRO_CONTEXT:
            self.anchors.append(Anchor(anchor_id=f"A{len(self.anchors) + 1:02d}", evidence_id=eid,
                                       statement=f"C12 series {sid} is CURRENT for reference period {se.reference_period}."))

    def _statement_ok(self, st) -> bool:
        """A statement is admissible at T only if it was published and received by T (never inferred
        from the report's freshness label)."""
        return st is not None and self.available(st.published_at) and self.provenance_ok(st.provenance)

    def _fomc(self, r: MacroEvidenceReport) -> None:
        """Every FOMC field is gated on the availability at T of the evidence it derives from, never on
        an upstream label: statement facts on that statement's publication and receipt; the schedule
        (next meeting, calendar membership) on the calendar's receipt; freshness on the latest statement
        and the calendar; consistency, the derived change and C12's comparison reasons on both statements
        and the calendar. ``expected_announcement_at`` comes from curated schedules whose receipt the
        report does not carry, so its availability cannot be checked and it is withheld."""
        fomc = r.fomc
        if "CONFLICTING_STATEMENT_COPIES" in fomc.reasons or fomc.statement is None:
            reason = "CONFLICTING_STATEMENT_COPIES" if fomc.statement is None and \
                "CONFLICTING_STATEMENT_COPIES" in fomc.reasons else "NO_FOMC_STATEMENT"
            self.exclude(Category.C12_MACRO, "fomc.statement", reason)
            self.missing(Category.C12_MACRO, "fomc.statement", (reason,))
            return
        latest_ok = self._statement_ok(fomc.statement)
        has_previous = fomc.previous_statement is not None
        previous_ok = self._statement_ok(fomc.previous_statement)
        calendar_known = fomc.calendar_provenance is not None
        calendar_ok = calendar_known and self.provenance_ok(fomc.calendar_provenance)
        calendar_late = calendar_known and not calendar_ok
        if not latest_ok and not previous_ok:
            self.exclude(Category.C12_MACRO, "fomc.statement", "STATEMENT_NOT_AVAILABLE_AT_EVALUATION")
            self.missing(Category.C12_MACRO, "fomc.statement", ("STATEMENT_NOT_AVAILABLE_AT_EVALUATION",))
            return
        freshness_ok = latest_ok and not calendar_late
        comparison_ok = latest_ok and (not has_previous or previous_ok) and not calendar_late
        eid = self.handle()
        current = fomc.freshness is Freshness.CURRENT and freshness_ok
        attributes = [Attribute(name="scope", value="CURRENT_STATEMENT" if current else "HISTORICAL_STATEMENT")]
        withheld, reasons = [], []
        if comparison_ok:
            attributes.append(Attribute(name="consistency", value=fomc.consistency))
            reasons += list(fomc.reasons)
        else:
            withheld.append("consistency:CONTRIBUTING_EVIDENCE_NOT_AVAILABLE_AT_EVALUATION")
        if latest_ok and not calendar_late:
            attributes.append(Attribute(name="in_calendar", value=fomc.in_calendar))
        else:
            withheld.append("in_calendar:CONTRIBUTING_EVIDENCE_NOT_AVAILABLE_AT_EVALUATION")
        if not latest_ok:
            reasons.append("LATEST_STATEMENT_NOT_AVAILABLE_AT_EVALUATION")
        if calendar_late:
            reasons.append("CALENDAR_NOT_AVAILABLE_AT_EVALUATION")
        values, times = [], []
        for label, st, ok, group in (("statement", fomc.statement, latest_ok, f"{eid}.G1"),
                                     ("previous_statement", fomc.previous_statement, previous_ok, f"{eid}.G2")):
            if st is None:
                continue
            if not ok:
                withheld.append(f"{label}:NOT_AVAILABLE_AT_EVALUATION")
                continue
            times += [self.time(TimeKind.OBSERVATION_OR_PUBLICATION, f"{label}.published_at", st.published_at),
                      self.time(TimeKind.AVAILABILITY, f"{label}.received_at", st.provenance.received_timestamp),
                      TimedValue(kind=TimeKind.DATE, name=f"{label}.statement_date", value=st.statement_date.isoformat())]
            attributes.append(Attribute(name=f"{label}.action", value=st.action.value))
            stated = f"AS_STATED_IN_STATEMENT_DATED_{st.statement_date.isoformat()}"
            for name in ("target_lower_percent", "target_upper_percent"):
                values.append(self.bound(eid, len(values) + 1, f"fomc.{label}.{name}", getattr(st, name), "percent",
                                         stated, group))
            if st.stated_change_percentage_points is not None:
                # withheld when the statements contradict, or when that cannot be established at T
                if comparison_ok and fomc.consistency == "CONTRADICTORY":
                    withheld.append(f"{label}.stated_change_percentage_points:CONTRADICTORY")
                elif not comparison_ok:
                    withheld.append(f"{label}.stated_change_percentage_points:CONSISTENCY_NOT_ESTABLISHED_AT_EVALUATION")
                else:
                    values.append(self.bound(eid, len(values) + 1, f"fomc.{label}.stated_change_percentage_points",
                                             st.stated_change_percentage_points, "percentage points", stated))
        change = fomc.range_change_since_previous
        if not (comparison_ok and has_previous):
            withheld.append("range_change_since_previous:CONTRIBUTING_STATEMENT_NOT_AVAILABLE_AT_EVALUATION")
        elif fomc.consistency == "CONSISTENT" and change.value is not None:
            values.append(self.bound(eid, len(values) + 1, "fomc.range_change_since_previous", change.value, change.unit,
                                     "DERIVED_BY_C12_FROM_CONSECUTIVE_STATEMENTS"))
        else:
            withheld.append(f"range_change_since_previous:{fomc.consistency}")
        conflicts = sorted(x for x in fomc.reasons if x.startswith(SCHEDULE_CONFLICT_PREFIXES))
        if conflicts:
            withheld.append("SCHEDULE:CONFLICTING_SCHEDULE_EVIDENCE")
        elif calendar_late:
            withheld.append("SCHEDULE:CALENDAR_NOT_AVAILABLE_AT_EVALUATION")
        elif fomc.next_meeting is not None and calendar_ok:
            times += [self.time(TimeKind.SCHEDULED, "next_meeting.start_date", fomc.next_meeting.start_date),
                      self.time(TimeKind.SCHEDULED, "next_meeting.end_date", fomc.next_meeting.end_date)]
        if fomc.expected_announcement_at is not None:
            withheld.append("expected_announcement_at:SCHEDULE_RECEIPT_NOT_IN_REPORT")
        if freshness_ok:
            state = fomc.freshness.value
        elif not latest_ok:
            state = "LATEST_STATEMENT_NOT_AVAILABLE_AT_EVALUATION"
        else:
            state = "CALENDAR_NOT_AVAILABLE_AT_EVALUATION"
        item = EvidenceItem(evidence_id=eid, category=Category.C12_MACRO,
                            tier=Tier.STRUCTURED if current else Tier.CONTEXTUAL, kind="C12_FOMC", subject="fomc",
                            state=state, attributes=tuple(attributes), values=tuple(values),
                            values_withheld=tuple(withheld), times=tuple(times), reasons=tuple(reasons))
        self.add_item(item, set(), {"C12:fomc"}, "C12_MACRO.fomc")
        for v in values:
            self.c12_values[v.field_path] = (eid, v)
        if current and self.task is TaskId.MACRO_CONTEXT and any(v.field_path.startswith("fomc.statement.") for v in values):
            self.anchors.append(Anchor(anchor_id=f"A{len(self.anchors) + 1:02d}", evidence_id=eid,
                                       statement=f"C12 latest verified FOMC statement is dated "
                                                 f"{fomc.statement.statement_date.isoformat()} and is CURRENT."))

    # --------------------------------------------------------------------- C12 ETF
    def c12_etf(self, use_items: bool) -> None:
        report, mapping = self.inputs.etf, self.inputs.etf_mapping
        if report is None:
            if use_items:
                self.status(Category.C12_ETF, CategoryState.NOT_SUPPLIED)
            return
        try:
            r = self.check_report(report, EtfEvidenceReport, C12_ETF_VERSION, Category.C12_ETF)
            if r.asset != "BTC":
                raise _Rejected("ASSET_MISMATCH")
            self.mapping = self._bind_mapping(r, mapping)
        except _Rejected as e:
            if use_items:
                self.exclude(Category.C12_ETF, "C12_ETF", e.reason)
                self.status(Category.C12_ETF, CategoryState.REPORT_REJECTED, (e.reason,))
            return
        if not use_items:
            return
        self.digest(Category.C12_ETF, r)
        self.limitations += list(EtfEvidenceReport.model_fields["limitations"].default)
        if r.provider_state != "APPROVED":
            self.exclude(Category.C12_ETF, "C12_ETF", "NO_APPROVED_ETF_PROVIDER")
            self.missing(Category.C12_ETF, "C12_ETF", ("NO_APPROVED_ETF_PROVIDER",))
            self.status(Category.C12_ETF, CategoryState.ALL_EXCLUDED, ("NO_APPROVED_ETF_PROVIDER",))
            return
        session = session_date(self.T)
        applicable = {f.ticker: f for f in self.mapping.applicable()}
        for m in r.metrics:
            eligible = {}
            for f in m.funds:
                fund = applicable.get(f.ticker)
                ok = (f.status.value == "OBSERVED" and f.value.value is not None and fund is not None
                      and fund.valid_on(session, self.mapping.identity_retrieved_on) is True)
                obs = f.observation
                # availability comes from the observation's own receipt and times, never from the OBSERVED label
                if ok and (obs is None or not self.provenance_ok(obs.provenance) or obs.trade_date > session
                           or any(t is not None and aware_utc(t) > self.T for t in (obs.as_of, obs.published_at))):
                    ok = False
                if ok:
                    eligible[f.ticker] = f
            if not eligible:
                self.exclude(Category.C12_ETF, f"metrics[{m.metric.value}]", f"COVERAGE_{m.coverage}")
                self.missing(Category.C12_ETF, m.metric.value, m.reasons or (f"COVERAGE_{m.coverage}",))
                continue
            eid = self.handle()
            values, times = [], []
            complete = m.coverage == "COMPLETE" and len(eligible) == len(m.funds) and m.aggregate.value is not None
            if complete:
                values.append(self.bound(eid, 1, f"metrics[{m.metric.value}].aggregate", m.aggregate.value, m.aggregate.unit))
            for ticker in sorted(eligible):
                f = eligible[ticker]
                values.append(self.bound(eid, len(values) + 1, f"metrics[{m.metric.value}].funds[{ticker}]",
                                         f.value.value, f.value.unit, f.basis.value if f.basis else None))
                for name in ("as_of", "published_at"):
                    when = getattr(f.observation, name) if f.observation else None
                    if when is not None:
                        times.append(self.time(TimeKind.OBSERVATION_OR_PUBLICATION, f"{ticker}.{name}", when))
            if m.trade_date is not None:
                times.append(TimedValue(kind=TimeKind.DATE, name="trade_date", value=m.trade_date.isoformat()))
            times.append(self.time(TimeKind.AVAILABILITY, "mapping_available_at", r.mapping_available_at))
            # In T2, ETF evidence is optional context only: never structured, never an anchor.
            structured = complete and self.task is TaskId.BTC_MARKET_STATE
            item = EvidenceItem(evidence_id=eid, category=Category.C12_ETF,
                                tier=Tier.STRUCTURED if structured else Tier.CONTEXTUAL, kind="C12_ETF_METRIC",
                                subject=m.metric.value, state=m.coverage,
                                attributes=tuple(Attribute(name="fund", value=t) for t in sorted(eligible)),
                                values=tuple(values), times=tuple(times), reasons=m.reasons,
                                limitations=tuple(EtfEvidenceReport.model_fields["limitations"].default))
            self.add_item(item, set(eligible), {"C12:etf"}, f"C12_ETF.metrics[{m.metric.value}]")
        has = any(i.category is Category.C12_ETF for i in self.items)
        reasons = sorted({e.reason for e in self.excluded if e.category is Category.C12_ETF})
        self.status(Category.C12_ETF, (CategoryState.PARTIAL if reasons else CategoryState.INCLUDED) if has
                    else CategoryState.ALL_EXCLUDED, reasons)

    def _bind_mapping(self, r: EtfEvidenceReport, mapping) -> AssetEtfMapping:
        if mapping is None:
            raise _Rejected("MAPPING_NOT_SUPPLIED")
        if type(mapping) is not AssetEtfMapping:
            raise _Rejected("MAPPING_BINDING_MISMATCH")
        try:
            m = AssetEtfMapping.model_validate(mapping.model_dump())
        except Exception:
            raise _Rejected("MAPPING_BINDING_MISMATCH") from None
        if not (r.mapping_state == "AVAILABLE" and c12_digest(m) == r.mapping_digest
                and m.mapping_version == r.mapping_version and r.mapping_available_at is not None
                and m.available_at == r.mapping_available_at and m.available_at <= self.T
                and m.identity_retrieved_on == r.mapping_as_of and m.asset == r.asset == "BTC"):
            raise _Rejected("MAPPING_BINDING_MISMATCH")
        return m

    def _resolves_to_btc(self, frame) -> bool:
        if self.mapping is None:
            return False
        session = session_date(self.T)
        funds: list[EtfFund] = list(self.mapping.applicable())
        for res in frame.fund_resolutions:
            if not re.fullmatch(r"\d{10}", res.cik or "") or aware_utc(res.available_at) > self.T:
                continue
            for f in funds:
                if f.ticker == res.ticker and int(res.cik) == f.cik \
                        and f.valid_on(session, self.mapping.identity_retrieved_on) is True:
                    return True
        return False

    # ------------------------------------------------------------------------ C13
    def c13(self) -> None:
        report = self.inputs.news
        if report is None:
            self.status(Category.C13, CategoryState.NOT_SUPPLIED)
            return
        try:
            r = self.check_report(report, VerificationReport, C13_VERSION, Category.C13)
            if any(x.evaluation_time != self.T for x in (*r.results, *r.rejections)) \
                    or any(x.engine_version != C13_VERSION for x in r.results):
                raise _Rejected("EVALUATION_TIME_MISMATCH" if any(x.evaluation_time != self.T for x in
                                                                  (*r.results, *r.rejections)) else "ENGINE_VERSION_NOT_ACCEPTED")
        except _Rejected as e:
            self.exclude(Category.C13, "C13", e.reason)
            self.status(Category.C13, CategoryState.REPORT_REJECTED, (e.reason,))
            return
        self.digest(Category.C13, r)
        for rej in sorted(r.rejections, key=lambda x: x.claim_id):
            self.exclude(Category.C13, f"rejections[{rej.claim_id}]", "NOT_NEWS")
        accepted = []
        for res in sorted(r.results, key=lambda x: (x.claim_id, x.curation_id or "")):
            locator = f"results[{res.claim_id}]"
            if SYNTHETIC_MARKER in res.limitations or SYNTHETIC_MARKER in res.reasons:
                self.exclude(Category.C13, locator, "SYNTHETIC_RECORD")
                continue
            applicability = self._applicability(res)
            if applicability is None:
                self.exclude(Category.C13, locator, "APPLICABILITY_UNRESOLVED")
                continue
            if self.task is TaskId.MACRO_CONTEXT and applicability != "MACRO":
                self.exclude(Category.C13, locator, "NOT_MACRO_APPLICABLE")
                continue
            accepted.append((res, applicability))
        if len(accepted) > MAX_ASSESSED_CLAIMS:
            # Every applicable claim needs its own mandatory claim note; never drop one to fit. The call is
            # refused instead (INPUT_LIMIT_EXCEEDED), with this local diagnostic in the record.
            self.claim_capacity_exceeded = len(accepted)
            self.exclude(Category.C13, "results",
                         f"ASSESSED_CLAIM_CAPACITY_EXCEEDED:{len(accepted)}>{MAX_ASSESSED_CLAIMS}")
        for res, applicability in accepted:
            self._claim(res, applicability)
        self.limitations += [x for x in dict.fromkeys(lim for res, _ in accepted for lim in res.limitations)]
        reasons = sorted({e.reason for e in self.excluded if e.category is Category.C13})
        self.status(Category.C13, (CategoryState.PARTIAL if reasons else CategoryState.INCLUDED) if self.claims
                    else CategoryState.ALL_EXCLUDED if reasons else CategoryState.INCLUDED, reasons)

    def _applicability(self, res) -> str | None:
        kinds = set()
        for fr in res.frames:
            if fr.frame_type is FrameType.RESIDUAL:
                continue
            if fr.frame_type in MACRO_FRAMES:
                kinds.add("MACRO")
            elif fr.frame_type in BTC_FRAMES and self._resolves_to_btc(fr):
                kinds.add("BTC")
            else:
                return None
        if not kinds:
            return None
        return "BTC_VIA_FUND_RESOLUTION" if "BTC" in kinds else "MACRO"

    def _claim(self, res, applicability: str) -> None:
        claim_id = f"N{len(self.claims) + 1:03d}"
        literals = {claim_id, res.state.value}
        frames, n = [], 0
        for fr in res.frames:
            facts = []
            for f in fr.facts:
                n += 1
                fact_id = f"{claim_id}.F{n:02d}"
                citations = []
                for c in f.citations:
                    dates = tuple(TimedValue(kind=TimeKind.DATE, name=label, value=d.isoformat()) for label, d in c.dates)
                    citations.append(CitationView(role=c.role.value, document_number=c.document_number,
                                                  c12_field_path=c.c12_field_path, subject=c.subject, action=c.action,
                                                  dates=dates))
                    literals |= {d.value for d in dates}
                    literals |= {x for x in (c.document_number, c.subject, c.action) if x and IDENTIFIER.match(x)}
                linked = self._links(res, f) if res.state.value != "UNVERIFIED" else ()
                facts.append(FactEntry(fact_id=fact_id, field=f.field, role=f.role.value, outcome=f.outcome.value,
                                       claim_asserted=f.asserted, citations=tuple(citations), reasons=f.reasons,
                                       linked_value_ids=linked))
                literals.add(fact_id)
            tickers = tuple(sorted({x.ticker for x in fr.fund_resolutions})) if applicability != "MACRO" else ()
            literals |= set(tickers) | {fr.frame_type.value, fr.state.value}
            literals |= {x.file_number for x in fr.fund_resolutions if applicability != "MACRO" and IDENTIFIER.match(x.file_number)}
            frames.append(FrameView(frame_type=fr.frame_type.value, state=fr.state.value, reasons=fr.reasons,
                                    facts=tuple(facts), fund_tickers=tickers))
        claim = AssessedClaim(claim_id=claim_id, state=res.state.value, applicability=applicability,
                              frames=tuple(frames), reasons=res.reasons, limitations=res.limitations)
        self.claims.append(claim)
        self.claim_literals[claim_id] = {x for x in literals if is_literal_candidate(x)}
        self.handle_sources.append(HandleSource(ref=claim_id, category=Category.C13,
                                                locator=f"results[{res.claim_id}]"))

    def _links(self, res, f) -> tuple[str, ...]:
        """A SUPPORTED fact may link to eligible C12 values in this request: the cited path must name
        the value and C13's own comparison must hold against it. Fact values themselves are never sent."""
        if f.outcome.value != "SUPPORTED":
            return ()
        paths = [c.c12_field_path for c in f.citations if c.c12_field_path and c.role.value == "SUPPORTS"]
        if not paths or any(p not in self.c12_values for p in paths):
            return ()
        try:
            if f.field == "TARGET_RANGE":
                lo, hi = (Decimal(x) for x in f.asserted.split("-"))
                by = {p.rsplit(".", 1)[1]: self.c12_values[p][1] for p in paths}
                if set(by) != {"target_lower_percent", "target_upper_percent"} or \
                        (Decimal(by["target_lower_percent"].value), Decimal(by["target_upper_percent"].value)) != (lo, hi):
                    return ()
                return tuple(self.c12_values[p][1].value_id for p in paths)
            if len(paths) != 1:
                return ()
            asserted = Decimal(f.asserted)
            value = Decimal(self.c12_values[paths[0]][1].value)
        except (InvalidOperation, ValueError, KeyError):
            return ()
        if paths[0] == "fomc.range_change_since_previous":
            ok = value.copy_abs() == asserted
        else:
            ok = value == asserted
        return (self.c12_values[paths[0]][1].value_id,) if ok else ()

    # ------------------------------------------------------------------- assembly
    def categories(self) -> tuple[CategoryStatus, ...]:
        out = []
        for cat in Category:
            if self.task is TaskId.MACRO_CONTEXT and cat in (Category.C10, Category.C11):
                out.append(CategoryStatus(category=cat, state=CategoryState.NOT_USED_BY_TASK, reasons=()))
                continue
            state, reasons = self.statuses.get(cat, (CategoryState.NOT_SUPPLIED, ()))
            out.append(CategoryStatus(category=cat, state=state, reasons=tuple(reasons)))
        return tuple(out)


def _bindings(b: _Builder) -> PrivateBindings:
    return PrivateBindings(report_digests=tuple(b.digests), handle_sources=tuple(b.handle_sources), **b.bindings_extra)


def select(task, evaluation_time, inputs: EvidenceInputs) -> Selection:
    """Build the request, or decide not to call the model. Never mutates the reports."""
    try:
        task = TaskId(task)
    except ValueError:
        return _skip(str(task), None, ("INVALID_TASK",), None)
    try:
        T = aware_utc(evaluation_time, "evaluation_time")
    except ValueError:
        return _skip(task.value, None, ("INVALID_EVALUATION_TIME",), None)
    b = _Builder(task, T, inputs)
    if task is TaskId.BTC_MARKET_STATE:
        b.c10()
        b.c11()
        b.c12_macro()
        b.c12_etf(use_items=True)
        b.c13()
    else:
        b.c12_macro()
        b.c12_etf(use_items=True)       # optional, eligible ETF context only (never an anchor)
        b.c13()
    excluded = tuple(b.excluded)
    if not b.anchors:
        return _skip(task.value, T, ("INSUFFICIENT_EVIDENCE", "NO_ANCHOR"), b, excluded)
    # Output capacity: every mandatory section must be representable within the approved output
    # contract (one claim note per claim, at most MAX_ASSESSED_CLAIMS; one assessment per anchor).
    if b.claim_capacity_exceeded or len(b.anchors) > MAX_ANCHORS:
        return _skip(task.value, T, ("INPUT_LIMIT_EXCEEDED",), b, excluded)
    structured = tuple(i for i in b.items if i.tier is Tier.STRUCTURED)
    contextual = tuple(i for i in b.items if i.tier is Tier.CONTEXTUAL)
    summary_category = Category.C10 if task is TaskId.BTC_MARKET_STATE else Category.C12_MACRO
    request = AIInterpretationRequest(
        task_id=task, evaluation_time=T, asset_scope="BTC" if task is TaskId.BTC_MARKET_STATE else "NONE_MACRO_ONLY",
        anchors=tuple(b.anchors), structured=structured, contextual=contextual, assessed_claims=tuple(b.claims),
        unavailable=tuple(b.unavailable), categories=b.categories(),
        required=RequiredSections(anchor_ids=tuple(a.anchor_id for a in b.anchors),
                                  claim_ids=tuple(c.claim_id for c in b.claims), summary_category=summary_category,
                                  min_uncertainties=1),
        limitations=tuple(dict.fromkeys(b.limitations)), prompt_id=PROMPT_ID, prompt_digest=PROMPT_DIGEST,
        schema_id=SCHEMA_ID, schema_digest=SCHEMA_DIGEST, selection_policy_id=SELECTION_POLICY_ID,
        selection_policy_digest=SELECTION_POLICY_DIGEST)
    text = canonical_json(request.model_dump(mode="json"))
    if ADDRESS.search(text):
        return _skip(task.value, T, ("PRIVACY_GUARD",), b, excluded)
    if len(text.encode()) > MAX_REQUEST_BYTES:
        return _skip(task.value, T, ("INPUT_LIMIT_EXCEEDED",), b, excluded)
    context = _context(task, b)
    return Selection(task_id=task.value, evaluation_time=T, skip=None, request=request, request_json=text,
                     request_sha256=hashlib.sha256(text.encode()).hexdigest(), excluded=excluded,
                     bindings=_bindings(b), context=context, released_whale_aggregate=b.whale_released)


def _skip(task: str, T, reasons, b: _Builder | None, excluded=()) -> Selection:
    bindings = _bindings(b) if b is not None else PrivateBindings(
        report_digests=(), handle_sources=(), watchlist_version=None, watchlist_digest=None, whale_rules_digest=None,
        whale_contributors=(), whale_gate=None)
    return Selection(task_id=task, evaluation_time=T, skip=tuple(reasons), request=None, request_json=None,
                     request_sha256=None, excluded=tuple(excluded), bindings=bindings, context=None)


def _context(task: TaskId, b: _Builder) -> RequestContext:
    items = {i.evidence_id: i for i in b.items}
    claims = {c.claim_id: c for c in b.claims}
    facts = {f.fact_id: (c.claim_id, f) for c in b.claims for fr in c.frames for f in fr.facts}
    values = {v.value_id: Bound(value_id=v.value_id, displays=v.displays, unit=v.unit, group=v.group,
                                owner=i.evidence_id) for i in b.items for v in i.values}
    literals = {eid: frozenset(lits) for eid, lits in b.item_literals.items()}
    literals.update({cid: frozenset(lits) for cid, lits in b.claim_literals.items()})
    handles = set(items) | set(claims) | set(facts) | {a.anchor_id for a in b.anchors} | \
        {f"CAT:{c.value}" for c in Category}
    keys = dict(b.source_keys)
    for fid, (cid, f) in facts.items():
        k = set()
        for c in f.citations:
            if c.c12_field_path:
                owner = b.c12_values.get(c.c12_field_path)
                k.add(f"C12:{owner[0]}" if owner else f"C12PATH:{c.c12_field_path}")
                if owner:
                    k |= b.source_keys[owner[0]]
            if c.document_number:
                k.add(f"C13:doc:{c.document_number}")
        keys[fid] = frozenset(k)
    states = {s.category: s.state for s in b.categories()}
    return RequestContext(task_id=task, items=items, claims=claims, facts=facts,
                          anchors={a.anchor_id: a for a in b.anchors}, values=values, literals=literals,
                          global_literals=frozenset(handles), categories=states, source_keys=keys,
                          engine_versions=dict(b.engine_versions), unavailable=tuple(b.unavailable))
