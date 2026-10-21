"""Point-in-time regressions: release vintage, simultaneous conflicts, FOMC currentness and
derived changes, Decimal-context independence, ETF mapping lookahead and economic units."""
import copy
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext
import itertools

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
