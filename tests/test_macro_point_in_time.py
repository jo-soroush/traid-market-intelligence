"""Point-in-time regressions: release vintage, simultaneous conflicts, FOMC currentness and
derived changes, Decimal-context independence, ETF mapping lookahead and economic units."""
import copy
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext
import itertools
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from test_macro_evidence import (
    APPROVED, BLS_REAL, CAL, F, NY, PROVIDERS, REAL, S, assert_no_release_claim, build, captures, obs, sched, series,
    statement, with_value, without,
)
from traid.domain.models import SourceProvenance
from traid.macro import (
    BLS_SERIES, US_SPOT_BTC_ETFS, Applicability, AssetEtfMapping, EtfFund, EtfMetric, Freshness, PolicyAction,
    ReceiptWindow, ScheduledRelease, build_etf_evidence,
)
from traid.macro.evidence import SeriesEvidence
from traid.macro.fed import FeedItem, STATEMENT_TITLE, parse_fomc_statement

D = Decimal
UTC = timezone.utc
AT = S + timedelta(minutes=5)


def edit(period, payload=BLS_REAL, sid="CUUR0000SA0", **fields):
    changed = copy.deepcopy(payload)
    for s in changed["Results"]["series"]:
        if s["seriesID"] == sid:
            for row in s["data"]:
                if f"{row['year']}-{row['period'][1:]}" == period:
                    row.update(fields)
    return changed


UNAVAILABLE = dict(value="-", footnotes=[{"code": "X", "text": "Data unavailable due to the 2025 lapse in appropriations."}])


# ===================================================== BLS: receipt time is not vintage
def test_first_capture_after_an_out_of_schedule_correction_is_never_the_release_value():
    # BLS published 336.940 at S and corrected it to 337.500 before TraID's first capture.
    corrected = captures(S + timedelta(days=3), payload=with_value("2026-09", "337.500"))
    s = series(build(caps=corrected))
    assert s.known_value.value == D("337.500") and s.captured_at == S + timedelta(days=3)
    assert s.receipt_window is ReceiptWindow.INFERRED_RELEASE_WINDOW     # inside the window, still not a vintage
    assert [(r.captured_at, r.value) for r in s.revisions] == [(S + timedelta(days=3), D("337.500"))]
    assert_no_release_claim(s)


@pytest.mark.parametrize("received", [S, S + timedelta(minutes=1), S + timedelta(days=20)])
def test_no_receipt_time_inside_the_window_establishes_the_release_vintage(received):
    s = series(build(at=received + timedelta(hours=1), caps=captures(received)))
    assert s.receipt_window is ReceiptWindow.INFERRED_RELEASE_WINDOW and s.known_value.value == D("336.940")
    assert_no_release_claim(s)


def test_missing_schedule_keeps_receipt_facts_and_claims_no_window_or_vintage():
    s = series(build(schedules=(), caps=captures(AT)))
    assert s.freshness is Freshness.SCHEDULE_UNKNOWN and s.receipt_window is ReceiptWindow.UNBOUNDED
    assert s.reference_period == "2026-09" and s.known_value.value == D("336.940")
    assert "NO_USABLE_SCHEDULE_FOR_EVENT" in s.reasons
    assert_no_release_claim(s)


def test_historical_backfill_gives_receipt_time_values_only():
    # A capture made today holds current revised values for every past period.
    backfill = captures(datetime(2026, 10, 21, 9, tzinfo=UTC))
    s = series(build(at=datetime(2026, 10, 21, 12, tzinfo=UTC), caps=backfill))
    assert s.known_value.value == D("336.940") and s.previous_known.value == D("334.980")
    assert s.captured_at == datetime(2026, 10, 21, 9, tzinfo=UTC)
    assert_no_release_claim(s)


def test_series_evidence_rejects_an_unestablished_release_value():
    s = series(build(caps=captures(AT)))
    forged = dict(s.model_dump(), release_value={"value": D("336.940"), "unit": s.unit, "reason": None})
    with pytest.raises(ValidationError, match="established release vintage"):
        SeriesEvidence.model_validate(forged)


# ================================================== BLS: simultaneous captures by field
def test_same_actual_with_conflicting_previous_withholds_only_the_previous():
    s = series(build(caps=captures(AT) + captures(AT, payload=with_value("2026-08", "300.000"))))
    assert s.known_value.value == D("336.940") and s.preliminary is False
    assert (s.previous_known.value, s.previous_known.reason) == (None, "CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME")
    assert [(c.captured_at, c.fields) for c in s.conflicting_receipts] == [(AT, ("PREVIOUS_PERIOD_VALUE",))]
    assert [r.value for r in s.revisions] == [D("336.940")]


def test_numeric_zero_and_unavailable_are_different_claims():
    zero = captures(AT, payload=with_value("2026-09", "0"))
    dash = captures(AT, payload=edit("2026-09", **UNAVAILABLE))
    s = series(build(caps=zero + dash))
    assert (s.known_value.value, s.known_value.reason) == (None, "CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME")
    assert s.revisions == () and [c.fields for c in s.conflicting_receipts] == [("REFERENCE_PERIOD_VALUE",)]
    only_zero = series(build(caps=zero + captures(AT, payload=with_value("2026-09", "0.000"))))
    assert only_zero.known_value.value == D(0) and only_zero.known_value.reason is None   # zero is a value
    only_dash = series(build(caps=dash + dash))
    assert only_dash.known_value.value is None and only_dash.known_value.reason.startswith("PUBLISHED_UNAVAILABLE:")


def test_unavailability_reasons_are_asserted_and_zero_to_unavailable_is_a_revision():
    other = edit("2026-09", value="-", footnotes=[{"code": "9", "text": "Data not available."}])
    s = series(build(caps=captures(AT, payload=edit("2026-09", **UNAVAILABLE)) + captures(AT, payload=other)))
    assert s.known_value.reason == "CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME"     # two different stated reasons
    later = S + timedelta(days=1)
    chain = series(build(caps=captures(AT, payload=with_value("2026-09", "0")) +
                         captures(later, payload=edit("2026-09", **UNAVAILABLE))))
    assert [(r.captured_at, r.raw_value, r.value) for r in chain.revisions] == [(AT, "0", D(0)), (later, "-", None)]


def test_equivalent_decimal_spellings_are_one_value_in_every_field():
    spelled = edit("2026-08", payload=with_value("2026-09", "336.9400"), value="334.98")
    s = series(build(caps=captures(AT) + captures(AT, payload=spelled)))
    assert s.conflicting_receipts == () and s.known_value.value == D("336.94") and s.previous_known.value == D("334.98")


def test_conflicts_in_several_periods_and_flags_are_each_withheld():
    both = edit("2026-08", payload=with_value("2026-09", "340.000"), value="300.000")
    s = series(build(caps=captures(AT) + captures(AT, payload=both)))
    assert s.known_value.value is None and s.previous_known.value is None and s.preliminary is None
    assert s.conflicting_receipts[0].fields == ("REFERENCE_PERIOD_VALUE", "PREVIOUS_PERIOD_VALUE")
    flagged = edit("2026-09", footnotes=[{"code": "P", "text": "preliminary"}])
    p = series(build(caps=captures(AT) + captures(AT, payload=flagged)))
    assert p.known_value.value == D("336.940") and p.preliminary is None      # the flag alone is withheld
    assert p.conflicting_receipts[0].fields == ("PRELIMINARY",)
    present = series(build(caps=captures(AT) + captures(AT, payload=without("2026-09"))))
    assert present.known_value.value is None and present.conflicting_receipts[0].fields[0] == "REFERENCE_PERIOD_VALUE"


def test_simultaneous_conflicts_never_become_a_revision_sequence():
    early = captures(AT) + captures(AT, payload=with_value("2026-09", "340.000"))
    later = captures(S + timedelta(days=2), payload=with_value("2026-09", "337.000"))
    s = series(build(caps=early + later))
    assert [(r.captured_at, r.value) for r in s.revisions] == [(S + timedelta(days=2), D("337.000"))]
    assert [c.captured_at for c in s.conflicting_receipts] == [AT]
    assert s.known_value.value == D("337.000") and s.previous_known.value == D("334.980")


def test_conflicting_reports_are_identical_under_input_permutations():
    caps = list(captures(AT) + captures(AT, payload=with_value("2026-09", "0")) +
                captures(AT, payload=edit("2026-09", **UNAVAILABLE)) +
                captures(AT, payload=with_value("2026-08", "300.000")))
    baseline = build(caps=caps).model_dump_json()
    for perm in itertools.islice(itertools.permutations(caps), 0, 5000, 397):
        assert build(caps=perm).model_dump_json() == baseline


# ======================================================== FOMC: target-only and derived
def test_target_only_raise_derives_the_change_from_the_trusted_previous_range():
    june, july = statement("20230614", 18), statement("20230726", 18)
    fomc = build(at=datetime(2023, 8, 1, tzinfo=UTC), schedules=(), statements=[june, july]).fomc
    assert fomc.statement.action is PolicyAction.RAISE and fomc.statement.stated_change_percentage_points is None
    assert (fomc.statement.target_lower_percent, fomc.statement.target_upper_percent) == (D("5.25"), D("5.5"))
    assert fomc.consistency == "CONSISTENT"
    assert (fomc.range_change_since_previous.value, fomc.range_change_since_previous.unit) == (D("0.25"), "percentage points")
    assert "PREVIOUS_STATEMENT_ADJACENCY_UNVERIFIED_NO_CALENDAR" in fomc.reasons


def test_target_only_reduction_without_a_trusted_previous_states_no_change():
    fomc = build(at=datetime(2020, 3, 16, tzinfo=UTC), schedules=(), statements=[statement("20200315", 21)]).fomc
    assert fomc.statement.action is PolicyAction.LOWER and fomc.statement.stated_change_percentage_points is None
    assert fomc.consistency == "NO_PREVIOUS_STATEMENT" and fomc.range_change_since_previous.value is None


def test_a_maintained_range_cannot_carry_a_change_size():
    hold = statement("20230614", 18)
    with pytest.raises(ValidationError, match="no change size"):
        type(hold).model_validate(dict(hold.model_dump(), stated_change_percentage_points=D("0.25")))
    with pytest.raises(ValidationError, match="positive"):
        type(hold).model_validate(dict(statement("20230726", 18).model_dump(), stated_change_percentage_points=D(0)))


def test_unverified_official_wording_still_fails_closed():
    # March 3, 2020: "decided today to lower ... by 1/2 percentage point, to 1 to 1-1/4 percent".
    page = (F / "fed_statement_20200303a.html").read_text()
    it = FeedItem(title=STATEMENT_TITLE, url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm",
                  published_at=datetime(2020, 3, 3, 15, tzinfo=UTC))
    with pytest.raises(Exception, match="missing or ambiguous"):
        parse_fomc_statement(page, item=it, received=it.published_at)


def test_stated_and_derived_changes_are_cross_checked():
    fomc = build(statements=REAL, calendars=(CAL,)).fomc       # Jul 29 hold -> Sep 16 raise by 1/4
    assert fomc.statement.stated_change_percentage_points == D("0.25") and fomc.range_change_since_previous.value == D("0.25")
    hold = build(at=datetime(2026, 2, 1, tzinfo=UTC), statements=REAL, calendars=(CAL,)).fomc
    assert hold.consistency == "CONSISTENT" and hold.range_change_since_previous.value == 0
    cases = {
        "STATED_CHANGE_CONTRADICTS_PREVIOUS_TARGET_RANGE": {"stated_change_percentage_points": D("0.5")},
        "DECISION_DIRECTION_CONTRADICTS_PREVIOUS_TARGET_RANGE": {"action": PolicyAction.LOWER},
        "TARGET_RANGE_BOUNDS_MOVED_UNEQUALLY": {"target_upper_percent": D("4.25")},
    }
    for reason, update in cases.items():
        bad = build(statements=[*REAL[:3], REAL[3].model_copy(update=update)], calendars=(CAL,)).fomc
        assert bad.consistency == "CONTRADICTORY" and bad.range_change_since_previous.value is None
        assert reason in bad.reasons, reason


def test_an_uncaptured_meeting_between_statements_blocks_the_derived_change():
    # Known: Jan 28 and Jul 29, 2026; the calendar lists Mar, Apr and Jun meetings in between.
    fomc = build(at=datetime(2026, 8, 1, tzinfo=UTC), statements=REAL, calendars=(CAL,)).fomc
    assert fomc.statement.statement_date == date(2026, 7, 29) and fomc.previous_statement.statement_date == date(2026, 1, 28)
    assert fomc.consistency == "INTERVENING_MEETING_NOT_CAPTURED" and fomc.range_change_since_previous.value is None


# ======================================================= FOMC: announcement currentness
OCT = date(2026, 10, 28)       # the calendar's Oct 27-28, 2026 meeting


def october(published=datetime(2026, 10, 28, 18, tzinfo=UTC), received=None):
    """Test-only record for the Oct 28, 2026 meeting, which has not happened; not a real statement."""
    url = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"
    return REAL[3].model_copy(update={
        "statement_date": OCT, "url": url, "published_at": published, "action": PolicyAction.MAINTAIN,
        "stated_change_percentage_points": None,
        "provenance": SourceProvenance(source="federal_reserve_board", source_type="test", source_id=url,
                                       source_timestamp=published, received_timestamp=received or published)})


def fomc_time(day=OCT, hh=14, retrieved=datetime(2026, 10, 1, tzinfo=UTC)):
    return ScheduledRelease(event_type="FOMC_DECISION", reference_period=f"{day:%Y-%m}", release_date=day,
                            release_time=time(hh), timezone=NY, timezone_evidence="Curated for this test",
                            source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                            retrieved_at=retrieved)


def fomc(at, schedules=(), statements=REAL):
    return build(at=at, schedules=schedules, statements=statements, calendars=(CAL,)).fomc


@pytest.mark.parametrize("at", [
    datetime(2026, 10, 28, 15, tzinfo=UTC),       # 11:00 EDT on the meeting date
    datetime(2026, 10, 28, 23, tzinfo=UTC),       # 19:00 EDT
    datetime(2026, 10, 29, 2, tzinfo=UTC),        # UTC date is the 29th; New York is still the 28th
])
def test_meeting_day_without_a_verified_release_time_is_uncertain(at):
    f = fomc(at)
    assert f.freshness is Freshness.RELEASE_TIME_UNKNOWN and f.expected_announcement.end_date == OCT
    assert f.expected_announcement_at is None and "MEETING_ENDS_ON_EVALUATION_DATE_RELEASE_TIME_UNVERIFIED" in f.reasons
    assert f.statement.statement_date == date(2026, 9, 16)           # the last verified decision is kept


def test_meeting_date_passed_in_new_york_is_due():
    f = fomc(datetime(2026, 10, 29, 4, 30, tzinfo=UTC))               # 00:30 EDT on the 29th
    assert f.freshness is Freshness.AWAITING_CAPTURE and "DUE_MEETING_DATE_PASSED_IN_NEW_YORK" in f.reasons


def test_verified_release_time_decides_before_and_after():
    release = datetime(2026, 10, 28, 18, tzinfo=UTC)                   # 14:00 EDT
    before = fomc(release - timedelta(microseconds=1), schedules=(fomc_time(),))
    assert before.freshness is Freshness.CURRENT and before.expected_announcement_at == release
    assert "ANNOUNCEMENT_SCHEDULED_LATER_ON_MEETING_DATE" in before.reasons
    due = fomc(release, schedules=(fomc_time(),))
    assert due.freshness is Freshness.AWAITING_CAPTURE and "DUE_BY_VERIFIED_RELEASE_TIME" in due.reasons
    captured = fomc(release + timedelta(minutes=1), schedules=(fomc_time(),), statements=[*REAL, october()])
    assert captured.freshness is Freshness.CURRENT and captured.statement.statement_date == OCT
    assert captured.expected_announcement is None


def test_delayed_or_late_received_statements_are_awaited():
    late = october(published=datetime(2026, 10, 28, 21, tzinfo=UTC))   # published three hours after schedule
    waiting = fomc(datetime(2026, 10, 28, 19, tzinfo=UTC), schedules=(fomc_time(),), statements=[*REAL, late])
    assert waiting.freshness is Freshness.AWAITING_CAPTURE and waiting.statement.statement_date == date(2026, 9, 16)
    slow = october(received=datetime(2026, 10, 28, 20, tzinfo=UTC))
    received = fomc(datetime(2026, 10, 28, 19, tzinfo=UTC), schedules=(fomc_time(),), statements=[*REAL, slow])
    assert received.freshness is Freshness.AWAITING_CAPTURE
    assert fomc(datetime(2026, 10, 28, 20, tzinfo=UTC), schedules=(fomc_time(),),
                statements=[*REAL, slow]).freshness is Freshness.CURRENT


def test_release_times_unknown_at_evaluation_or_contradictory_are_not_used():
    at = datetime(2026, 10, 28, 19, tzinfo=UTC)
    future_schedule = fomc_time(retrieved=datetime(2026, 10, 28, 20, tzinfo=UTC))
    assert fomc(at, schedules=(future_schedule,)).freshness is Freshness.RELEASE_TIME_UNKNOWN
    contradictory = fomc(at, schedules=(fomc_time(), fomc_time(hh=15)))
    assert contradictory.freshness is Freshness.RELEASE_TIME_UNKNOWN
    assert "CONFLICTING_FOMC_RELEASE_TIMES:2026-10-28" in contradictory.reasons


def test_without_a_calendar_announcement_freshness_is_unknown():
    f = build(statements=REAL).fomc
    assert f.freshness is Freshness.SCHEDULE_UNKNOWN and f.statement.statement_date == date(2026, 9, 16)


def test_next_meeting_uses_new_york_dates():
    # 01:00 UTC on Oct 29 is still Oct 28 in New York: the Oct 27-28 meeting is not yet past.
    assert fomc(datetime(2026, 10, 29, 1, tzinfo=UTC)).next_meeting.end_date == OCT


# ============================================ FOMC: explicit schedules absent from the calendar
OCT22 = date(2026, 10, 22)     # hypothetical announcement date, not a calendar meeting and not a real event


def unscheduled(day=OCT22, published=datetime(2026, 10, 22, 18, tzinfo=UTC)):
    """Test-only statement record for a hypothetical announcement; not a real statement."""
    url = f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{day:%Y%m%d}a.htm"
    return october(published=published).model_copy(update={
        "statement_date": day, "url": url,
        "provenance": SourceProvenance(source="federal_reserve_board", source_type="test", source_id=url,
                                       source_timestamp=published, received_timestamp=published)})


def test_codex_unmatched_schedule_example_is_awaited_not_current():
    f = fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(fomc_time(day=OCT22),))
    assert OCT22 not in {m.end_date for m in CAL.meetings}
    assert f.freshness is Freshness.AWAITING_CAPTURE and f.statement.statement_date == date(2026, 9, 16)
    assert f.expected_announcement is None and f.expected_announcement_at == datetime(2026, 10, 22, 18, tzinfo=UTC)
    assert f.reasons == ("ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:2026-10-22",
                         "STATEMENT_FOR_SCHEDULED_ANNOUNCEMENT_NOT_CAPTURED", "DUE_BY_VERIFIED_RELEASE_TIME")


def test_unmatched_future_schedule_keeps_the_latest_statement_current():
    future_day = fomc(datetime(2026, 10, 21, 12, tzinfo=UTC), schedules=(fomc_time(day=OCT22),))
    assert future_day.freshness is Freshness.CURRENT and future_day.expected_announcement_at is None
    assert future_day.reasons == ("ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:2026-10-22",)
    same_day = fomc(datetime(2026, 10, 22, 18, tzinfo=UTC) - timedelta(microseconds=1), schedules=(fomc_time(day=OCT22),))
    assert same_day.freshness is Freshness.CURRENT and same_day.expected_announcement_at == datetime(2026, 10, 22, 18, tzinfo=UTC)
    assert "ANNOUNCEMENT_SCHEDULED_LATER_ON_EVALUATION_DATE" in same_day.reasons


def test_unmatched_schedule_is_due_at_its_release_time_and_satisfied_by_its_statement():
    at = datetime(2026, 10, 22, 18, tzinfo=UTC)
    assert fomc(at, schedules=(fomc_time(day=OCT22),)).freshness is Freshness.AWAITING_CAPTURE
    captured = fomc(at, schedules=(fomc_time(day=OCT22),), statements=[*REAL, unscheduled()])
    assert captured.freshness is Freshness.CURRENT and captured.statement.statement_date == OCT22
    assert captured.in_calendar == "NOT_IN_CALENDAR" and captured.reasons == ()
    # A statement published late is not yet known, so the due announcement is still awaited.
    late = unscheduled(published=datetime(2026, 10, 22, 21, tzinfo=UTC))
    assert fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(fomc_time(day=OCT22),),
                statements=[*REAL, late]).freshness is Freshness.AWAITING_CAPTURE


def test_unmatched_schedule_received_after_evaluation_is_not_used():
    late = fomc_time(day=OCT22, retrieved=datetime(2026, 10, 22, 21, tzinfo=UTC))
    r = build(at=datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(late,), statements=REAL, calendars=(CAL,))
    assert r.fomc.freshness is Freshness.CURRENT and r.fomc.reasons == () and r.excluded_after_evaluation.schedules == 1


def test_conflicting_or_duplicate_unmatched_schedules():
    two = (fomc_time(day=OCT22), fomc_time(day=OCT22, hh=15))
    today = fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=two)
    assert today.freshness is Freshness.RELEASE_TIME_UNKNOWN and today.expected_announcement_at is None
    assert "CONFLICTING_FOMC_RELEASE_TIMES:2026-10-22" in today.reasons
    assert "ANNOUNCEMENT_ON_EVALUATION_DATE_RELEASE_TIME_UNVERIFIED" in today.reasons
    passed = fomc(datetime(2026, 10, 23, 12, tzinfo=UTC), schedules=two)
    assert passed.freshness is Freshness.AWAITING_CAPTURE and "DUE_ANNOUNCEMENT_DATE_PASSED_IN_NEW_YORK" in passed.reasons
    at = datetime(2026, 10, 22, 20, tzinfo=UTC)
    single = fomc(at, schedules=(fomc_time(day=OCT22),)).model_dump_json()
    assert fomc(at, schedules=(fomc_time(day=OCT22),) * 3).model_dump_json() == single      # duplicates are one
    mixed = [fomc_time(day=OCT22), fomc_time(day=OCT22, hh=15), fomc_time(), fomc_time(day=date(2026, 12, 9))]
    baseline = build(at=at, schedules=mixed, statements=REAL, calendars=(CAL,)).model_dump_json()
    for perm in itertools.permutations(mixed):
        assert build(at=at, schedules=perm, statements=REAL, calendars=(CAL,)).model_dump_json() == baseline


def test_unmatched_schedule_uses_its_new_york_date_and_exact_time():
    evening = fomc_time(day=OCT22, hh=21)            # 21:00 EDT on Oct 22 is 01:00 UTC on Oct 23
    release = datetime(2026, 10, 23, 1, tzinfo=UTC)
    before = fomc(release - timedelta(minutes=30), schedules=(evening,))
    assert before.freshness is Freshness.CURRENT and before.expected_announcement_at == release
    assert fomc(release, schedules=(evening,)).freshness is Freshness.AWAITING_CAPTURE


def test_unmatched_schedules_before_the_latest_statement_or_without_calendar():
    old = fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(fomc_time(day=date(2026, 9, 1)),))
    assert old.freshness is Freshness.CURRENT and old.reasons == ()   # superseded by the Sep 16 statement
    nocal = build(at=datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(fomc_time(day=OCT22),), statements=REAL).fomc
    assert nocal.freshness is Freshness.AWAITING_CAPTURE and "NO_FOMC_CALENDAR_KNOWN" in nocal.reasons
    ahead = build(at=datetime(2026, 10, 21, tzinfo=UTC), schedules=(fomc_time(day=OCT22),), statements=REAL).fomc
    assert ahead.freshness is Freshness.SCHEDULE_UNKNOWN


def test_notation_votes_are_not_expected_statements_unless_explicitly_scheduled():
    # Test-only record for the Jul 29-30, 2025 meeting; the calendar lists an Aug 22, 2025 notation vote.
    july = unscheduled(day=date(2025, 7, 30), published=datetime(2025, 7, 30, 18, tzinfo=UTC))
    at = datetime(2025, 8, 25, tzinfo=UTC)
    assert fomc(at, statements=[july]).freshness is Freshness.CURRENT
    vote = fomc_time(day=date(2025, 8, 22), retrieved=datetime(2025, 8, 1, tzinfo=UTC))
    explicit = fomc(at, schedules=(vote,), statements=[july])
    assert explicit.freshness is Freshness.AWAITING_CAPTURE
    assert "ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:2025-08-22" in explicit.reasons


# ================================================= FOMC: schedules without a release hour
def fomc_date(day=OCT22, tz=NY, hh=None, retrieved=datetime(2026, 10, 1, tzinfo=UTC)):
    """A curated FOMC schedule carrying a date (and zone) but no verified release hour."""
    return ScheduledRelease(event_type="FOMC_DECISION", reference_period=f"{day:%Y-%m}", release_date=day,
                            release_time=None if hh is None else time(hh), timezone=tz,
                            timezone_evidence=None if tz is None else "Curated for this test",
                            source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                            retrieved_at=retrieved)


def test_codex_date_only_schedule_on_its_new_york_date_is_uncertain():
    f = fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(fomc_date(),))
    assert f.freshness is Freshness.RELEASE_TIME_UNKNOWN and f.statement.statement_date == date(2026, 9, 16)
    assert f.expected_announcement is None and f.expected_announcement_at is None
    assert f.reasons == ("ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:2026-10-22",
                         "ANNOUNCEMENT_ON_EVALUATION_DATE_RELEASE_TIME_UNVERIFIED")


def test_codex_date_only_schedule_on_the_following_new_york_date_is_awaited():
    f = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=(fomc_date(),))
    assert f.freshness is Freshness.AWAITING_CAPTURE and f.statement.statement_date == date(2026, 9, 16)
    assert f.expected_announcement_at is None
    assert f.reasons == ("ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:2026-10-22",
                         "STATEMENT_FOR_SCHEDULED_ANNOUNCEMENT_NOT_CAPTURED", "DUE_ANNOUNCEMENT_DATE_PASSED_IN_NEW_YORK")
    satisfied = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=(fomc_date(),), statements=[*REAL, unscheduled()])
    assert satisfied.freshness is Freshness.CURRENT and satisfied.reasons == ()


def test_future_date_only_schedule_does_not_make_the_statement_stale():
    f = fomc(datetime(2026, 10, 21, 12, tzinfo=UTC), schedules=(fomc_date(),))
    assert f.freshness is Freshness.CURRENT and f.expected_announcement_at is None
    assert f.reasons == ("ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:2026-10-22",)


def test_date_only_schedule_without_a_calendar():
    def nocal(at):
        return build(at=at, schedules=(fomc_date(),), statements=REAL).fomc
    assert nocal(datetime(2026, 10, 21, 12, tzinfo=UTC)).freshness is Freshness.SCHEDULE_UNKNOWN
    same = nocal(datetime(2026, 10, 22, 20, tzinfo=UTC))
    assert same.freshness is Freshness.RELEASE_TIME_UNKNOWN and "NO_FOMC_CALENDAR_KNOWN" in same.reasons
    assert nocal(datetime(2026, 10, 23, 16, tzinfo=UTC)).freshness is Freshness.AWAITING_CAPTURE


def test_date_only_schedule_received_after_evaluation_is_not_used():
    late = fomc_date(retrieved=datetime(2026, 10, 22, 21, tzinfo=UTC))
    r = build(at=datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(late,), statements=REAL, calendars=(CAL,))
    assert r.fomc.freshness is Freshness.CURRENT and r.fomc.reasons == () and r.excluded_after_evaluation.schedules == 1


def test_date_only_and_timed_schedules_for_one_date():
    both = (fomc_date(), fomc_time(day=OCT22))                   # the timed entry refines the date-only one
    before = fomc(datetime(2026, 10, 22, 17, tzinfo=UTC), schedules=both)
    assert before.freshness is Freshness.CURRENT and before.expected_announcement_at == datetime(2026, 10, 22, 18, tzinfo=UTC)
    due = fomc(datetime(2026, 10, 22, 18, tzinfo=UTC), schedules=both)
    assert due.freshness is Freshness.AWAITING_CAPTURE and "DUE_BY_VERIFIED_RELEASE_TIME" in due.reasons
    clash = (fomc_date(), fomc_time(day=OCT22), fomc_time(day=OCT22, hh=15))
    unsure = fomc(datetime(2026, 10, 22, 17, tzinfo=UTC), schedules=clash)
    assert unsure.freshness is Freshness.RELEASE_TIME_UNKNOWN and unsure.expected_announcement_at is None
    assert "CONFLICTING_FOMC_RELEASE_TIMES:2026-10-22" in unsure.reasons


def test_duplicate_and_permuted_date_only_schedules_are_deterministic():
    at = datetime(2026, 10, 22, 20, tzinfo=UTC)
    assert fomc(at, schedules=(fomc_date(),) * 3).model_dump_json() == fomc(at, schedules=(fomc_date(),)).model_dump_json()
    mixed = [fomc_date(), fomc_time(day=OCT22, hh=15), fomc_date(day=date(2026, 10, 28)), fomc_date(tz=None),
             fomc_date(day=date(2026, 10, 23), tz="Europe/London")]
    baseline = build(at=at, schedules=mixed, statements=REAL, calendars=(CAL,)).model_dump_json()
    for perm in itertools.permutations(mixed):
        assert build(at=at, schedules=perm, statements=REAL, calendars=(CAL,)).model_dump_json() == baseline


def test_date_only_schedule_follows_new_york_date_transitions():
    midnight = datetime(2026, 10, 23, 4, tzinfo=UTC)             # 00:00 EDT on Oct 23
    assert fomc(midnight - timedelta(microseconds=1), schedules=(fomc_date(),)).freshness is Freshness.RELEASE_TIME_UNKNOWN
    assert fomc(midnight, schedules=(fomc_date(),)).freshness is Freshness.AWAITING_CAPTURE
    # 03:00 UTC on Oct 22 is still Oct 21 in New York: the Oct 22 schedule is not yet on its date.
    assert fomc(datetime(2026, 10, 22, 3, tzinfo=UTC), schedules=(fomc_date(),)).freshness is Freshness.CURRENT


def test_schedules_without_a_determinable_new_york_date_are_one_window():
    # Oct 22 in London (BST) is 23:00 UTC Oct 21 to 23:00 UTC Oct 22: two New York dates, one announcement.
    london = (fomc_date(tz="Europe/London"),)
    window_end = datetime(2026, 10, 22, 23, tzinfo=UTC)
    assert fomc(datetime(2026, 10, 21, 22, 59, tzinfo=UTC), schedules=london).freshness is Freshness.CURRENT
    for at in (datetime(2026, 10, 21, 23, tzinfo=UTC), window_end - timedelta(microseconds=1)):
        f = fomc(at, schedules=london)
        assert f.freshness is Freshness.RELEASE_TIME_UNKNOWN and f.expected_announcement_at is None
        assert f.reasons == ("ANNOUNCEMENT_SCHEDULE_NEW_YORK_DATE_UNDETERMINED:2026-10-22",
                             "EVALUATION_TIME_WITHIN_SCHEDULED_WINDOW_RELEASE_TIME_UNVERIFIED")
    due = fomc(window_end, schedules=london)
    assert due.freshness is Freshness.AWAITING_CAPTURE and "DUE_SCHEDULED_WINDOW_PASSED" in due.reasons
    # A statement published within the window is not shown to be the scheduled announcement.
    within = fomc(window_end, schedules=london, statements=[*REAL, unscheduled()])
    assert within.freshness is Freshness.AWAITING_CAPTURE and "DUE_SCHEDULED_WINDOW_PASSED" in within.reasons
    later = fomc(window_end, schedules=london, statements=[*REAL, unscheduled(published=window_end)])
    assert later.freshness is Freshness.CURRENT and later.reasons == ()


@pytest.mark.parametrize("hh, earliest, latest", [
    (None, datetime(2026, 10, 21, 10, tzinfo=UTC), datetime(2026, 10, 23, 12, tzinfo=UTC)),   # Oct 22, any zone
    (14, datetime(2026, 10, 22, 0, tzinfo=UTC), datetime(2026, 10, 23, 2, tzinfo=UTC)),       # 14:00, any zone
])
def test_schedules_without_a_verified_zone_cover_every_possible_instant(hh, earliest, latest):
    unzoned = (fomc_date(tz=None, hh=hh),)
    assert fomc(earliest - timedelta(microseconds=1), schedules=unzoned).freshness is Freshness.CURRENT
    inside = fomc(latest - timedelta(microseconds=1), schedules=unzoned)
    assert inside.freshness is Freshness.RELEASE_TIME_UNKNOWN and inside.expected_announcement_at is None
    assert "FOMC_SCHEDULE_TIMEZONE_UNVERIFIED:2026-10-22" in inside.reasons
    assert fomc(latest, schedules=unzoned).freshness is Freshness.AWAITING_CAPTURE


def test_the_latest_due_announcement_is_chosen_by_time_not_input_kind():
    # A London window ending Oct 20 and a New York date-only Oct 22 schedule are both due on Oct 24.
    mixed = (fomc_date(day=date(2026, 10, 20), tz="Europe/London"), fomc_date())
    f = fomc(datetime(2026, 10, 24, 12, tzinfo=UTC), schedules=mixed)
    assert f.freshness is Freshness.AWAITING_CAPTURE and f.reasons[-1] == "DUE_ANNOUNCEMENT_DATE_PASSED_IN_NEW_YORK"


def test_date_only_schedule_for_a_calendar_meeting_keeps_meeting_semantics():
    f = fomc(datetime(2026, 10, 28, 15, tzinfo=UTC), schedules=(fomc_date(day=OCT),))
    assert f.freshness is Freshness.RELEASE_TIME_UNKNOWN and f.expected_announcement.end_date == OCT
    assert f.reasons == ("MEETING_ENDS_ON_EVALUATION_DATE_RELEASE_TIME_UNVERIFIED",)


# ======================================== FOMC: matching scheduled announcements to statements
OCT21 = date(2026, 10, 21)
UNZONED_START, UNZONED_END = datetime(2026, 10, 21, 10, tzinfo=UTC), datetime(2026, 10, 23, 12, tzinfo=UTC)
UNZONED = (fomc_date(tz=None),)                 # Oct 22, no hour, no verified zone: UNZONED_START..UNZONED_END


def test_codex_statement_inside_an_uncertain_window_does_not_settle_it():
    earlier = unscheduled(day=OCT21, published=datetime(2026, 10, 21, 18, tzinfo=UTC))   # inside the window
    statements = [*REAL, earlier]
    same = fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=UNZONED, statements=statements)
    assert same.freshness is Freshness.RELEASE_TIME_UNKNOWN and same.expected_announcement_at is None
    assert same.reasons == ("FOMC_SCHEDULE_TIMEZONE_UNVERIFIED:2026-10-22",
                            "ANNOUNCEMENT_SCHEDULE_NEW_YORK_DATE_UNDETERMINED:2026-10-22",
                            "EVALUATION_TIME_WITHIN_SCHEDULED_WINDOW_RELEASE_TIME_UNVERIFIED")
    after = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=UNZONED, statements=statements)
    assert after.freshness is Freshness.AWAITING_CAPTURE and after.expected_announcement_at is None
    assert after.reasons == ("FOMC_SCHEDULE_TIMEZONE_UNVERIFIED:2026-10-22",
                             "ANNOUNCEMENT_SCHEDULE_NEW_YORK_DATE_UNDETERMINED:2026-10-22",
                             "STATEMENT_FOR_SCHEDULED_ANNOUNCEMENT_NOT_CAPTURED", "DUE_SCHEDULED_WINDOW_PASSED")
    for f in (same, after):                   # the last verified decision stays visible, unchanged
        assert f.statement == earlier and f.previous_statement.statement_date == date(2026, 9, 16)
        assert f.consistency == "CONSISTENT" and f.range_change_since_previous.value == 0


def test_unrelated_statement_before_an_uncertain_window():
    before = [*REAL, unscheduled(day=OCT21, published=UNZONED_START - timedelta(hours=1))]
    assert fomc(UNZONED_START - timedelta(microseconds=1), schedules=UNZONED, statements=before).freshness \
        is Freshness.CURRENT
    assert fomc(UNZONED_START, schedules=UNZONED, statements=before).freshness is Freshness.RELEASE_TIME_UNKNOWN
    assert fomc(UNZONED_END, schedules=UNZONED, statements=before).freshness is Freshness.AWAITING_CAPTURE


@pytest.mark.parametrize("published, settled", [
    (UNZONED_START, False),                                 # the earliest instant the announcement could take
    (datetime(2026, 10, 22, 18, tzinfo=UTC), False),        # mid-window, even on the schedule's own date
    (UNZONED_END - timedelta(microseconds=1), False),       # the last instant the window denotes
    (UNZONED_END, True),                                    # after every instant: definitely later
    (UNZONED_END + timedelta(days=1), True),
])
def test_window_is_settled_only_by_a_definitely_later_statement(published, settled):
    record = unscheduled(day=published.astimezone(ZoneInfo(NY)).date(), published=published)
    f = fomc(UNZONED_END + timedelta(days=2), schedules=UNZONED, statements=[*REAL, record])
    assert f.statement == record
    assert f.freshness is (Freshness.CURRENT if settled else Freshness.AWAITING_CAPTURE)
    assert ("DUE_SCHEDULED_WINDOW_PASSED" in f.reasons) is not settled


def test_window_with_an_unzoned_hour_includes_its_last_possible_instant():
    unzoned = (fomc_date(tz=None, hh=14),)          # 14:00 in some zone: Oct 22 00:00Z .. Oct 23 02:00Z inclusive
    last = datetime(2026, 10, 23, 2, tzinfo=UTC)
    for published, status in ((last - timedelta(microseconds=1), Freshness.AWAITING_CAPTURE), (last, Freshness.CURRENT)):
        record = unscheduled(day=published.astimezone(ZoneInfo(NY)).date(), published=published)
        assert fomc(last + timedelta(hours=1), schedules=unzoned, statements=[*REAL, record]).freshness is status


def test_foreign_zone_window_is_not_settled_by_a_statement_within_it():
    london = (fomc_date(tz="Europe/London"),)       # 23:00Z Oct 21 .. 23:00Z Oct 22
    evening = unscheduled(day=OCT21, published=datetime(2026, 10, 21, 23, 30, tzinfo=UTC))   # 19:30 EDT Oct 21
    f = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=london, statements=[*REAL, evening])
    assert f.freshness is Freshness.AWAITING_CAPTURE and f.statement == evening
    tokyo = (fomc_date(tz="Asia/Tokyo"),)           # 15:00Z Oct 21 .. 15:00Z Oct 22
    after = unscheduled(published=datetime(2026, 10, 22, 15, tzinfo=UTC))
    assert fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=tokyo, statements=[*REAL, after]).freshness \
        is Freshness.CURRENT


def test_new_york_date_only_schedule_is_settled_by_the_statement_for_that_board_date():
    at = datetime(2026, 10, 23, 16, tzinfo=UTC)
    # Dated and published on Oct 22 in New York: the Board's statement for that date.
    for published in (datetime(2026, 10, 22, 4, tzinfo=UTC), datetime(2026, 10, 23, 3, 59, tzinfo=UTC)):
        assert fomc(at, schedules=(fomc_date(),), statements=[*REAL, unscheduled(published=published)]).freshness \
            is Freshness.CURRENT
    # 03:00 UTC on Oct 22 is still Oct 21 in New York: an Oct 21 statement, not the Oct 22 one.
    late_21 = unscheduled(day=OCT21, published=datetime(2026, 10, 22, 3, tzinfo=UTC))
    assert fomc(datetime(2026, 10, 22, 20, tzinfo=UTC), schedules=(fomc_date(),), statements=[*REAL, late_21]).freshness \
        is Freshness.RELEASE_TIME_UNKNOWN
    assert fomc(at, schedules=(fomc_date(),), statements=[*REAL, late_21]).freshness is Freshness.AWAITING_CAPTURE


@pytest.mark.parametrize("statement_date, published", [
    (OCT22, datetime(2026, 10, 22, 3, tzinfo=UTC)),     # dated Oct 22 but published on Oct 21 in New York
    (OCT21, datetime(2026, 10, 22, 18, tzinfo=UTC)),    # published on Oct 22 but dated Oct 21
])
def test_board_date_match_needs_both_the_statement_date_and_its_publication_date(statement_date, published):
    record = unscheduled(published=published).model_copy(update={"statement_date": statement_date})
    f = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=(fomc_date(),), statements=[*REAL, record])
    assert f.freshness is Freshness.AWAITING_CAPTURE and f.statement == record


def test_statement_before_a_verified_release_time_does_not_settle_it():
    morning = unscheduled(published=datetime(2026, 10, 22, 12, tzinfo=UTC))   # 08:00 EDT; scheduled 14:00 EDT
    timed = (fomc_time(day=OCT22),)
    before = fomc(datetime(2026, 10, 22, 17, tzinfo=UTC), schedules=timed, statements=[*REAL, morning])
    assert before.freshness is Freshness.CURRENT and before.expected_announcement_at == datetime(2026, 10, 22, 18, tzinfo=UTC)
    assert "ANNOUNCEMENT_SCHEDULED_LATER_ON_EVALUATION_DATE" in before.reasons
    due = fomc(datetime(2026, 10, 22, 18, tzinfo=UTC), schedules=timed, statements=[*REAL, morning])
    assert due.freshness is Freshness.AWAITING_CAPTURE and due.statement == morning
    assert due.reasons[-2:] == ("STATEMENT_FOR_SCHEDULED_ANNOUNCEMENT_NOT_CAPTURED", "DUE_BY_VERIFIED_RELEASE_TIME")
    on_time = unscheduled(published=datetime(2026, 10, 22, 18, tzinfo=UTC))
    assert fomc(datetime(2026, 10, 22, 18, tzinfo=UTC), schedules=timed, statements=[*REAL, on_time]).freshness \
        is Freshness.CURRENT


def test_calendar_meeting_matching_with_and_without_a_verified_time():
    at = datetime(2026, 10, 28, 19, tzinfo=UTC)
    early = october(published=datetime(2026, 10, 28, 12, tzinfo=UTC))       # dated Oct 28, 08:00 EDT
    # The calendar alone gives no time: the Board's statement for the meeting date settles it.
    assert fomc(at, statements=[*REAL, early]).freshness is Freshness.CURRENT
    # A verified 14:00 EDT release time is not met by an 08:00 EDT statement.
    timed = fomc(at, schedules=(fomc_time(),), statements=[*REAL, early])
    assert timed.freshness is Freshness.AWAITING_CAPTURE and timed.expected_announcement.end_date == OCT
    assert timed.reasons[-2:] == ("STATEMENT_FOR_PAST_MEETING_NOT_CAPTURED", "DUE_BY_VERIFIED_RELEASE_TIME")
    assert fomc(at, schedules=(fomc_time(),), statements=[*REAL, october()]).freshness is Freshness.CURRENT


def test_multiple_statements_and_announcements():
    schedules = (fomc_date(day=date(2026, 10, 20)), *UNZONED, fomc_time())     # Oct 20, Oct 22 window, Oct 28 14:00 EDT
    oct20 = unscheduled(day=date(2026, 10, 20), published=datetime(2026, 10, 20, 18, tzinfo=UTC))
    oct23 = unscheduled(day=date(2026, 10, 23), published=datetime(2026, 10, 23, 13, tzinfo=UTC))   # after the window
    one = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=schedules, statements=[*REAL, oct20])
    assert one.freshness is Freshness.AWAITING_CAPTURE and one.statement == oct20
    assert one.reasons[-1] == "DUE_SCHEDULED_WINDOW_PASSED"
    two = fomc(datetime(2026, 10, 23, 16, tzinfo=UTC), schedules=schedules, statements=[*REAL, oct20, oct23])
    assert two.freshness is Freshness.CURRENT and two.statement == oct23 and two.previous_statement == oct20
    meeting = fomc(datetime(2026, 10, 28, 19, tzinfo=UTC), schedules=schedules, statements=[*REAL, oct20, oct23])
    assert meeting.freshness is Freshness.AWAITING_CAPTURE and meeting.statement == oct23
    assert meeting.expected_announcement_at == datetime(2026, 10, 28, 18, tzinfo=UTC)
    settled = fomc(datetime(2026, 10, 28, 19, tzinfo=UTC), schedules=schedules, statements=[*REAL, oct20, oct23, october()])
    assert settled.freshness is Freshness.CURRENT and settled.reasons == ("FOMC_SCHEDULE_TIMEZONE_UNVERIFIED:2026-10-22",)


def test_matching_is_deterministic_over_duplicates_and_order():
    at = datetime(2026, 10, 23, 16, tzinfo=UTC)
    inside = unscheduled(day=OCT21, published=datetime(2026, 10, 21, 18, tzinfo=UTC))
    copy = inside.model_copy(update={"provenance": inside.provenance.model_copy(
        update={"received_timestamp": datetime(2026, 10, 21, 19, tzinfo=UTC)})})
    schedules = [*UNZONED, *UNZONED, fomc_date(day=date(2026, 10, 20)), fomc_date(tz="Europe/London")]
    statements = [*REAL, inside, copy]
    baseline = build(at=at, schedules=schedules, statements=statements, calendars=(CAL,))
    assert baseline.fomc.freshness is Freshness.AWAITING_CAPTURE and baseline.fomc.statement == inside
    for perm in itertools.permutations(schedules):
        assert build(at=at, schedules=perm, statements=statements[::-1], calendars=(CAL,)).model_dump_json() \
            == baseline.model_dump_json()


# ============================================================= Decimal-context determinism
def _scenarios():
    reduction = REAL[3].model_copy(update={"action": PolicyAction.LOWER, "target_lower_percent": D("3.25"),
                                           "target_upper_percent": D("3.5")})            # test-only record
    invalid = REAL[3].model_copy(update={"target_upper_percent": D("4.25")})
    yield "raise", build(statements=REAL, calendars=(CAL,), caps=captures(AT))
    yield "maintain", build(at=datetime(2026, 2, 1, tzinfo=UTC), statements=REAL, calendars=(CAL,))
    yield "target-only", build(at=datetime(2023, 8, 1, tzinfo=UTC), schedules=(),
                               statements=[statement("20230614", 18), statement("20230726", 18)])
    yield "reduction", build(statements=[*REAL[:3], reduction], calendars=(CAL,))
    yield "invalid", build(statements=[*REAL[:3], invalid], calendars=(CAL,))


EXPECTED = {"raise": "CONSISTENT", "maintain": "CONSISTENT", "target-only": "CONSISTENT", "reduction": "CONSISTENT",
            "invalid": "CONTRADICTORY"}


def test_full_reports_are_identical_in_every_decimal_context():
    baseline = {name: r.model_dump_json() for name, r in _scenarios()}
    assert {name: r.fomc.consistency for name, r in _scenarios()} == EXPECTED
    for prec, rounding in itertools.product((1, 2, 3, 6, 28, 100), (ROUND_DOWN, ROUND_UP)):
        with localcontext() as ctx:
            ctx.prec, ctx.rounding = prec, rounding
            assert {name: r.model_dump_json() for name, r in _scenarios()} == baseline, (prec, rounding)


def test_original_round_down_case_is_consistent():
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 1, ROUND_DOWN
        f = build(statements=REAL, calendars=(CAL,)).fomc
    assert f.consistency == "CONSISTENT" and f.range_change_since_previous.value == D("0.25")


# ================================================================= ETF mapping lookahead
def fund(ticker, cik, **kw):
    return EtfFund(ticker=ticker, registrant_name=f"Test fund {ticker}", cik=cik, exchange="TEST",
                   applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence="test fixture", **kw)


def mapping(version, available, funds, as_of=None):
    """Test-only mappings with fictional funds; no real launch date is asserted."""
    return AssetEtfMapping(asset="BTC", jurisdiction="US", mapping_version=version, funds=tuple(funds),
                           identity_source="test", identity_retrieved_on=as_of or available.date(),
                           available_at=available, available_at_evidence="test fixture")


A = fund("TSTA", 1, valid_from=date(2024, 1, 11), validity_evidence="test fixture")
B = fund("TSTB", 2, valid_from=date(2024, 5, 1), validity_evidence="test fixture")
V1 = mapping("v1", datetime(2024, 1, 2, tzinfo=UTC), [A])
V2 = mapping("v2", datetime(2024, 6, 1, tzinfo=UTC), [A, B])


def coverage(at, mappings=(V1, V2), **kw):
    return build_etf_evidence(evaluation_time=at, mappings=mappings, **kw)


def tickers(report):
    return [f.ticker for f in report.metrics[0].funds]


def test_before_any_mapping_was_known_coverage_is_unavailable_not_retroactive():
    r = build_etf_evidence(evaluation_time=datetime(2023, 6, 1, tzinfo=UTC))
    assert r.mapping_state == "NO_MAPPING_KNOWN_AT_EVALUATION_TIME" and r.mapping_version is None
    assert r.excluded_mappings_after_evaluation == 1 and r.unverified_applicability == ()
    assert all(m.funds == () and m.coverage == "NONE" and m.aggregate.reason == "NO_MAPPING_KNOWN_AT_EVALUATION_TIME"
               for m in r.metrics)


def test_shipped_mapping_becomes_usable_exactly_when_it_was_recorded():
    recorded = datetime(2026, 10, 21, 19, 58, 30, tzinfo=UTC)
    assert US_SPOT_BTC_ETFS.available_at == recorded
    assert build_etf_evidence(evaluation_time=recorded - timedelta(microseconds=1)).mapping_state != "AVAILABLE"
    now = build_etf_evidence(evaluation_time=recorded)
    assert now.mapping_state == "AVAILABLE" and len(tickers(now)) == 11
    older = build_etf_evidence(evaluation_time=datetime(2026, 10, 23, tzinfo=UTC), trade_date=date(2026, 10, 20))
    assert all(m.funds == () and m.aggregate.reason == "FUND_VALIDITY_AT_TRADE_DATE_UNVERIFIED" for m in older.metrics)


def test_launch_boundary_and_receipt_boundary_of_a_mapping_version():
    assert coverage(V1.available_at - timedelta(microseconds=1)).mapping_state == "NO_MAPPING_KNOWN_AT_EVALUATION_TIME"
    before_launch = coverage(datetime(2024, 1, 10, 23, tzinfo=UTC))      # Jan 10 in New York
    assert before_launch.mapping_version == "v1" and tickers(before_launch) == []
    assert before_launch.metrics[0].aggregate.reason == "NO_MAPPED_FUND_VALID_AT_TRADE_DATE"
    assert tickers(coverage(datetime(2024, 1, 11, 22, tzinfo=UTC))) == ["TSTA"]


def test_a_later_mapping_revision_never_rewrites_an_earlier_evaluation():
    may = coverage(datetime(2024, 5, 15, 20, tzinfo=UTC))
    assert may.mapping_version == "v1" and tickers(may) == ["TSTA"] and may.excluded_mappings_after_evaluation == 1
    later = coverage(datetime(2024, 6, 2, tzinfo=UTC), providers=PROVIDERS + (APPROVED,), trade_date=date(2024, 5, 15),
                     observations=tuple(obs(t, day=date(2024, 5, 15), received=datetime(2024, 5, 16, tzinfo=UTC))
                                        for t in ("TSTA", "TSTB")))
    m = later.metrics[0]
    assert later.mapping_version == "v2" and [f.ticker for f in m.funds] == ["TSTA", "TSTB"] and m.coverage == "COMPLETE"
    april = coverage(datetime(2024, 6, 2, tzinfo=UTC), trade_date=date(2024, 4, 30))
    assert tickers(april) == ["TSTA"]                                    # TSTB was not yet valid


def test_validity_end_and_conflicting_versions():
    closed = fund("TSTA", 1, valid_from=date(2024, 1, 11), valid_until=date(2024, 3, 1), validity_evidence="test fixture")
    v = mapping("v3", datetime(2024, 1, 2, tzinfo=UTC), [closed])
    assert tickers(coverage(datetime(2024, 3, 2, 22, tzinfo=UTC), mappings=(v,))) == []
    twin = mapping("v1-other", V1.available_at, [B])
    r = coverage(datetime(2024, 5, 2, tzinfo=UTC), mappings=(V1, twin))
    assert r.mapping_state == "CONFLICTING_MAPPING_VERSIONS" and all(m.funds == () for m in r.metrics)
    with pytest.raises(ValidationError):
        fund("TSTC", 3, valid_from=date(2024, 1, 1))                     # a period without evidence
    with pytest.raises(ValidationError):
        fund("TSTC", 3, valid_from=date(2024, 2, 1), valid_until=date(2024, 1, 1), validity_evidence="x")
    with pytest.raises(ValidationError):
        mapping("bad", datetime(2024, 1, 1, tzinfo=UTC), [A], as_of=date(2024, 1, 2))   # available before its facts


def test_trade_dates_are_compared_on_the_new_york_session():
    at = datetime(2026, 10, 22, 2, tzinfo=UTC)                            # Oct 21, 22:00 EDT
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    r = build_etf_evidence(evaluation_time=at, providers=PROVIDERS + (APPROVED,),
                           observations=tuple(obs(t, day=date(2026, 10, 22)) for t in funds))
    assert r.excluded_after_evaluation == len(funds)
    with pytest.raises(ValueError, match="session date"):
        build_etf_evidence(evaluation_time=at, trade_date=date(2026, 10, 22))


# ======================================================================= economic units
def test_payroll_employment_is_a_level_of_jobs_not_persons_or_a_change():
    spec = BLS_SERIES["CES0000000001"]
    assert spec.unit == "thousands of payroll jobs" and "person" not in spec.unit and spec.measure == "LEVEL"
    sch = (sched("2026-09", date(2026, 10, 2), event="EMPLOYMENT_SITUATION"),
           sched("2026-10", date(2026, 11, 6), event="EMPLOYMENT_SITUATION"))
    nfp = series(build(schedules=sch, caps=captures(datetime(2026, 10, 2, 12, 40, tzinfo=UTC))), "CES0000000001")
    assert nfp.known_value.value == D(159044) and nfp.previous_known.value == D(159015)   # levels, not +29
    assert not any("change" in name for name in SeriesEvidence.model_fields)
    assert {s.measure for s in BLS_SERIES.values()} == {"LEVEL", "RATE"} and BLS_SERIES["LNS14000000"].measure == "RATE"
