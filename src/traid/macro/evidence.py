"""Deterministic point-in-time macro evidence at one explicit evaluation time T.

Only observations TraID received by T are read; later ones are counted and never
otherwise inspected. Release schedules come from the caller with their source.

BLS series. The API returns currently published values with no vintage metadata, so a
capture only shows "what BLS published as of our receipt time". Three facts stay apart:

* Known at receipt: the latest capture received by T (``known_value``) and the prior
  period as it stood in that same capture (``previous_known``).
* Inferred release window: for the latest release due by T (reference period P, scheduled
  at S) the window ends at N, the scheduled release of the immediately following period.
  A capture received in [S, N) is inside the inferred window. That is a fact about the
  receipt and the schedule, not evidence of what BLS published at S: BLS can correct a
  value out of schedule before our capture, and the API cannot show it. If the schedule
  does not list the next period's release, the window is UNBOUNDED.
* Original-release vintage: no approved source establishes it (ALFRED is unavailable), so
  ``release_value`` and ``previous_at_release`` are unavailable, never filled from a
  receipt-time capture.

A capture already holding P before S contradicts the schedule and is excluded. Captures
received at one instant are compared field by field (P's value or stated unavailability,
P's preliminary flag, and P-1's value): a field on which they disagree is withheld, the
receipt is listed as a conflict, and it never enters the revision sequence. Numeric zero,
"-" (unavailable) and an absent period are distinct; equal numbers in different spellings
are one value. Distinct values of P across receipt times are kept as revisions in receipt
order; nothing is overwritten. Consensus has no approved source: it is always unavailable,
never zero, and a "surprise" is never computed.

FOMC. A statement counts from its verified publication time (feed GMT time equal to the
page's EST/EDT release time) and our receipt. The latest known statement is the last
verified decision. A change derived by comparing it with the previous known statement is
evidence, kept apart from what the statement states, and it is withheld when the calendar
lists an entry between the two without a known statement. Freshness of the latest expected
announcement is judged on Board (America/New_York) dates, the dates the statement pages
carry. Expected announcements are the non-notation calendar meetings plus every curated
FOMC schedule known by T, including one whose date matches no calendar meeting (reported as
such, never dropped and never turned into an invented meeting). One without a known
statement is due once its zone-verified release time has passed, or once its date has
passed in New York; on that date without a single verified time (none, or conflicting
ones) it is RELEASE_TIME_UNKNOWN, and no release hour is assumed. A future schedule leaves
the latest statement current.

PCE and GDP are BEA releases; BEA access is not configured, so they are UNSUPPORTED.
Arithmetic runs in an explicit exact Decimal context, never the ambient one. No output
interprets direction, scores surprises or authorizes anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from traid.domain.models import SourceProvenance
from traid.liquidity import Metric
from traid.macro.models import (
    BLS_SERIES, CANONICAL, EVENT_SOURCES, SOURCE_CAPABILITIES, FomcCalendar, FomcMeeting, FomcStatement,
    MacroEventType, MacroModel, PolicyAction, ScheduledRelease, SeriesCapture, SeriesValue, SourceCapability,
    SupportState, capability, digest, next_period, previous_period, rank, utc,
)

ENGINE_VERSION = "c12-macro-evidence-2"
MAX_OBSERVATIONS = 10000
NEW_YORK = ZoneInfo("America/New_York")
POINTS = "percentage points"
NOT_ESTABLISHED = "ORIGINAL_RELEASE_VINTAGE_NOT_ESTABLISHED_NO_VINTAGE_SOURCE"
CONFLICT = "CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME"


class ReceiptWindow(StrEnum):
    INFERRED_RELEASE_WINDOW = "INFERRED_RELEASE_WINDOW"   # received in [release, next period's scheduled release)
    AFTER_INFERRED_WINDOW = "AFTER_INFERRED_WINDOW"       # received at or after the next period's scheduled release
    UNBOUNDED = "UNBOUNDED"                               # the schedule does not bound the window


class ReleaseVintage(StrEnum):
    NOT_ESTABLISHED = "NOT_ESTABLISHED"   # no approved vintage source; receipt-time values are not release values


class Freshness(StrEnum):
    CURRENT = "CURRENT"                       # the latest due release is known
    AWAITING_CAPTURE = "AWAITING_CAPTURE"     # a release is due by T but is not known
    RELEASE_TIME_UNKNOWN = "RELEASE_TIME_UNKNOWN"   # expected on T's date at an unverified time: due or not is unknown
    NO_RELEASE_DUE = "NO_RELEASE_DUE"         # no scheduled release at or before T
    SCHEDULE_UNKNOWN = "SCHEDULE_UNKNOWN"     # no usable schedule (time and zone, or calendar) for this event
    UNSUPPORTED = "UNSUPPORTED"               # the source is not available


class Revision(MacroModel):
    captured_at: datetime
    raw_value: str
    value: Decimal | None


class ReceiptConflict(MacroModel):
    captured_at: datetime
    fields: tuple[Literal["REFERENCE_PERIOD_VALUE", "PRELIMINARY", "PREVIOUS_PERIOD_VALUE"], ...]


class SeriesEvidence(MacroModel):
    series_id: str
    event_type: MacroEventType
    description: str
    unit: str
    measure: Literal["LEVEL", "RATE"]
    seasonal_adjustment: Literal["SA", "NSA"]
    freshness: Freshness
    reference_period: str | None
    scheduled_at: datetime | None
    next_scheduled_at: datetime | None
    publication_time: datetime | None          # BLS API gives none
    first_observed_at: datetime | None
    known_value: Metric                         # P as published at TraID's latest receipt by T
    previous_known: Metric                      # P-1 in that same receipt
    preliminary: bool | None
    captured_at: datetime | None
    receipt_window: ReceiptWindow | None        # of the known receipt
    release_vintage: ReleaseVintage
    release_value: Metric                       # as originally published; needs an established vintage
    previous_at_release: Metric
    consensus: Metric
    revisions: tuple[Revision, ...]             # unambiguous receipts only, in receipt order
    conflicting_receipts: tuple[ReceiptConflict, ...]
    provenance: SourceProvenance | None
    reasons: tuple[str, ...]

    @model_validator(mode="after")
    def no_unestablished_release_values(self):
        if self.release_vintage is ReleaseVintage.NOT_ESTABLISHED and (
                self.release_value.value is not None or self.previous_at_release.value is not None):
            raise ValueError("original-release values require an established release vintage")
        return self


class FomcEvidence(MacroModel):
    freshness: Freshness                        # of the latest expected announcement
    statement: FomcStatement | None             # the last verified decision known at T
    previous_statement: FomcStatement | None
    consistency: Literal["CONSISTENT", "CONTRADICTORY", "INTERVENING_MEETING_NOT_CAPTURED",
                         "NO_PREVIOUS_STATEMENT", "NO_STATEMENT"]
    range_change_since_previous: Metric         # TraID-derived from the two known statements, signed
    in_calendar: Literal["SCHEDULED_MEETING", "NOT_IN_CALENDAR", "CALENDAR_UNAVAILABLE", "NO_STATEMENT"]
    expected_announcement: FomcMeeting | None   # the meeting whose statement is due or possibly due and not known
    expected_announcement_at: datetime | None   # its curated, zone-verified release time, if any
    next_meeting: FomcMeeting | None
    calendar_provenance: SourceProvenance | None
    reasons: tuple[str, ...]


class EventStatus(MacroModel):
    event_type: MacroEventType
    source_capability: SourceCapability
    state: SupportState
    series_ids: tuple[str, ...]
    reasons: tuple[str, ...]


class ExcludedCounts(MacroModel):
    bls_captures: int = Field(ge=0)
    fomc_statements: int = Field(ge=0)
    fomc_calendars: int = Field(ge=0)
    schedules: int = Field(ge=0)


class MacroEvidenceReport(MacroModel):
    engine_version: str = ENGINE_VERSION
    evaluation_time: datetime
    sources: tuple[SourceCapability, ...] = SOURCE_CAPABILITIES
    events: tuple[EventStatus, ...]
    series: tuple[SeriesEvidence, ...]
    fomc: FomcEvidence
    excluded_after_evaluation: ExcludedCounts
    inconsistent_bls_captures: tuple[str, ...]
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    limitations: tuple[str, ...] = (
        "OBSERVED_FACTS_ONLY_NO_MARKET_IMPACT_INTERPRETATION",
        "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION",
        "CONSENSUS_UNAVAILABLE_NO_APPROVED_SOURCE_NO_SURPRISE_COMPUTED",
        "BLS_API_RETURNS_CURRENT_VALUES_WITHOUT_VINTAGES_ORIGINAL_RELEASE_VALUES_NOT_ESTABLISHED",
        "BLS_RELEASE_WINDOW_IS_INFERRED_FROM_RECEIPT_AND_SCHEDULE_NOT_A_VINTAGE",
        "BLS_OUT_OF_SCHEDULE_CORRECTIONS_NOT_DETECTABLE",
        "BLS_PUBLICATION_TIME_NOT_PROVIDED_BY_API",
        "SCHEDULES_CALLER_SUPPLIED_WITH_SOURCE",
        "FOMC_UNSCHEDULED_ACTIONS_ABSENT_FROM_CALENDAR_CANNOT_BE_EXCLUDED",
        "PCE_AND_GDP_UNSUPPORTED_BEA_ACCESS_NOT_CONFIGURED",
    )


# --------------------------------------------------------------------------- helpers
def _na(unit: str, reason: str) -> Metric:
    return Metric(value=None, unit=unit, reason=reason)


def _received(obj, cls) -> datetime:
    """Only the receipt time is read before deciding whether an observation was knowable."""
    p = getattr(obj, "provenance", None)
    received = getattr(p, "received_timestamp", None)
    if type(obj) is not cls or type(p) is not SourceProvenance or not isinstance(received, datetime) \
            or received.tzinfo is None or received.utcoffset() is None:
        raise ValueError(f"canonical {cls.__name__} with a timezone-aware receipt time required")
    return received


def _known(items, cls, T, receipt=None):
    known, later = [], 0
    for item in items:
        if type(item) is not cls:
            raise ValueError(f"{cls.__name__} required")
        when = receipt(item) if receipt else _received(item, cls)
        if when > T:
            later += 1
            continue
        known.append(cls.model_validate(item.model_dump()))
    return known, later


def _event_schedule(schedules, event_type):
    timed = [(s.scheduled_at(), s) for s in schedules if s.event_type is event_type]
    usable = sorted(((at, s) for at, s in timed if at is not None), key=lambda x: (x[0], x[1].reference_period))
    by_period: dict[str, list] = {}
    for at, s in usable:
        by_period.setdefault(s.reference_period, []).append(at)
    conflicting = {p for p, ats in by_period.items() if len(set(ats)) > 1}
    return usable, conflicting


# ------------------------------------------------------------------------------- BLS
def _number(v: SeriesValue | None) -> tuple:
    """A value's identity: absent, stated unavailable, or an exact number in any spelling."""
    if v is None:
        return ("ABSENT",)
    if v.value is None:
        return ("UNAVAILABLE",)
    return ("VALUE", format(v.value.normalize(CANONICAL), "f"))


def _asserted(v: SeriesValue | None) -> tuple:
    return _number(v) + ((v.unavailable_reason,) if v is not None and v.value is None else ())


@dataclass(frozen=True)
class _Receipt:
    """Captures of one series received at one instant, compared field by field."""
    at: datetime
    capture: SeriesCapture          # deterministic representative (canonical rank)
    holds: bool                     # some capture at this instant holds the reference period
    conflicts: tuple[str, ...]      # fields on which the simultaneous captures disagree


def _receipts(captures: list[SeriesCapture], period: str) -> list[_Receipt]:
    by_time: dict[datetime, list[SeriesCapture]] = {}
    for c in captures:
        by_time.setdefault(c.provenance.received_timestamp, []).append(c)
    fields = (("REFERENCE_PERIOD_VALUE", lambda c: _asserted(c.value(period))),
              ("PRELIMINARY", lambda c: None if c.value(period) is None else c.value(period).preliminary),
              ("PREVIOUS_PERIOD_VALUE", lambda c: _asserted(c.value(previous_period(period)))))
    out = []
    for at in sorted(by_time):
        group = by_time[at]
        conflicts = tuple(name for name, identity in fields if len({identity(c) for c in group}) > 1)
        out.append(_Receipt(at=at, capture=min(group, key=rank), conflicts=conflicts,
                            holds=any(c.value(period) is not None for c in group)))
    return out


def _metric(receipt: _Receipt, period: str, name: str, unit: str, absent: str) -> Metric:
    if name in receipt.conflicts:
        return _na(unit, CONFLICT)
    v = receipt.capture.value(period)
    if v is None:
        return _na(unit, absent)
    if v.value is None:
        return _na(unit, f"PUBLISHED_UNAVAILABLE:{v.unavailable_reason}")
    return Metric(value=v.value, unit=unit)


def _series(spec, captures: list[SeriesCapture], schedule, conflicting, T) -> SeriesEvidence:
    unit = spec.unit
    base = dict(series_id=spec.series_id, event_type=spec.event_type, description=spec.description, unit=unit,
                measure=spec.measure, seasonal_adjustment=spec.seasonal_adjustment, publication_time=None,
                release_vintage=ReleaseVintage.NOT_ESTABLISHED, release_value=_na(unit, NOT_ESTABLISHED),
                previous_at_release=_na(unit, NOT_ESTABLISHED), consensus=_na(unit, "NO_APPROVED_CONSENSUS_SOURCE"))
    due = [(at, s) for at, s in schedule if at <= T and s.reference_period not in conflicting]
    upcoming = [(at, s) for at, s in schedule if at > T]
    reasons = ["BLS_API_PROVIDES_NO_PUBLICATION_TIMESTAMP"]
    if conflicting:
        reasons.append("CONFLICTING_SCHEDULE_ENTRIES:" + ",".join(sorted(conflicting)))
    captures = sorted(captures, key=lambda c: (c.provenance.received_timestamp, rank(c)))
    if due:
        scheduled_at, release = due[-1]
        period = release.reference_period
        # The window closes at the next period's release; a gap in the schedule leaves it open.
        following = [at for at, s in schedule if s.reference_period == next_period(period)]
        next_at = following[0] if following else None
        if next_at is None:
            reasons.append("NEXT_PERIOD_RELEASE_NOT_SCHEDULED_WINDOW_UNBOUNDED")
    elif not schedule:
        reasons.append("NO_USABLE_SCHEDULE_FOR_EVENT")
        scheduled_at = next_at = period = None
        if captures:
            published = [v for v in captures[-1].values if v.value is not None]
            period = published[-1].reference_period if published else None
    else:
        reasons.append("NO_RELEASE_DUE_BY_EVALUATION_TIME")
        none = _na(unit, "NO_RELEASE_DUE")
        return SeriesEvidence(freshness=Freshness.NO_RELEASE_DUE, reference_period=None, scheduled_at=None,
                              next_scheduled_at=upcoming[0][0] if upcoming else None, first_observed_at=None,
                              known_value=none, previous_known=none, preliminary=None, captured_at=None,
                              receipt_window=None, revisions=(), conflicting_receipts=(), provenance=None,
                              reasons=tuple(reasons), **base)
    holding = [r for r in _receipts(captures, period) if r.holds] if period is not None else []
    revisions, conflicts, last = [], [], None
    for r in holding:
        if r.conflicts:
            conflicts.append(ReceiptConflict(captured_at=r.at, fields=r.conflicts))
        if "REFERENCE_PERIOD_VALUE" in r.conflicts:
            continue     # simultaneous disagreement is not a step in the revision sequence
        v = r.capture.value(period)
        if last is None or _number(v) != _number(last):
            revisions.append(Revision(captured_at=r.at, raw_value=v.raw_value, value=v.value))
        last = v
    if conflicts:
        reasons.append(CONFLICT)

    def window(at: datetime) -> ReceiptWindow:
        if scheduled_at is None or next_at is None or at < scheduled_at:
            return ReceiptWindow.UNBOUNDED
        return ReceiptWindow.INFERRED_RELEASE_WINDOW if at < next_at else ReceiptWindow.AFTER_INFERRED_WINDOW

    known = holding[-1] if holding else None
    if known is None:
        missing = _na(unit, "PERIOD_NOT_IN_ANY_KNOWN_CAPTURE" if period else "NO_KNOWN_CAPTURE")
        known_value = previous_known = missing
        preliminary = None
    else:
        known_value = _metric(known, period, "REFERENCE_PERIOD_VALUE", unit, "PERIOD_NOT_IN_KNOWN_CAPTURE")
        previous_known = _metric(known, previous_period(period), "PREVIOUS_PERIOD_VALUE", unit,
                                 "PREVIOUS_PERIOD_NOT_IN_KNOWN_CAPTURE")
        preliminary = None if {"REFERENCE_PERIOD_VALUE", "PRELIMINARY"} & set(known.conflicts) \
            else known.capture.value(period).preliminary
    if len(revisions) > 1:
        reasons.append(f"REVISED_ACROSS_CAPTURES:{len(revisions) - 1}")
    if scheduled_at is None:
        freshness = Freshness.SCHEDULE_UNKNOWN
    elif any(r.at >= scheduled_at for r in holding):
        freshness = Freshness.CURRENT
    else:
        freshness = Freshness.AWAITING_CAPTURE
        reasons.append("LATEST_DUE_RELEASE_NOT_CAPTURED")
    return SeriesEvidence(
        freshness=freshness, reference_period=period, scheduled_at=scheduled_at, next_scheduled_at=next_at,
        first_observed_at=holding[0].at if holding else None, known_value=known_value,
        previous_known=previous_known, preliminary=preliminary, captured_at=known.at if known else None,
        receipt_window=window(known.at) if known else None, revisions=tuple(revisions),
        conflicting_receipts=tuple(conflicts), provenance=known.capture.provenance if known else None,
        reasons=tuple(reasons), **base)


def _inconsistent(capture: SeriesCapture, schedule) -> bool:
    """A capture already holding a period whose release was scheduled after the capture."""
    received = capture.provenance.received_timestamp
    return any(at > received and capture.value(s.reference_period) is not None for at, s in schedule)


# ------------------------------------------------------------------------------ FOMC
def _announcement_times(schedules) -> tuple[dict, list]:
    """Curated FOMC release times by their New York date; a date listed with two times has no verified time."""
    by_date: dict = {}
    for s in schedules:
        at = s.scheduled_at() if s.event_type is MacroEventType.FOMC_DECISION else None
        if at is not None:
            by_date.setdefault(at.astimezone(NEW_YORK).date(), set()).add(at)
    return ({d: min(ats) for d, ats in by_date.items() if len(ats) == 1},
            sorted(d for d, ats in by_date.items() if len(ats) > 1))


def _compare(previous: FomcStatement | None, current: FomcStatement, calendar) -> tuple[str, Metric, list]:
    if previous is None:
        return "NO_PREVIOUS_STATEMENT", _na(POINTS, "NO_PREVIOUS_STATEMENT"), []
    reasons = []
    if calendar is None:
        reasons.append("PREVIOUS_STATEMENT_ADJACENCY_UNVERIFIED_NO_CALENDAR")
    elif any(previous.statement_date < m.end_date < current.statement_date for m in calendar.meetings):
        # Notation votes count here: an action between the two statements may be unknown to TraID.
        why = "INTERVENING_MEETING_NOT_CAPTURED"
        return why, _na(POINTS, why), [why]
    with localcontext(CANONICAL):   # exact for these magnitudes; never the ambient context
        lower = current.target_lower_percent - previous.target_lower_percent
        upper = current.target_upper_percent - previous.target_upper_percent
    sign = 0 if lower == 0 else (-1 if lower.is_signed() else 1)
    expected = {PolicyAction.MAINTAIN: 0, PolicyAction.RAISE: 1, PolicyAction.LOWER: -1}[current.action]
    stated = current.stated_change_percentage_points
    if lower != upper:
        problem = "TARGET_RANGE_BOUNDS_MOVED_UNEQUALLY"
    elif sign != expected:
        problem = "DECISION_DIRECTION_CONTRADICTS_PREVIOUS_TARGET_RANGE"
    elif stated is not None and lower.copy_abs() != stated:
        problem = "STATED_CHANGE_CONTRADICTS_PREVIOUS_TARGET_RANGE"
    else:
        return "CONSISTENT", Metric(value=lower, unit=POINTS), reasons
    return "CONTRADICTORY", _na(POINTS, problem), reasons + [problem]


def _fomc(statements: list[FomcStatement], calendars: list[FomcCalendar], schedules, T) -> FomcEvidence:
    today = T.astimezone(NEW_YORK).date()        # Board dates are New York dates
    calendar = max(calendars, key=lambda c: (c.provenance.received_timestamp, rank(c))) if calendars else None
    upcoming = [m for m in calendar.meetings if m.end_date >= today] if calendar else []
    next_meeting = upcoming[0] if upcoming else None
    reasons = []
    by_url: dict[str, list[FomcStatement]] = {}
    for s in statements:
        by_url.setdefault(s.url, []).append(s)
    unique = []
    for url in sorted(by_url):
        group = by_url[url]
        if any(s.model_dump(exclude={"provenance"}) != group[0].model_dump(exclude={"provenance"}) for s in group):
            reasons.append("CONFLICTING_STATEMENT_COPIES")
            continue
        unique.append(min(group, key=lambda s: (s.provenance.received_timestamp, rank(s))))
    if "CONFLICTING_STATEMENT_COPIES" in reasons:
        unique = []
    unique.sort(key=lambda s: (s.published_at, s.url))
    current = unique[-1] if unique else None
    previous = unique[-2] if len(unique) > 1 else None

    times, conflicted = _announcement_times(schedules)
    if conflicted:
        reasons.append("CONFLICTING_FOMC_RELEASE_TIMES:" + ",".join(d.isoformat() for d in conflicted))
    expected = expected_at = None
    if calendar is None:
        reasons.append("NO_FOMC_CALENDAR_KNOWN")
    # Announcement dates come from calendar meetings and from explicit curated schedules; a
    # schedule whose date matches no meeting is still evidence and is never dropped.
    meetings = {m.end_date: m for m in calendar.meetings if not m.notation_vote} if calendar else {}
    candidates = sorted(set(meetings) | set(times) | set(conflicted))
    open_dates = [d for d in candidates if current is None or d > current.statement_date]
    for d in open_dates:
        if d not in meetings:
            reasons.append(f"ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:{d.isoformat()}")
    due, unknown, later = [], [], []
    for d in (d for d in open_dates if d <= today):
        meeting, at = meetings.get(d), times.get(d)
        if at is not None:
            (due if at <= T else later).append((meeting, at))
        elif d < today:
            due.append((meeting, None))
        else:
            unknown.append((meeting, None))
    if due:
        expected, expected_at = due[-1]
        freshness = Freshness.AWAITING_CAPTURE
        reasons.append("STATEMENT_FOR_PAST_MEETING_NOT_CAPTURED" if expected
                       else "STATEMENT_FOR_SCHEDULED_ANNOUNCEMENT_NOT_CAPTURED")
        reasons.append("DUE_BY_VERIFIED_RELEASE_TIME" if expected_at else
                       "DUE_MEETING_DATE_PASSED_IN_NEW_YORK" if expected else "DUE_ANNOUNCEMENT_DATE_PASSED_IN_NEW_YORK")
    elif unknown:
        expected, _ = unknown[-1]
        freshness = Freshness.RELEASE_TIME_UNKNOWN
        reasons.append("MEETING_ENDS_ON_EVALUATION_DATE_RELEASE_TIME_UNVERIFIED" if expected
                       else "ANNOUNCEMENT_ON_EVALUATION_DATE_RELEASE_TIME_UNVERIFIED")
    else:
        freshness = (Freshness.SCHEDULE_UNKNOWN if calendar is None
                     else Freshness.CURRENT if current else Freshness.NO_RELEASE_DUE)
        if later:
            expected, expected_at = later[0]
            reasons.append("ANNOUNCEMENT_SCHEDULED_LATER_ON_MEETING_DATE" if expected
                           else "ANNOUNCEMENT_SCHEDULED_LATER_ON_EVALUATION_DATE")
    if current is None:
        return FomcEvidence(freshness=freshness, statement=None, previous_statement=None, consistency="NO_STATEMENT",
                            range_change_since_previous=_na(POINTS, "NO_STATEMENT"), in_calendar="NO_STATEMENT",
                            expected_announcement=expected, expected_announcement_at=expected_at,
                            next_meeting=next_meeting, calendar_provenance=calendar.provenance if calendar else None,
                            reasons=tuple(reasons + ["NO_FOMC_STATEMENT_KNOWN"]))
    consistency, change, compared = _compare(previous, current, calendar)
    in_calendar = "CALENDAR_UNAVAILABLE" if calendar is None else (
        "SCHEDULED_MEETING" if any(m.end_date == current.statement_date for m in calendar.meetings)
        else "NOT_IN_CALENDAR")
    return FomcEvidence(freshness=freshness, statement=current, previous_statement=previous,
                        consistency=consistency, range_change_since_previous=change, in_calendar=in_calendar,
                        expected_announcement=expected, expected_announcement_at=expected_at,
                        next_meeting=next_meeting, calendar_provenance=calendar.provenance if calendar else None,
                        reasons=tuple(reasons + compared))


# -------------------------------------------------------------------------------- API
def build_macro_evidence(
    *, evaluation_time: datetime, schedules: tuple[ScheduledRelease, ...] = (),
    bls_captures: tuple[SeriesCapture, ...] = (), fomc_statements: tuple[FomcStatement, ...] = (),
    fomc_calendars: tuple[FomcCalendar, ...] = (),
) -> MacroEvidenceReport:
    """Point-in-time macro evidence at T. Pure: no clock, network or ambient context."""
    for items in (schedules, bls_captures, fomc_statements, fomc_calendars):
        if not isinstance(items, tuple) or len(items) > MAX_OBSERVATIONS:
            raise ValueError("bounded tuples of observations required")
    T = utc(evaluation_time, "evaluation_time")
    # A schedule is knowledge too: an entry retrieved after T was not known at T.
    known_schedules, late_schedules = _known(schedules, ScheduledRelease, T, receipt=lambda s: utc(s.retrieved_at))
    captures, late_captures = _known(bls_captures, SeriesCapture, T)
    # A statement is knowable only once both published and received.
    statements, late_statements = _known(
        fomc_statements, FomcStatement, T,
        receipt=lambda s: max(_received(s, FomcStatement), utc(getattr(s, "published_at", None), "published_at")))
    calendars, late_calendars = _known(fomc_calendars, FomcCalendar, T)

    inconsistent, series = [], []
    by_event = {e: _event_schedule(known_schedules, e) for e in MacroEventType}
    for sid, spec in sorted(BLS_SERIES.items()):
        schedule, conflicting = by_event[spec.event_type]
        usable = []
        for c in (c for c in captures if c.series_id == sid):
            if _inconsistent(c, schedule):
                inconsistent.append(f"{sid}@{c.provenance.received_timestamp.isoformat()}")
            else:
                usable.append(c)
        series.append(_series(spec, usable, schedule, conflicting, T))
    events = []
    for event in MacroEventType:
        cap = capability(EVENT_SOURCES[event])
        ids = tuple(sorted(s for s, spec in BLS_SERIES.items() if spec.event_type is event))
        reasons = () if cap.state is SupportState.SUPPORTED else (cap.reason,)
        events.append(EventStatus(event_type=event, source_capability=cap, state=cap.state, series_ids=ids, reasons=reasons))
    inputs = MacroInputs(schedules=tuple(sorted(known_schedules, key=rank)), bls_captures=tuple(sorted(captures, key=rank)),
                         fomc_statements=tuple(sorted(statements, key=rank)), fomc_calendars=tuple(sorted(calendars, key=rank)))
    return MacroEvidenceReport(
        evaluation_time=T, events=tuple(events), series=tuple(series),
        fomc=_fomc(statements, calendars, known_schedules, T),
        excluded_after_evaluation=ExcludedCounts(bls_captures=late_captures, fomc_statements=late_statements,
                                                 fomc_calendars=late_calendars, schedules=late_schedules),
        inconsistent_bls_captures=tuple(sorted(inconsistent)), input_digest=digest(inputs))


class MacroInputs(MacroModel):
    """The knowable inputs at T, in canonical order; their digest identifies the evidence basis."""
    schedules: tuple[ScheduledRelease, ...]
    bls_captures: tuple[SeriesCapture, ...]
    fomc_statements: tuple[FomcStatement, ...]
    fomc_calendars: tuple[FomcCalendar, ...]
