"""C13 optional read-only C12 adapter (design §8, owner decision O3 option a).

Uses REAL C12 code (build_macro_evidence, parsers) on the repository's C12 fixtures (tests/fixtures/macro);
same-date twins, conflicting copies and contradictory pairs are SYN edits of those real statements."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import itertools
import json
from pathlib import Path

from news_support import _no_network, claim, curate  # noqa: F401  (autouse fixture)
from traid.macro import ScheduledRelease
from traid.macro.bls import parse_bls_response
from traid.macro.evidence import build_macro_evidence
from traid.macro.fed import STATEMENT_TITLE, FeedItem, parse_fomc_calendar, parse_fomc_statement
from traid.macro.models import BLS_SERIES, FomcCalendar, FomcMeeting, FomcStatement
from traid.news import OfficialEvidence, verify
from traid.news.macro_adapter import C12MacroEvaluator
from traid.news.models import BLS_SERIES_TOKENS, FactOutcome, VerificationState

UTC = timezone.utc
S = VerificationState
FIX = Path(__file__).parent / "fixtures" / "macro"
T = datetime(2026, 10, 21, 20, tzinfo=UTC)        # the R3 scenario: next meeting Oct 27-28, statements Sep 16 and Jul 29


def statement(stamp, hour):
    y, m, d = int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])
    item = FeedItem(title=STATEMENT_TITLE, url=f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{stamp}a.htm",
                    published_at=datetime(y, m, d, hour, tzinfo=UTC))
    return parse_fomc_statement((FIX / f"fed_statement_{stamp}a.html").read_text(), item=item,
                                received=item.published_at + timedelta(minutes=1))


CAL = parse_fomc_calendar((FIX / "fed_fomc_calendar.html").read_text(), received=datetime(2025, 1, 2, tzinfo=UTC))
REAL = [statement("20251210", 19), statement("20260128", 19), statement("20260729", 18), statement("20260916", 18)]
SEP = REAL[3]


def fomc_time(day=date(2026, 10, 28), hh=14, retrieved=datetime(2026, 10, 1, tzinfo=UTC)):
    return ScheduledRelease(event_type="FOMC_DECISION", reference_period=f"{day:%Y-%m}", release_date=day, release_time=time(hh),
                            timezone="America/New_York", timezone_evidence="Curated for this test",
                            source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", retrieved_at=retrieved)


def report(at=T, statements=REAL, calendars=(CAL,), schedules=(), **kw):
    return build_macro_evidence(evaluation_time=at, fomc_statements=tuple(statements), fomc_calendars=tuple(calendars),
                                schedules=tuple(schedules), **kw)


def run(c, cur, rep, at=T):
    out = verify(claims=(c,), curations=(cur,), evidence=OfficialEvidence(), evaluation_time=at, macro=C12MacroEvaluator(rep))
    return out.results[0]


def one(frame_type, identity, facts, *, text="macro claim", at=T, **kw):
    c = claim(text, received=at - timedelta(hours=1), **kw)
    return c, curate(c, [("e", frame_type, identity)], [("p", "e", facts)])


def decision(board_date, action, extra=(), at=T):
    return one("FOMC_DECISION", {"board_date": board_date}, [("ACTION", action), *extra], at=at)


def schedule(start="2026-10-27", end="2026-10-28", extra=()):
    return one("FOMC_SCHEDULE", {"meeting_start": start, "meeting_end": end}, [("SCHEDULED_ON", f"{start}/{end}"), *extra])


def latest_fomc(board_date, at=T):
    return one("LATEST_IDENTITY", {"sequence": "FOMC_STATEMENTS", "board_date": board_date}, [("MEMBER_IS_LATEST", "true")], at=at)


def twin(s: FomcStatement, minutes=30) -> FomcStatement:
    """SYN: a second statement carrying the same Board date, at a distinct URL and later time."""
    data = s.model_dump()
    data.update(url=s.url.replace("a.htm", "b.htm"), published_at=s.published_at + timedelta(minutes=minutes),
                provenance={**data["provenance"], "received_timestamp": s.published_at + timedelta(minutes=minutes + 1)})
    return FomcStatement.model_validate(data)


def test_series_tokens_match_the_c12_registry():
    assert set(BLS_SERIES_TOKENS) == set(BLS_SERIES)


# ------------------------------------------------------------------ FOMC decisions (M03-M06, R6, F2)
def test_c00_real_c12_scenario():
    f = report().fomc
    assert (f.statement.statement_date, f.previous_statement.statement_date) == (date(2026, 9, 16), date(2026, 7, 29))
    assert (f.next_meeting.start_date, f.next_meeting.end_date, f.freshness.value) == (date(2026, 10, 27), date(2026, 10, 28), "CURRENT")


def test_m03_m04_m05_decisions():
    assert run(*decision("2026-09-16", "RAISE"), report()).state is S.CONFIRMED
    r = run(*decision("2026-09-16", "MAINTAIN"), report())
    assert r.state is S.UNVERIFIED and r.reasons == ("FOMC_STATEMENT_NOT_UNIQUELY_IDENTIFIED_BY_DATE",)   # no contradiction path
    assert run(*decision("2026-07-29", "MAINTAIN"), report()).state is S.CONFIRMED
    assert run(*decision("2026-01-28", "MAINTAIN"), report()).reasons == ("NOT_PROVIDED_BY_C12_EVIDENCE",)


def test_target_range_qualifier_and_change_sizes():
    ok = decision("2026-09-16", "RAISE", [("TARGET_RANGE", "3.75-4.00"), ("CHANGE_SIZE", "0.25", "STATED_IN_DECISION")])
    assert run(*ok, report()).state is S.CONFIRMED
    derived = decision("2026-09-16", "RAISE", [("CHANGE_SIZE", "0.25", "DERIVED_COMPARISON")])
    assert run(*derived, report()).state is S.CONFIRMED                           # C12 says CONSISTENT and publishes 0.25
    wrong = decision("2026-09-16", "RAISE", [("TARGET_RANGE", "4.00-4.25")])
    assert run(*wrong, report()).state is S.PARTIALLY_CONFIRMED                   # unequal qualifier: unresolved, never MISLEADING
    previous = decision("2026-07-29", "MAINTAIN", [("CHANGE_SIZE", "0.25", "STATED_IN_DECISION")])
    r = run(*previous, report())
    assert r.state is S.PARTIALLY_CONFIRMED and "STATED_CHANGE_NOT_IN_STATEMENT" in r.reasons   # M06n: never derived
    old_derived = decision("2026-07-29", "MAINTAIN", [("CHANGE_SIZE", "0.25", "DERIVED_COMPARISON")])
    assert "NOT_PROVIDED_BY_C12_EVIDENCE" in run(*old_derived, report()).reasons


def test_m06_continuity_unverified_keeps_stated_size_and_withholds_derived():
    rep = report(statements=[REAL[0], SEP])        # Jan and Jul missing: intervening meetings not captured
    assert rep.fomc.consistency in ("INTERVENING_MEETING_NOT_CAPTURED", "CONTINUITY_UNVERIFIED")
    stated = decision("2026-09-16", "RAISE", [("CHANGE_SIZE", "0.25", "STATED_IN_DECISION")])
    assert run(*stated, rep).state is S.CONFIRMED
    derived = run(*decision("2026-09-16", "RAISE", [("CHANGE_SIZE", "0.25", "DERIVED_COMPARISON")]), rep)
    assert derived.state is S.PARTIALLY_CONFIRMED and f"C12:{rep.fomc.consistency}" in derived.reasons


def test_m06c_contradictory_pair_withholds_both_stated_sizes():
    lowered = FomcStatement.model_validate({**SEP.model_dump(), "target_lower_percent": Decimal("3.25"), "target_upper_percent": Decimal("3.50")})
    rep = report(statements=[REAL[2], lowered])
    assert rep.fomc.consistency == "CONTRADICTORY"
    r = run(*decision("2026-09-16", "RAISE", [("CHANGE_SIZE", "0.25", "STATED_IN_DECISION")]), rep)
    assert {"CONFLICTING_SOURCE_EVIDENCE", "C12:CONTRADICTORY"} <= set(r.reasons)


def test_f2_same_date_statements_are_ambiguous_in_any_order():
    statements = [REAL[2], SEP, twin(SEP)]
    outcomes = set()
    for order in itertools.permutations(statements):
        rep = report(statements=order)
        r = run(*decision("2026-09-16", "RAISE"), rep)
        outcomes.add((r.state, r.reasons, rep.input_digest))
    assert outcomes == {(S.UNVERIFIED, ("FOMC_STATEMENT_IDENTITY_AMBIGUOUS:2026-09-16",), report(statements=statements).input_digest)}
    assert run(*latest_fomc("2026-09-16"), report(statements=statements)).reasons == ("FOMC_STATEMENT_IDENTITY_AMBIGUOUS:2026-09-16",)
    assert run(*schedule(), report(statements=statements)).state is S.CONFIRMED          # C31: schedule unaffected


def test_m01_c34_conflicting_statement_copies():
    conflicting = FomcStatement.model_validate({**SEP.model_dump(), "decision_text": "altered copy",
                                                "provenance": {**SEP.provenance.model_dump(),
                                                               "received_timestamp": SEP.provenance.received_timestamp + timedelta(minutes=5)}})
    rep = report(statements=REAL + [conflicting])
    assert rep.fomc.statement is None and "CONFLICTING_STATEMENT_COPIES" in rep.fomc.reasons
    for c, cur in (decision("2026-07-29", "MAINTAIN"), latest_fomc("2026-07-29"),
                   decision("2026-09-16", "RAISE", [("CHANGE_SIZE", "0.25", "STATED_IN_DECISION")])):
        r = run(c, cur, rep)
        assert r.state is S.UNVERIFIED and r.reasons == ("C12:CONFLICTING_STATEMENT_COPIES",)
    assert run(*schedule(), rep).state is S.CONFIRMED                                     # R3: no statement gate for schedules


def test_m02_report_not_at_evaluation_time_and_no_report():
    rep = report(at=T - timedelta(hours=1))
    r = run(*decision("2026-09-16", "RAISE"), rep)
    assert r.reasons == ("C12_REPORT_NOT_AT_EVALUATION_TIME",)
    c, cur = decision("2026-09-16", "RAISE")
    plain = verify(claims=(c,), curations=(cur,), evidence=OfficialEvidence(), evaluation_time=T).results[0]
    assert plain.reasons == ("MACRO_EVIDENCE_NOT_CONFIGURED",)
    assert run(c, cur, None).reasons == ("MACRO_EVIDENCE_NOT_PROVIDED",)


def test_m07_m07l_current_range_and_latest_identity():
    r = run(*one("FOMC_CURRENT_RANGE", {}, [("TARGET_RANGE", "3.75-4.00")]), report())
    assert r.state is S.UNVERIFIED and r.reasons == ("STATUS_COVERAGE_INCOMPLETE",)
    assert {c.c12_field_path for c in r.frames[0].facts[0].citations} == {"fomc.statement", "fomc.previous_statement"}
    old = run(*latest_fomc("2026-07-29"), report())
    assert old.state is S.OUTDATED and f"LATER_SEQUENCE_MEMBER_KNOWN:{SEP.url}" in old.reasons
    assert run(*latest_fomc("2026-09-16"), report()).reasons == ("LATEST_NOT_PROVABLE",)
    equal_time = FomcStatement.model_validate({**REAL[2].model_dump(), "published_at": SEP.published_at,
                                               "provenance": {**REAL[2].provenance.model_dump(), "received_timestamp": SEP.provenance.received_timestamp}})
    tie = report(statements=[equal_time, SEP])
    assert run(*latest_fomc("2026-07-29"), tie).reasons == ("LATEST_NOT_PROVABLE",)     # C12's URL tie-break is not "later"


def test_c03_future_decision_and_c04_schedule_plus_decision():
    assert run(*decision("2026-10-28", "MAINTAIN"), report()).reasons == ("FUTURE_EVENT",)
    c = claim("The FOMC meets Oct 27-28 and will hold rates", received=T - timedelta(hours=1))
    cur = curate(c, [("s", "FOMC_SCHEDULE", {"meeting_start": "2026-10-27", "meeting_end": "2026-10-28"}),
                     ("d", "FOMC_DECISION", {"board_date": "2026-10-28"})],
                 [("p1", "s", [("SCHEDULED_ON", "2026-10-27/2026-10-28")]), ("p2", "d", [("ACTION", "MAINTAIN")])], distinct=(("s", "d"),))
    r = run(c, cur, report())
    assert r.state is S.PARTIALLY_CONFIRMED and {"SCHEDULE_ONLY_NOT_OCCURRENCE_OR_DECISION", "FUTURE_EVENT"} <= set(r.reasons)


# ------------------------------------------------------------------ FOMC schedule (R3)
def test_c02_schedule_confirmed_as_schedule_only():
    r = run(*schedule(), report())
    assert r.state is S.CONFIRMED and r.reasons == ("SCHEDULE_ONLY_NOT_OCCURRENCE_OR_DECISION",)


def test_c05_c06_wrong_dates_and_unexposed_announcement_time():
    assert run(*schedule("2026-12-08", "2026-12-09"), report()).reasons == ("NOT_PROVIDED_BY_C12_EVIDENCE",)
    r = run(*schedule(extra=[("ANNOUNCEMENT_TIME", "2026-10-28T18:00:00+00:00")]), report())
    assert r.state is S.PARTIALLY_CONFIRMED and "ANNOUNCEMENT_TIME_NOT_PROVIDED_BY_C12_EVIDENCE" in r.reasons
    r = run(*schedule(extra=[("PROJECTIONS", "false")]), report())
    assert r.state is S.CONFIRMED
    assert run(*schedule(extra=[("PROJECTIONS", "true")]), report()).state is S.PARTIALLY_CONFIRMED


def test_c10_c13_calendar_availability():
    assert run(*schedule(), report(calendars=())).reasons == ("SCHEDULE_EVIDENCE_UNAVAILABLE",)
    late = CAL.model_copy(update={"provenance": CAL.provenance.model_copy(update={"received_timestamp": T + timedelta(minutes=1)})})
    assert run(*schedule(), report(calendars=(late,))).reasons == ("SCHEDULE_EVIDENCE_UNAVAILABLE",)
    exact = CAL.model_copy(update={"provenance": CAL.provenance.model_copy(update={"received_timestamp": T})})
    assert run(*schedule(), report(calendars=(exact,))).state is S.CONFIRMED
    after = datetime(2026, 10, 29, 20, tzinfo=UTC)
    c, cur = schedule()
    c = claim(c.text, received=after - timedelta(hours=1))
    cur = cur.model_copy(update={"claim_id": c.claim_id, "curated_at": c.claim_received_at})
    assert run(c, cur, report(at=after), at=after).reasons == ("NOT_PROVIDED_BY_C12_EVIDENCE",)


def test_c20_c22_conflicting_schedule_evidence_and_notation_votes():
    rep = report(schedules=(fomc_time(hh=14), fomc_time(hh=15)))
    r = run(*schedule(), rep)
    assert r.state is S.UNVERIFIED and r.reasons[0].startswith("CONFLICTING_SCHEDULE_EVIDENCE:CONFLICTING_FOMC_RELEASE_TIMES:")
    rep = report(schedules=(fomc_time(day=date(2026, 10, 22)),))
    assert run(*schedule(), rep).reasons[0].startswith("CONFLICTING_SCHEDULE_EVIDENCE:ANNOUNCEMENT_SCHEDULE_WITHOUT_CALENDAR_MEETING:")
    notation = FomcCalendar(meetings=(FomcMeeting(start_date=date(2026, 10, 27), end_date=date(2026, 10, 27), projections=False,
                                                  notation_vote=True),),
                            source_url=CAL.source_url, provenance=CAL.provenance)
    assert run(*schedule("2026-10-27", "2026-10-27"), report(calendars=(notation,))).reasons == ("CALENDAR_ENTRY_IS_NOTATION_VOTE",)


def test_c40_verified_release_time_is_a_schedule_fact():
    at = datetime(2026, 10, 28, 19, tzinfo=UTC)
    rep = report(at=at, schedules=(fomc_time(),))
    assert rep.fomc.expected_announcement_at == datetime(2026, 10, 28, 18, tzinfo=UTC)
    c = claim("The FOMC statement is due at 2pm EDT on Oct 28", received=at - timedelta(hours=1))
    cur = curate(c, [("s", "FOMC_SCHEDULE", {"meeting_start": "2026-10-27", "meeting_end": "2026-10-28"})],
                 [("p", "s", [("SCHEDULED_ON", "2026-10-27/2026-10-28"), ("ANNOUNCEMENT_TIME", "2026-10-28T14:00:00-04:00")])])
    assert run(c, cur, rep, at=at).state is S.CONFIRMED
    c2, cur2 = decision("2026-10-28", "MAINTAIN")
    c2 = claim(c2.text, received=at - timedelta(hours=1))
    cur2 = cur2.model_copy(update={"claim_id": c2.claim_id, "curated_at": c2.claim_received_at})
    assert run(c2, cur2, rep, at=at).state is S.UNVERIFIED


def test_c50_statement_input_permutations_give_identical_results():
    results = set()
    for order in itertools.permutations(REAL):
        rep = report(statements=order)
        r = run(*latest_fomc("2026-07-29"), rep)
        results.add((rep.model_dump_json(), r.model_dump_json()))
    assert len(results) == 1


# ------------------------------------------------------------------ BLS (M09-M15, R3)
BLS = json.loads((FIX / "bls_v2_timeseries.json").read_text())
SERIES = tuple(sorted(BLS_SERIES))


def cpi_schedule(period, day):
    return ScheduledRelease(event_type="CPI", reference_period=period, release_date=day, release_time=time(8, 30), timezone="America/New_York",
                            timezone_evidence="Curated for this test", source_url="https://www.bls.gov/schedule/news_release/cpi.htm",
                            retrieved_at=datetime(2026, 10, 1, tzinfo=UTC))


AT = datetime(2026, 10, 20, tzinfo=UTC)
CPI_SCHEDULE = (cpi_schedule("2026-09", date(2026, 10, 15)), cpi_schedule("2026-10", date(2026, 11, 10)))


def with_value(period, value, sid="CUUR0000SA0"):
    import copy
    changed = copy.deepcopy(BLS)
    for s in changed["Results"]["series"]:
        if s["seriesID"] == sid:
            for row in s["data"]:
                if f"{row['year']}-{row['period'][1:]}" == period:
                    row["value"] = value
    return changed


def bls_report(*payloads_and_times):
    captures = ()
    for payload, received in payloads_and_times:
        captures += parse_bls_response(payload, SERIES, received)
    return build_macro_evidence(evaluation_time=AT, bls_captures=captures, schedules=CPI_SCHEDULE)


def value(series, period, scope, x, unit=None):
    facts = [("VALUE", x)] + ([("UNIT", unit)] if unit else [])
    return one("MACRO_VALUE", {"series": series, "period": period, "scope": scope}, facts, at=AT)


def brun(c, cur, rep):
    return run(c, cur, rep, at=AT)


REVISED = lambda: bls_report((BLS, datetime(2026, 10, 15, 13, tzinfo=UTC)),
                             (with_value("2026-09", "337.100"), datetime(2026, 10, 16, 13, tzinfo=UTC)))


def test_m09_value_as_published_at_some_receipt_including_its_revisions():
    rep = REVISED()
    se = next(s for s in rep.series if s.series_id == "CUUR0000SA0")
    assert [r.raw_value for r in se.revisions] == ["336.940", "337.100"]
    for x in ("336.940", "337.100", "337.1"):
        r = brun(*value("CUUR0000SA0", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", x, "index, 1982-84=100"), rep)
        assert r.state is S.CONFIRMED, x


def test_m09c_m10_current_value_and_unmatched_value_are_never_concluded_or_false():
    rep = REVISED()
    r = brun(*value("CUUR0000SA0", "2026-09", "CURRENT", "337.100"), rep)
    assert r.state is S.UNVERIFIED and "STATUS_COVERAGE_INCOMPLETE" in r.reasons
    r = brun(*value("CUUR0000SA0", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "300"), rep)
    assert r.state is S.UNVERIFIED and {"NO_QUALIFYING_EVIDENCE", "UNCAPTURED_VINTAGE_NOT_EXCLUDABLE"} <= set(r.reasons)


def test_r3_previous_period_binding():
    rep = REVISED()
    se = next(s for s in rep.series if s.series_id == "CUUR0000SA0")
    assert brun(*value("CUUR0000SA0", "2026-08", "AS_PUBLISHED_AT_SOME_RECEIPT", str(se.previous_known.value)), rep).state is S.CONFIRMED
    # M09p: a value equal to one of P's revisions is never evidence for P-1
    assert brun(*value("CUUR0000SA0", "2026-08", "AS_PUBLISHED_AT_SOME_RECEIPT", "336.940"), rep).state is S.UNVERIFIED
    r = brun(*value("CUUR0000SA0", "2026-08", "CURRENT", str(se.previous_known.value)), rep)          # M09q
    assert r.reasons == ("PRIOR_PERIOD_REVISION_HISTORY_NOT_PROVIDED_BY_C12",)
    assert brun(*value("CUUR0000SA0", "2026-07", "AS_PUBLISHED_AT_SOME_RECEIPT", "1"), rep).reasons == ("NOT_PROVIDED_BY_C12_EVIDENCE",)


def test_m11_conflicting_receipts_and_m12_m13_m15():
    at = datetime(2026, 10, 15, 13, tzinfo=UTC)
    rep = bls_report((BLS, at), (with_value("2026-09", "999.999"), at))
    r = brun(*value("CUUR0000SA0", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "336.940"), rep)
    assert r.reasons == ("CONFLICTING_SOURCE_EVIDENCE",)
    rep = REVISED()
    assert brun(*value("CUUR0000SA0", "2026-09", "ORIGINAL", "336.940"), rep).reasons == (
        "C12:ORIGINAL_RELEASE_VINTAGE_NOT_ESTABLISHED_NO_VINTAGE_SOURCE",)
    cons = one("MACRO_CONSENSUS", {"series": "CUUR0000SA0", "period": "2026-09"}, [("CONSENSUS", "336.5")], at=AT)
    assert brun(*cons, rep).reasons == ("C12:NO_APPROVED_CONSENSUS_SOURCE",)
    for kind, why in (("MOM_PCT", "DERIVATION_METHOD_UNVERIFIED"), ("LEVEL_DIFF", "DERIVATION_METHOD_UNVERIFIED"),
                      ("YOY_PCT", "NOT_PROVIDED_BY_C12_EVIDENCE")):
        assert brun(*one("MACRO_CHANGE", {"series": "CES0000000001", "period": "2026-09", "change_kind": kind}, [("CHANGE", "150")], at=AT),
                    rep).reasons == (why,)
    for token in ("PCE", "GDP"):
        r = brun(*value(token, "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "1"), rep)
        assert r.reasons == ("C12:BEA_API_REQUIRES_REGISTERED_USERID_NOT_CONFIGURED",)


def test_m14_ambiguous_series_and_units():
    rep = REVISED()
    r = brun(*value("CPI", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "336.940"), rep)     # SA 336.298, NSA 336.940
    assert r.state is S.UNVERIFIED and "AMBIGUOUS_SERIES" in r.reasons
    r = brun(*value("CES0000000001", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "159044", "percent"), rep)
    assert r.state is S.UNVERIFIED and "AMBIGUOUS_UNIT" in r.reasons


def test_m16_c12_withholding_never_becomes_confirmed_or_false():
    """Exhaustive: every C12 withholding state x every macro frame type; no CONTRADICTED anywhere, no SUPPORTED withheld field."""
    withholding = {
        "no-bls-capture": build_macro_evidence(evaluation_time=AT, schedules=CPI_SCHEDULE),
        "no-schedule": build_macro_evidence(evaluation_time=AT, bls_captures=parse_bls_response(BLS, SERIES, datetime(2026, 10, 16, tzinfo=UTC))),
        "conflicting-receipts": bls_report((BLS, datetime(2026, 10, 15, 13, tzinfo=UTC)), (with_value("2026-09", "1.1"), datetime(2026, 10, 15, 13, tzinfo=UTC))),
        "no-statement": report(at=AT, statements=[]),
        "conflicting-copies": report(at=AT, statements=[SEP, FomcStatement.model_validate({**SEP.model_dump(), "decision_text": "x"})]),
        "no-calendar": report(at=AT, calendars=()),
    }
    frames = [value("CUUR0000SA0", "2026-09", s, "336.940") for s in ("CURRENT", "ORIGINAL")] + [
        value("CUUR0000SA0", "2026-08", s, "334.980") for s in ("CURRENT",)] + [
        one("MACRO_CONSENSUS", {"series": "CUUR0000SA0", "period": "2026-09"}, [("SURPRISE", "0.1")], at=AT),
        one("MACRO_CHANGE", {"series": "CUUR0000SA0", "period": "2026-09", "change_kind": "MOM_PCT"}, [("CHANGE", "0.2")], at=AT),
        one("FOMC_CURRENT_RANGE", {}, [("TARGET_RANGE", "3.75-4.00")], at=AT)]
    for name, rep in withholding.items():
        for c, cur in frames + [decision("2026-09-16", "RAISE", at=AT), latest_fomc("2026-07-29", at=AT)]:
            r = run(c, cur, rep, at=AT)
            assert r.state in (S.UNVERIFIED, S.CONFIRMED, S.OUTDATED, S.PARTIALLY_CONFIRMED), name
            assert all(f.outcome is not FactOutcome.CONTRADICTED for fr in r.frames for f in fr.facts), name
            if name in ("no-statement", "conflicting-copies"):
                assert r.state is S.UNVERIFIED or r.frames[0].frame_type.value.startswith("MACRO"), name
            if r.frames and r.frames[0].frame_type.value in ("FOMC_CURRENT_RANGE", "MACRO_CONSENSUS", "MACRO_CHANGE") or \
                    any(k in r.frames[0].frame_key for k in (":CURRENT", ":ORIGINAL")):
                assert r.state is S.UNVERIFIED, (name, r.frames[0].frame_key)
