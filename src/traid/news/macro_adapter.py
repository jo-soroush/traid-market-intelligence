"""Optional read-only C12 macro adapter (design §8, owner decision O3 option a).

The only input is a C12 ``MacroEvidenceReport`` built at exactly the evaluation time T by an
allowlisted engine version; no raw capture or statement is read. The adapter has no CONTRADICTED
path (M-I3): C12 establishes neither uniqueness nor vintages. Anything C12 withholds stays
withheld with C12's reason (M-I2, M-I5). C13 never computes a macro fact C12 does not publish
(M-I7). This is the only C13 module that imports C12.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from traid.macro.evidence import MacroEvidenceReport, SeriesEvidence
from traid.macro.models import BLS_SERIES, FomcStatement, previous_period
from traid.news.curation import NormEvent, NormFact, series_alternatives
from traid.news.engine import FrameOutcome, MacroContext, MacroEvaluator, Outcome, combine, to_fact, unresolved, \
    unresolved_frame
from traid.news.models import BEA_SERIES_TOKENS, CitationRole, EvidenceCitation, FactOutcome, FactRole, FrameType
from traid.news.text import window

ALLOWED_ENGINE_VERSIONS = ("c12-macro-evidence-2",)
O = FactOutcome
SCHEDULE_CONFLICT_PREFIXES = ("CONFLICTING_FOMC_RELEASE_TIMES:", "ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:",
                              "ANNOUNCEMENT_SCHEDULE_NEW_YORK_DATE_UNDETERMINED:", "FOMC_SCHEDULE_TIMEZONE_UNVERIFIED:")
BEA_EVENTS = {"PCE": "PCE", "GDP": "GDP_ADVANCE"}


def _cite(path: str, subject: str, role: CitationRole = CitationRole.SUPPORTS, dates=()) -> EvidenceCitation:
    return EvidenceCitation(role=role, c12_field_path=path, subject=subject, dates=tuple(dates))


def _supported(path: str, subject: str, dates=()) -> Outcome:
    return Outcome(O.SUPPORTED, (), (_cite(path, subject, dates=dates),))


def _equal(a: Decimal | None, b: str) -> bool:
    return a is not None and a == Decimal(b)


class C12MacroEvaluator(MacroEvaluator):
    def __init__(self, report: MacroEvidenceReport | None) -> None:
        if report is not None and type(report) is not MacroEvidenceReport:
            raise ValueError("a canonical C12 MacroEvidenceReport is required")
        self.report = report
        self.input_digest = report.input_digest if report is not None else ""

    # ------------------------------------------------------------------ dispatch
    def evaluate(self, event: NormEvent, context: MacroContext) -> FrameOutcome:
        r = self.report
        if r is None:
            return unresolved_frame(event, "MACRO_EVIDENCE_NOT_PROVIDED")
        if r.engine_version not in ALLOWED_ENGINE_VERSIONS:
            return unresolved_frame(event, "C12_ENGINE_VERSION_NOT_ALLOWED")
        if r.evaluation_time != context.evaluation_time:
            return unresolved_frame(event, "C12_REPORT_NOT_AT_EVALUATION_TIME")
        ft = event.frame_type
        if ft in (FrameType.MACRO_VALUE, FrameType.MACRO_CHANGE, FrameType.MACRO_CONSENSUS):
            return self._bls(event)
        if ft is FrameType.FOMC_DECISION:
            return self._decision(event, context)
        if ft is FrameType.FOMC_CURRENT_RANGE:
            return self._current_range(event)
        if ft is FrameType.FOMC_SCHEDULE:
            return self._schedule(event)
        return self._latest(event, context)

    # ---------------------------------------------------------------------- BLS
    def _bls(self, event: NormEvent) -> FrameOutcome:
        ident = event.ident
        token = ident["series"]
        if token in BEA_SERIES_TOKENS:
            status = next(e for e in self.report.events if e.event_type.value == BEA_EVENTS[token])
            return unresolved_frame(event, "C12:" + (status.reasons[0] if status.reasons else "NOT_PROVIDED"))
        alternatives = series_alternatives(token)
        facts = []
        for f in event.facts:
            per_series = [self._bls_fact(event.frame_type, f, sid, ident) for sid in alternatives]
            facts.append(to_fact(f, combine(per_series, "SERIES")))
        return FrameOutcome(facts=tuple(facts))

    def _series(self, sid: str) -> SeriesEvidence | None:
        return next((s for s in self.report.series if s.series_id == sid), None)

    def _bls_fact(self, ft: FrameType, f: NormFact, sid: str, ident: dict) -> Outcome:
        se = self._series(sid)
        if se is None or sid not in BLS_SERIES:
            return unresolved("NOT_PROVIDED_BY_C12_EVIDENCE")
        path = f"series[{sid}]"
        if se.conflicting_receipts or any(x.startswith(f"{sid}@") for x in self.report.inconsistent_bls_captures):
            return unresolved("CONFLICTING_SOURCE_EVIDENCE")
        if ft is FrameType.MACRO_CONSENSUS:
            return unresolved(f"C12:{se.consensus.reason}")
        if ft is FrameType.MACRO_CHANGE:
            return unresolved("NOT_PROVIDED_BY_C12_EVIDENCE" if ident["change_kind"] == "YOY_PCT" else "DERIVATION_METHOD_UNVERIFIED")
        P = se.reference_period
        if P is None:
            return unresolved(f"C12:NO_REFERENCE_PERIOD:{se.freshness.value}")
        period = "P" if ident["period"] == P else "P-1" if ident["period"] == previous_period(P) else None
        if period is None:
            return unresolved("NOT_PROVIDED_BY_C12_EVIDENCE")
        scope = ident["scope"]
        if f.field == "UNIT":
            return _supported(f"{path}.unit", sid) if f.value == se.unit.lower() else unresolved("AMBIGUOUS_UNIT")
        if f.field == "PRELIMINARY":
            if period != "P" or se.preliminary is None:
                return unresolved("C12:PRELIMINARY_NOT_ESTABLISHED" if period == "P" else "NOT_PROVIDED_BY_C12_EVIDENCE")
            return _supported(f"{path}.preliminary", sid) if se.preliminary == (f.value == "true") \
                else unresolved("PRELIMINARY_NOT_SUPPORTED_BY_C12_EVIDENCE")
        # VALUE
        if scope == "ORIGINAL":
            return unresolved(f"C12:{se.release_value.reason}")
        if scope == "CURRENT":
            if period == "P-1":
                return unresolved("PRIOR_PERIOD_REVISION_HISTORY_NOT_PROVIDED_BY_C12")
            return Outcome(O.UNRESOLVED, ("STATUS_COVERAGE_INCOMPLETE", "BLS_OUT_OF_SCHEDULE_CORRECTIONS_NOT_DETECTABLE"),
                           (_cite(f"{path}.revisions", sid, CitationRole.ESTABLISHES_EARLIER_STATUS),))
        if period == "P-1":              # R3: P's revisions are never consulted for P-1
            if se.previous_known.value is None:
                return unresolved(f"C12:{se.previous_known.reason}")
            return _supported(f"{path}.previous_known", sid) if _equal(se.previous_known.value, f.value) \
                else unresolved("NO_QUALIFYING_EVIDENCE", "UNCAPTURED_VINTAGE_NOT_EXCLUDABLE")
        if _equal(se.known_value.value, f.value):
            return _supported(f"{path}.known_value", sid)
        for i, rev in enumerate(se.revisions):
            if _equal(rev.value, f.value):
                return _supported(f"{path}.revisions[{i}]", sid)
        if se.known_value.value is None and not se.revisions:
            return unresolved(f"C12:{se.known_value.reason}")
        return unresolved("NO_QUALIFYING_EVIDENCE", "UNCAPTURED_VINTAGE_NOT_EXCLUDABLE")

    # --------------------------------------------------------------------- FOMC
    def _gate(self) -> str | None:
        fomc = self.report.fomc
        if "CONFLICTING_STATEMENT_COPIES" in fomc.reasons:
            return "C12:CONFLICTING_STATEMENT_COPIES"
        if fomc.statement is None:
            return "C12:NO_STATEMENT"
        return None

    def _identify(self, board_date: str) -> tuple[FomcStatement | None, str | None, str | None]:
        """A Board date is only a lookup key: exactly one report statement must carry it (R2 Fix 2)."""
        fomc = self.report.fomc
        candidates = [(s, p) for s, p in ((fomc.statement, "fomc.statement"), (fomc.previous_statement, "fomc.previous_statement"))
                      if s is not None and s.statement_date.isoformat() == board_date]
        if not candidates:
            return None, None, "NOT_PROVIDED_BY_C12_EVIDENCE"
        if len(candidates) > 1:
            return None, None, f"FOMC_STATEMENT_IDENTITY_AMBIGUOUS:{board_date}"
        return candidates[0][0], candidates[0][1], None

    def _decision(self, event: NormEvent, context: MacroContext) -> FrameOutcome:
        D = event.ident["board_date"]
        if window(date.fromisoformat(D))[0] > context.evaluation_time:
            return unresolved_frame(event, "FUTURE_EVENT")
        blocked = self._gate()
        if blocked:
            return unresolved_frame(event, blocked)
        stmt, path, why = self._identify(D)
        if stmt is None:
            return unresolved_frame(event, why)
        fomc = self.report.fomc
        facts = []
        for f in event.facts:
            if f.field == "ACTION":
                o = _supported(f"{path}.action", D) if stmt.action.value == f.value else unresolved("FOMC_STATEMENT_NOT_UNIQUELY_IDENTIFIED_BY_DATE")
            elif f.field == "TARGET_RANGE":
                lo, hi = (Decimal(x) for x in f.value.split("-"))
                o = Outcome(O.SUPPORTED, (), (_cite(f"{path}.target_lower_percent", D), _cite(f"{path}.target_upper_percent", D))) \
                    if (stmt.target_lower_percent, stmt.target_upper_percent) == (lo, hi) \
                    else unresolved("FOMC_STATEMENT_NOT_UNIQUELY_IDENTIFIED_BY_DATE")
            elif f.token == "STATED_IN_DECISION":
                if fomc.consistency == "CONTRADICTORY":
                    o = unresolved("CONFLICTING_SOURCE_EVIDENCE", "C12:CONTRADICTORY")
                elif stmt.stated_change_percentage_points is None:
                    o = unresolved("STATED_CHANGE_NOT_IN_STATEMENT")
                elif stmt.stated_change_percentage_points == Decimal(f.value):
                    o = _supported(f"{path}.stated_change_percentage_points", D)
                else:
                    o = unresolved("CHANGE_SIZE_NOT_SUPPORTED_BY_C12_EVIDENCE")
            else:   # DERIVED_COMPARISON: only C12's own derivation for the latest statement
                change = fomc.range_change_since_previous
                if path != "fomc.statement":
                    o = unresolved("NOT_PROVIDED_BY_C12_EVIDENCE")
                elif fomc.consistency != "CONSISTENT" or change.value is None:
                    o = unresolved(f"C12:{fomc.consistency}")
                elif change.value.copy_abs() == Decimal(f.value):      # copy_abs is exact; abs() rounds to context
                    o = _supported("fomc.range_change_since_previous", D)
                else:
                    o = unresolved("CHANGE_SIZE_NOT_SUPPORTED_BY_C12_EVIDENCE")
            facts.append(to_fact(f, o))
        return FrameOutcome(facts=tuple(facts))

    def _current_range(self, event: NormEvent) -> FrameOutcome:
        """Never concluded (R4): both statements are cited as historical evidence."""
        fomc = self.report.fomc
        cites = tuple(_cite(p, "FOMC", CitationRole.ESTABLISHES_EARLIER_STATUS) for s, p in
                      ((fomc.statement, "fomc.statement"), (fomc.previous_statement, "fomc.previous_statement")) if s is not None)
        return FrameOutcome(facts=tuple(to_fact(f, Outcome(O.UNRESOLVED, ("STATUS_COVERAGE_INCOMPLETE",), cites))
                                        for f in event.facts))

    def _schedule(self, event: NormEvent) -> FrameOutcome:
        """R3: calendar evidence only; no statement identity; a schedule fact, never an occurrence or decision."""
        fomc = self.report.fomc
        S, E = event.ident["meeting_start"], event.ident["meeting_end"]
        meeting = fomc.next_meeting
        if fomc.calendar_provenance is None or "NO_FOMC_CALENDAR_KNOWN" in fomc.reasons:
            return unresolved_frame(event, "SCHEDULE_EVIDENCE_UNAVAILABLE")
        if meeting is None or (meeting.start_date.isoformat(), meeting.end_date.isoformat()) != (S, E):
            return unresolved_frame(event, "NOT_PROVIDED_BY_C12_EVIDENCE")
        if meeting.notation_vote:
            return unresolved_frame(event, "CALENDAR_ENTRY_IS_NOTATION_VOTE")
        conflicts = sorted(r for r in fomc.reasons if r.startswith(SCHEDULE_CONFLICT_PREFIXES))
        if conflicts:
            return unresolved_frame(event, "CONFLICTING_SCHEDULE_EVIDENCE:" + ";".join(conflicts))
        facts = []
        for f in event.facts:
            if f.field == "SCHEDULED_ON":
                o = Outcome(O.SUPPORTED, ("SCHEDULE_ONLY_NOT_OCCURRENCE_OR_DECISION",), (_cite("fomc.next_meeting", f"{S}/{E}"),))
            elif f.field == "ANNOUNCEMENT_TIME":
                expected = fomc.expected_announcement
                ok = expected is not None and expected.end_date.isoformat() == E and fomc.expected_announcement_at is not None \
                    and fomc.expected_announcement_at == datetime.fromisoformat(f.value)
                o = _supported("fomc.expected_announcement_at", f"{S}/{E}") if ok \
                    else unresolved("ANNOUNCEMENT_TIME_NOT_PROVIDED_BY_C12_EVIDENCE")
            else:   # PROJECTIONS
                o = _supported("fomc.next_meeting.projections", f"{S}/{E}") if meeting.projections == (f.value == "true") \
                    else unresolved("PROJECTIONS_NOT_PROVIDED_BY_C12_EVIDENCE")
            facts.append(to_fact(f, o))
        return FrameOutcome(facts=tuple(facts))

    def _latest(self, event: NormEvent, context: MacroContext) -> FrameOutcome:
        """'The most recent FOMC statement is the one dated D' (R4; corrected in R2)."""
        D = event.ident.get("board_date")
        if D is None:
            return unresolved_frame(event, "MEMBER_NOT_IDENTIFIED")
        blocked = self._gate()
        if blocked:
            return unresolved_frame(event, blocked)
        m, path, why = self._identify(D)
        if m is None:
            return unresolved_frame(event, why)
        fomc = self.report.fomc
        later = [(s, p) for s, p in ((fomc.statement, "fomc.statement"), (fomc.previous_statement, "fomc.previous_statement"))
                 if s is not None and s.published_at > m.published_at and s.statement_date.isoformat() > D]
        facts = []
        for f in event.facts:
            if f.role is FactRole.QUALIFIER:
                facts.append(to_fact(f, unresolved("QUALIFIER_NOT_EVALUATED_FOR_FOMC_SEQUENCE")))
            elif later:
                s, p = later[0]
                code = "LATER_MEMBER_AFTER_REFERENCE_TIME" if s.published_at > context.reference_time \
                    else "LATER_MEMBER_BEFORE_REFERENCE_TIME"
                reasons = (f"LATER_SEQUENCE_MEMBER_KNOWN:{s.url}", code) + \
                    (("REFERENCE_TIME_UPPER_BOUND_ONLY",) if context.reference_is_upper_bound else ())
                facts.append(to_fact(f, Outcome(O.SUPERSEDED, reasons, (_cite(p, D, CitationRole.SUPERSEDES),
                                                                       _cite(path, D, CitationRole.ESTABLISHES_EARLIER_STATUS)))))
            else:
                facts.append(to_fact(f, unresolved("LATEST_NOT_PROVABLE")))
        return FrameOutcome(facts=tuple(facts))


__all__ = ["ALLOWED_ENGINE_VERSIONS", "C12MacroEvaluator"]
