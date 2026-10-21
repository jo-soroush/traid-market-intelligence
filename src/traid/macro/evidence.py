"""Deterministic point-in-time macro evidence at one explicit evaluation time T.

Only observations TraID received by T are read; later ones are counted and never
otherwise inspected. Release schedules come from the caller with their source.

BLS series. The API returns currently published values without vintages, so a
captured value means "what BLS published as of our receipt time". For the latest
release due by T (reference period P, scheduled at S) the window ends at N, the
scheduled release of the immediately following reference period. A capture received
in [S, N) holds the value as published in that release (RELEASE_WINDOW) unless BLS
corrected it out of schedule, which the API cannot show. If the schedule does not list
the next period's release, the window is UNKNOWN and no release value is claimed. A
capture received after T, such as a later backfill of current revised values, is never
read at T. A capture already holding
P before S contradicts the schedule and is excluded. "Previous" is the prior period
as it stood in that same release-window capture. Distinct values of one period across
captures are kept as revisions, in receipt order; nothing is overwritten. Consensus has
no approved source: it is always unavailable, never zero, and a "surprise" is never
computed.

FOMC. A statement counts from its verified publication time (feed GMT time equal to the
page's EST/EDT release time) and our receipt. The current target range is the latest
known statement's; a raise/cut is cross-checked against the previous statement's range.

PCE and GDP are BEA releases; BEA access is not configured, so they are UNSUPPORTED.
No output interprets direction, scores surprises or authorizes anything.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import Field

from traid.domain.models import SourceProvenance
from traid.liquidity import Metric
from traid.macro.models import (
    BLS_SERIES, EVENT_SOURCES, SOURCE_CAPABILITIES, FomcCalendar, FomcMeeting, FomcStatement, MacroEventType,
    MacroModel, ScheduledRelease, SeriesCapture, SourceCapability, SupportState, capability, digest,
    next_period, previous_period, rank, utc,
)

ENGINE_VERSION = "c12-macro-evidence-1"
MAX_OBSERVATIONS = 10000


class Vintage(StrEnum):
    RELEASE_WINDOW = "RELEASE_WINDOW"   # received between the release and the next period's scheduled release
    UNKNOWN_WINDOW = "UNKNOWN_WINDOW"   # the schedule does not bound the release window


class Freshness(StrEnum):
    CURRENT = "CURRENT"                       # the latest due release is captured after its release
    AWAITING_CAPTURE = "AWAITING_CAPTURE"     # a release is due by T but no capture after it holds its period
    NO_RELEASE_DUE = "NO_RELEASE_DUE"         # no scheduled release at or before T
    SCHEDULE_UNKNOWN = "SCHEDULE_UNKNOWN"     # no usable schedule (time and zone) for this event
    UNSUPPORTED = "UNSUPPORTED"               # the source is not available


class Revision(MacroModel):
    captured_at: datetime
    raw_value: str
    value: Decimal | None


class SeriesEvidence(MacroModel):
    series_id: str
    event_type: MacroEventType
    description: str
    unit: str
    seasonal_adjustment: Literal["SA", "NSA"]
    freshness: Freshness
    reference_period: str | None
    scheduled_at: datetime | None
    next_scheduled_at: datetime | None
    publication_time: datetime | None          # BLS API gives none
    first_observed_at: datetime | None
    release_value: Metric                       # as published in the release (release-window capture only)
    previous_at_release: Metric                 # prior period in that same capture
    known_value: Metric                         # latest capture received by T
    known_vintage: Vintage | None
    captured_at: datetime | None
    preliminary: bool | None
    consensus: Metric
    revisions: tuple[Revision, ...]
    provenance: SourceProvenance | None
    reasons: tuple[str, ...]


class FomcEvidence(MacroModel):
    freshness: Freshness
    statement: FomcStatement | None
    previous_statement: FomcStatement | None
    consistency: Literal["CONSISTENT", "CONTRADICTORY", "NO_PREVIOUS_STATEMENT", "NO_STATEMENT"]
    in_calendar: Literal["SCHEDULED_MEETING", "NOT_IN_CALENDAR", "CALENDAR_UNAVAILABLE", "NO_STATEMENT"]
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
        "BLS_API_RETURNS_CURRENT_VALUES_RELEASE_WINDOW_INFERRED_FROM_RECEIPT_AND_SCHEDULE",
        "BLS_OUT_OF_SCHEDULE_CORRECTIONS_NOT_DETECTABLE",
        "BLS_PUBLICATION_TIME_NOT_PROVIDED_BY_API",
        "SCHEDULES_CALLER_SUPPLIED_WITH_SOURCE",
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
def _series(spec, captures: list[SeriesCapture], schedule, conflicting, T) -> SeriesEvidence:
    unit = spec.unit
    base = dict(series_id=spec.series_id, event_type=spec.event_type, description=spec.description, unit=unit,
                seasonal_adjustment=spec.seasonal_adjustment, publication_time=None,
                consensus=_na(unit, "NO_APPROVED_CONSENSUS_SOURCE"))
    due = [(at, s) for at, s in schedule if at <= T and s.reference_period not in conflicting]
    upcoming = [(at, s) for at, s in schedule if at > T]
    reasons = ["BLS_API_PROVIDES_NO_PUBLICATION_TIMESTAMP"]
    if conflicting:
        reasons.append("CONFLICTING_SCHEDULE_ENTRIES:" + ",".join(sorted(conflicting)))
    captures = sorted(captures, key=lambda c: (c.provenance.received_timestamp, rank(c)))
    latest = captures[-1] if captures else None
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
        scheduled_at = next_at = None
        period = None
        if latest:
            published = [v for v in latest.values if v.value is not None]
            period = published[-1].reference_period if published else None
    else:
        reasons.append("NO_RELEASE_DUE_BY_EVALUATION_TIME")
        return SeriesEvidence(freshness=Freshness.NO_RELEASE_DUE, reference_period=None, scheduled_at=None,
                              next_scheduled_at=upcoming[0][0] if upcoming else None, first_observed_at=None,
                              release_value=_na(unit, "NO_RELEASE_DUE"), previous_at_release=_na(unit, "NO_RELEASE_DUE"),
                              known_value=_na(unit, "NO_RELEASE_DUE"), known_vintage=None, captured_at=None,
                              preliminary=None, revisions=(), provenance=None, reasons=tuple(reasons), **base)
    holding = [c for c in captures if period is not None and c.value(period) is not None]
    revisions, last = [], None
    for c in holding:
        v = c.value(period)
        if last is None or v.value != last.value or (v.value is None) != (last.value is None):
            revisions.append(Revision(captured_at=c.provenance.received_timestamp, raw_value=v.raw_value, value=v.value))
        last = v

    def vintage(c: SeriesCapture) -> Vintage:
        received = c.provenance.received_timestamp
        if scheduled_at is None or next_at is None or not scheduled_at <= received < next_at:
            return Vintage.UNKNOWN_WINDOW
        return Vintage.RELEASE_WINDOW

    window = [c for c in holding if vintage(c) is Vintage.RELEASE_WINDOW]
    first = window[0] if window else None
    if first is not None and len({c.value(period).raw_value != "-" and c.value(period).value for c in window
                                  if c.provenance.received_timestamp == first.provenance.received_timestamp}) > 1:
        first = None
        reasons.append("CONFLICTING_RELEASE_WINDOW_CAPTURES")
    if first is not None and first.value(period).value is not None:
        release_value = Metric(value=first.value(period).value, unit=unit)
        prior = first.value(previous_period(period))
        previous = (Metric(value=prior.value, unit=unit) if prior is not None and prior.value is not None
                    else _na(unit, "PREVIOUS_PERIOD_UNAVAILABLE_IN_RELEASE_CAPTURE" if prior is None
                             else f"PUBLISHED_UNAVAILABLE:{prior.unavailable_reason}"))
    else:
        why = ("PUBLISHED_UNAVAILABLE:" + first.value(period).unavailable_reason if first is not None
               else "NO_CAPTURE_IN_RELEASE_WINDOW")
        release_value = _na(unit, why)
        previous = _na(unit, why)
        if first is None:
            reasons.append("RELEASE_VALUE_NOT_PROVEN_AS_PUBLISHED_AT_RELEASE")
    known = holding[-1] if holding else None
    same_receipt = [c for c in holding if known is not None
                    and c.provenance.received_timestamp == known.provenance.received_timestamp]
    if len({c.value(period).raw_value != "-" and c.value(period).value for c in same_receipt}) > 1:
        # Two responses received at one instant disagree: neither is what TraID knew.
        known_value = _na(unit, "CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME")
        reasons.append("CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME")
    elif known is not None:
        kv = known.value(period)
        known_value = Metric(value=kv.value, unit=unit) if kv.value is not None else \
            _na(unit, f"PUBLISHED_UNAVAILABLE:{kv.unavailable_reason}")
    else:
        known_value = _na(unit, "PERIOD_NOT_IN_ANY_KNOWN_CAPTURE" if period else "NO_KNOWN_CAPTURE")
    if len(revisions) > 1:
        reasons.append(f"REVISED_ACROSS_CAPTURES:{len(revisions) - 1}")
    if scheduled_at is None:
        freshness = Freshness.SCHEDULE_UNKNOWN
    elif any(c.provenance.received_timestamp >= scheduled_at for c in holding):
        freshness = Freshness.CURRENT
    else:
        freshness = Freshness.AWAITING_CAPTURE
        reasons.append("LATEST_DUE_RELEASE_NOT_CAPTURED")
    return SeriesEvidence(
        freshness=freshness, reference_period=period, scheduled_at=scheduled_at, next_scheduled_at=next_at,
        first_observed_at=holding[0].provenance.received_timestamp if holding else None,
        release_value=release_value, previous_at_release=previous, known_value=known_value,
        known_vintage=vintage(known) if known else None,
        captured_at=known.provenance.received_timestamp if known else None,
        preliminary=known.value(period).preliminary if known else None, revisions=tuple(revisions),
        provenance=known.provenance if known else None, reasons=tuple(reasons), **base)


def _inconsistent(capture: SeriesCapture, schedule) -> bool:
    """A capture already holding a period whose release was scheduled after the capture."""
    received = capture.provenance.received_timestamp
    return any(at > received and capture.value(s.reference_period) is not None for at, s in schedule)


# ------------------------------------------------------------------------------ FOMC
def _fomc(statements: list[FomcStatement], calendars: list[FomcCalendar], T) -> FomcEvidence:
    calendar = max(calendars, key=lambda c: (c.provenance.received_timestamp, rank(c))) if calendars else None
    upcoming = [m for m in calendar.meetings if m.end_date >= T.date()] if calendar else []
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
    calendar_state = "CALENDAR_UNAVAILABLE" if calendar is None else None
    if calendar is None:
        reasons.append("NO_FOMC_CALENDAR_KNOWN")
    missed = [m for m in (calendar.meetings if calendar else ()) if m.end_date < T.date() and not m.notation_vote
              and not any(s.statement_date == m.end_date for s in unique)]
    if not unique:
        return FomcEvidence(freshness=Freshness.AWAITING_CAPTURE if missed else Freshness.NO_RELEASE_DUE,
                            statement=None, previous_statement=None, consistency="NO_STATEMENT",
                            in_calendar="NO_STATEMENT", next_meeting=next_meeting,
                            calendar_provenance=calendar.provenance if calendar else None,
                            reasons=tuple(reasons + ["NO_FOMC_STATEMENT_KNOWN"]))
    current = unique[-1]
    previous = unique[-2] if len(unique) > 1 else None
    if previous is None:
        consistency = "NO_PREVIOUS_STATEMENT"
    else:
        step = {"MAINTAIN": Decimal(0), "RAISE": current.change_percentage_points or Decimal(0),
                "LOWER": -(current.change_percentage_points or Decimal(0))}[current.action.value]
        expected = (previous.target_lower_percent + step, previous.target_upper_percent + step)
        consistency = "CONSISTENT" if (current.target_lower_percent, current.target_upper_percent) == expected \
            else "CONTRADICTORY"
        if consistency == "CONTRADICTORY":
            reasons.append("DECISION_CHANGE_CONTRADICTS_PREVIOUS_TARGET_RANGE")
    if calendar_state is None:
        scheduled = any(m.end_date == current.statement_date for m in calendar.meetings)
        calendar_state = "SCHEDULED_MEETING" if scheduled else "NOT_IN_CALENDAR"
    latest_missed = [m for m in missed if m.end_date > current.statement_date]
    freshness = Freshness.AWAITING_CAPTURE if latest_missed else Freshness.CURRENT
    if latest_missed:
        reasons.append("STATEMENT_FOR_PAST_MEETING_NOT_CAPTURED")
    return FomcEvidence(freshness=freshness, statement=current, previous_statement=previous,
                        consistency=consistency, in_calendar=calendar_state, next_meeting=next_meeting,
                        calendar_provenance=calendar.provenance if calendar else None, reasons=tuple(reasons))


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
        evaluation_time=T, events=tuple(events), series=tuple(series), fomc=_fomc(statements, calendars, T),
        excluded_after_evaluation=ExcludedCounts(bls_captures=late_captures, fomc_statements=late_statements,
                                                 fomc_calendars=late_calendars, schedules=late_schedules),
        inconsistent_bls_captures=tuple(sorted(inconsistent)), input_digest=digest(inputs))


class MacroInputs(MacroModel):
    """The knowable inputs at T, in canonical order; their digest identifies the evidence basis."""
    schedules: tuple[ScheduledRelease, ...]
    bls_captures: tuple[SeriesCapture, ...]
    fomc_statements: tuple[FomcStatement, ...]
    fomc_calendars: tuple[FomcCalendar, ...]
