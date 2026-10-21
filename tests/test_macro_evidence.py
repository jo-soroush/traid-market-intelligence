import copy
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, localcontext
import inspect
import itertools
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

import traid.macro.etf as etf_module
import traid.macro.evidence as evidence_module
from traid.domain.models import SourceProvenance
from traid.macro import (
    BLS_SERIES, PROVIDERS, US_SPOT_BTC_ETFS, Applicability, AssetEtfMapping, EtfEvidenceReport, EtfFund, EtfMetric,
    EtfObservation, EtfProvider, Freshness, MacroEvidenceReport, MacroEventType, ProviderState, ScheduledRelease,
    SupportState, ValueBasis, Vintage, build_etf_evidence, build_macro_evidence, verify_mapping_identity,
)
from traid.macro.bls import parse_bls_response
from traid.macro.fed import FeedItem, STATEMENT_TITLE, parse_fomc_calendar, parse_fomc_statement
from traid.macro.models import FomcStatement

D = Decimal
UTC = timezone.utc
F = Path(__file__).parent / "fixtures" / "macro"
BLS_REAL = json.loads((F / "bls_v2_timeseries.json").read_text())
SERIES = tuple(sorted(BLS_SERIES))
NY = "America/New_York"
EVIDENCE = "Release time as listed on the BLS schedule page; zone recorded by the curator for this test"
S = datetime(2026, 10, 15, 12, 30, tzinfo=UTC)    # 08:30 EDT
N = datetime(2026, 11, 10, 13, 30, tzinfo=UTC)    # 08:30 EST (after the DST change)


def sched(period, day, hh=8, mm=30, event="CPI", tz=NY, retrieved=datetime(2026, 10, 1, tzinfo=UTC), **kw):
    return ScheduledRelease(event_type=event, reference_period=period, release_date=day,
                            release_time=None if hh is None else time(hh, mm), timezone=tz,
                            timezone_evidence=None if tz is None else EVIDENCE,
                            source_url="https://www.bls.gov/schedule/news_release/cpi.htm", retrieved_at=retrieved, **kw)


CPI_SCHEDULE = (sched("2026-09", date(2026, 10, 15)), sched("2026-10", date(2026, 11, 10)))


def captures(received, payload=BLS_REAL, series=SERIES):
    return parse_bls_response(payload, series, received)


def with_value(period, value, payload=BLS_REAL, sid="CUUR0000SA0"):
    changed = copy.deepcopy(payload)
    for s in changed["Results"]["series"]:
        if s["seriesID"] == sid:
            for row in s["data"]:
                if f"{row['year']}-{row['period'][1:]}" == period:
                    row["value"] = value
    return changed


def without(period, payload=BLS_REAL):
    changed = copy.deepcopy(payload)
    for s in changed["Results"]["series"]:
        s["data"] = [r for r in s["data"] if f"{r['year']}-{r['period'][1:]}" != period]
        if s["data"]:
            s["data"][0]["latest"] = "true"
    return changed


def build(at=datetime(2026, 10, 21, tzinfo=UTC), schedules=CPI_SCHEDULE, caps=(), statements=(), calendars=()):
    return build_macro_evidence(evaluation_time=at, schedules=tuple(schedules), bls_captures=tuple(caps),
                                fomc_statements=tuple(statements), fomc_calendars=tuple(calendars))


def series(report, sid="CUUR0000SA0"):
    return next(s for s in report.series if s.series_id == sid)


# ============================================================== schedule / timezones
def test_new_york_release_times_convert_across_the_dst_change():
    assert CPI_SCHEDULE[0].scheduled_at() == S and CPI_SCHEDULE[1].scheduled_at() == N
    assert sched("2026-02", date(2026, 3, 9)).scheduled_at() == datetime(2026, 3, 9, 12, 30, tzinfo=UTC)
    assert sched("2026-01", date(2026, 3, 6)).scheduled_at() == datetime(2026, 3, 6, 13, 30, tzinfo=UTC)


def test_nonexistent_and_ambiguous_local_times_are_named():
    with pytest.raises(ValidationError, match="does not exist"):
        sched("2026-02", date(2026, 3, 8), hh=2, mm=30)       # spring forward gap
    with pytest.raises(ValidationError, match="ambiguous"):
        sched("2026-10", date(2026, 11, 1), hh=1, mm=30)      # fall back repeat


@pytest.mark.parametrize("kw", [
    dict(period="2026-02", day=date(2026, 3, 8), hh=2, mm=30),            # does not exist (spring forward)
    dict(period="2026-10", day=date(2026, 11, 1), hh=1, mm=30),           # ambiguous (fall back)
    dict(period="2026-09", day=date(2026, 10, 15), tz="Eastern/Nowhere"),
    dict(period="2026-13", day=date(2026, 10, 15)),
])
def test_ambiguous_nonexistent_or_invalid_schedule_times_are_rejected(kw):
    with pytest.raises(ValidationError):
        sched(**kw)


def test_a_zone_is_never_assumed():
    with pytest.raises(ValidationError):   # a zone needs its evidence
        ScheduledRelease(event_type="CPI", reference_period="2026-09", release_date=date(2026, 10, 15),
                         release_time=time(8, 30), timezone=NY, source_url="u", retrieved_at=datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(ValidationError):   # an aware wall-clock time is ambiguous input
        sched("2026-09", date(2026, 10, 15)).model_copy(update={"release_time": time(8, 30, tzinfo=UTC)}).model_validate(
            dict(sched("2026-09", date(2026, 10, 15)).model_dump(), release_time=time(8, 30, tzinfo=UTC)))
    no_zone = sched("2026-09", date(2026, 10, 15), tz=None)
    assert no_zone.scheduled_at() is None
    r = build(schedules=(no_zone,), caps=captures(S + timedelta(minutes=5)))
    assert series(r).freshness is Freshness.SCHEDULE_UNKNOWN and series(r).release_value.value is None


# ======================================================= release window and revisions
def test_capture_inside_the_release_window_is_the_release_value_with_previous():
    s = series(build(caps=captures(S + timedelta(minutes=3))))
    assert (s.freshness, s.reference_period, s.scheduled_at, s.next_scheduled_at) == (Freshness.CURRENT, "2026-09", S, N)
    assert s.release_value.value == D("336.940") and s.previous_at_release.value == D("334.980")
    assert s.known_vintage is Vintage.RELEASE_WINDOW and s.publication_time is None
    assert s.consensus.value is None and s.consensus.reason == "NO_APPROVED_CONSENSUS_SOURCE"
    assert s.unit == "index, 1982-84=100" and s.seasonal_adjustment == "NSA"


def test_historical_backfill_is_unusable_before_its_receipt_and_schedule_gaps_unbound_the_window():
    backfill = captures(datetime(2026, 10, 21, 9, tzinfo=UTC))        # current revised values, fetched today
    then = build(at=S + timedelta(hours=2), caps=backfill)              # evaluating the release day itself
    assert series(then).known_value.value is None and then.excluded_after_evaluation.bls_captures == 4
    gap = (CPI_SCHEDULE[0], sched("2026-11", date(2026, 12, 10)))      # the 2026-10 release is not listed
    s = series(build(schedules=gap, caps=captures(S + timedelta(minutes=3))))
    assert s.next_scheduled_at is None and s.known_vintage is Vintage.UNKNOWN_WINDOW
    assert s.release_value.value is None and s.release_value.reason == "NO_CAPTURE_IN_RELEASE_WINDOW"
    assert "NEXT_PERIOD_RELEASE_NOT_SCHEDULED_WINDOW_UNBOUNDED" in s.reasons
    assert s.known_value.value == D("336.940")    # still what TraID knew, just not proven as the release value


def test_revisions_are_kept_in_receipt_order_and_never_overwritten():
    first = captures(S + timedelta(minutes=5))
    revised = captures(S + timedelta(days=3), payload=with_value("2026-09", "337.010"))
    s = series(build(caps=first + revised))
    assert [r.value for r in s.revisions] == [D("336.940"), D("337.010")]
    assert s.release_value.value == D("336.940") and s.known_value.value == D("337.010")
    assert "REVISED_ACROSS_CAPTURES:1" in s.reasons


def test_a_capture_holding_a_period_before_its_release_contradicts_the_schedule():
    early = captures(S - timedelta(minutes=1))            # already holds 2026-09 before 08:30 EDT
    r = build(caps=early)
    assert r.inconsistent_bls_captures == tuple(sorted(f"{sid}@{(S - timedelta(minutes=1)).isoformat()}"
                                                       for sid in ("CUSR0000SA0", "CUUR0000SA0")))
    assert series(r).known_value.value is None and series(r).freshness is Freshness.AWAITING_CAPTURE


def test_published_unavailable_values_stay_unavailable_never_zero():
    known = datetime(2025, 11, 1, tzinfo=UTC)
    sch = (sched("2025-10", date(2025, 11, 13), retrieved=known), sched("2025-11", date(2025, 12, 18), retrieved=known))
    s = series(build(at=datetime(2025, 11, 20, tzinfo=UTC), schedules=sch,
                     caps=captures(datetime(2025, 11, 13, 14, tzinfo=UTC), payload=_until("2025-10"))))
    assert s.known_value.value is None and "lapse in appropriations" in s.known_value.reason
    assert s.release_value.value is None and s.release_value.reason.startswith("PUBLISHED_UNAVAILABLE:")


def _until(period):
    changed = copy.deepcopy(BLS_REAL)
    for s in changed["Results"]["series"]:
        s["data"] = [r for r in s["data"] if f"{r['year']}-{r['period'][1:]}" <= period]
        for r in s["data"]:
            r.pop("latest", None)
    return changed


def test_due_but_uncaptured_release_and_no_release_due():
    before = captures(S - timedelta(days=2), payload=without("2026-09"))
    s = series(build(caps=before))
    assert s.freshness is Freshness.AWAITING_CAPTURE and "LATEST_DUE_RELEASE_NOT_CAPTURED" in s.reasons
    assert s.known_value.value is None
    early = series(build(at=datetime(2026, 10, 1, 12, tzinfo=UTC), caps=()))
    assert early.freshness is Freshness.NO_RELEASE_DUE and early.next_scheduled_at == S


def test_observations_after_evaluation_are_counted_never_read():
    base = build(caps=captures(S + timedelta(minutes=3)))
    later = build(caps=captures(S + timedelta(minutes=3)) + captures(datetime(2026, 10, 22, tzinfo=UTC),
                                                                       payload=with_value("2026-09", "999")),
                  schedules=CPI_SCHEDULE + (sched("2026-11", date(2026, 12, 10), retrieved=datetime(2026, 10, 22, tzinfo=UTC)),))
    assert later.excluded_after_evaluation.bls_captures == 4 and later.excluded_after_evaluation.schedules == 1
    a, b = base.model_dump(mode="json"), later.model_dump(mode="json")
    for d in (a, b):
        d.pop("excluded_after_evaluation")
    assert a == b


def test_conflicting_schedule_entries_are_not_used():
    conflict = CPI_SCHEDULE + (sched("2026-09", date(2026, 10, 16)),)
    s = series(build(schedules=conflict, caps=captures(S + timedelta(minutes=3))))
    assert any(r.startswith("CONFLICTING_SCHEDULE_ENTRIES:2026-09") for r in s.reasons)
    assert s.reference_period != "2026-09"


def test_unsupported_bea_events_and_source_capabilities():
    r = build()
    events = {e.event_type: e for e in r.events}
    for e in (MacroEventType.PCE, MacroEventType.GDP_ADVANCE):
        assert events[e].state is SupportState.UNAVAILABLE and events[e].reasons == ("BEA_API_REQUIRES_REGISTERED_USERID_NOT_CONFIGURED",)
    assert events[MacroEventType.CPI].series_ids == ("CUSR0000SA0", "CUUR0000SA0")
    assert events[MacroEventType.EMPLOYMENT_SITUATION].series_ids == ("CES0000000001", "LNS14000000")
    assert {s.source.value: s.state.value for s in r.sources}["FRED_ALFRED"] == "UNAVAILABLE"


def test_preliminary_flags_and_employment_units():
    sch = (sched("2026-09", date(2026, 10, 2), event="EMPLOYMENT_SITUATION"),
           sched("2026-10", date(2026, 11, 6), event="EMPLOYMENT_SITUATION"))
    r = build(schedules=sch, caps=captures(datetime(2026, 10, 2, 12, 40, tzinfo=UTC)))
    nfp, rate = series(r, "CES0000000001"), series(r, "LNS14000000")
    assert nfp.preliminary is True and nfp.unit == "thousands of persons" and nfp.release_value.value == D(159044)
    assert rate.unit == "percent" and rate.release_value.value == D("4.2") and rate.previous_at_release.value == D("4.1")


def test_macro_evidence_is_deterministic_across_orders_and_contexts():
    caps = list(captures(S + timedelta(minutes=5)) + captures(S + timedelta(days=2), payload=with_value("2026-09", "337.0")))
    schedules = list(CPI_SCHEDULE)
    baseline = build(caps=caps, schedules=schedules).model_dump_json()
    for perm in itertools.islice(itertools.permutations(caps), 0, 40, 7):
        with localcontext() as ctx:
            ctx.prec, ctx.rounding = 2, ROUND_DOWN
            assert build(caps=perm, schedules=list(reversed(schedules))).model_dump_json() == baseline
    assert MacroEvidenceReport.model_validate_json(baseline).model_dump_json() == baseline


# ============================================================================ FOMC
def statement(stamp, hour, received=None):
    y, m, d = int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])
    it = FeedItem(title=STATEMENT_TITLE, url=f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{stamp}a.htm",
                  published_at=datetime(y, m, d, hour, tzinfo=UTC))
    return parse_fomc_statement((F / f"fed_statement_{stamp}a.html").read_text(), item=it,
                                received=received or it.published_at + timedelta(minutes=1))


CAL = parse_fomc_calendar((F / "fed_fomc_calendar.html").read_text(), received=datetime(2025, 1, 2, tzinfo=UTC))
REAL = [statement("20251210", 19), statement("20260128", 19), statement("20260729", 18), statement("20260916", 18)]


def test_fomc_current_range_and_consistency_with_previous_statement():
    fomc = build(statements=REAL, calendars=(CAL,)).fomc
    assert fomc.statement.statement_date == date(2026, 9, 16) and fomc.statement.target_upper_percent == 4
    assert fomc.previous_statement.statement_date == date(2026, 7, 29)
    assert fomc.consistency == "CONSISTENT" and fomc.in_calendar == "SCHEDULED_MEETING"
    assert fomc.next_meeting.end_date == date(2026, 10, 28) and fomc.freshness is Freshness.CURRENT
    jan = build(at=datetime(2026, 2, 1, tzinfo=UTC), statements=REAL, calendars=(CAL,)).fomc
    assert jan.statement.statement_date == date(2026, 1, 28) and jan.consistency == "CONSISTENT"   # Dec cut -> Jan hold


def test_statements_are_unknown_before_publication_and_receipt():
    just_before = build(at=datetime(2026, 9, 16, 17, 59, tzinfo=UTC), statements=REAL, calendars=(CAL,)).fomc
    assert just_before.statement.statement_date == date(2026, 7, 29)
    late_receipt = [*REAL[:3], statement("20260916", 18, received=datetime(2026, 9, 17, tzinfo=UTC))]
    r = build(at=datetime(2026, 9, 16, 20, tzinfo=UTC), statements=late_receipt, calendars=(CAL,))
    assert r.fomc.statement.statement_date == date(2026, 7, 29) and r.excluded_after_evaluation.fomc_statements == 1


def test_contradictory_decision_and_missing_statements():
    bad = REAL[3].model_copy(update={"target_upper_percent": D("4.25"), "target_lower_percent": D("4")})
    assert build(statements=[*REAL[:3], bad], calendars=(CAL,)).fomc.consistency == "CONTRADICTORY"
    missed = build(at=datetime(2026, 10, 30, tzinfo=UTC), statements=REAL, calendars=(CAL,)).fomc
    assert missed.freshness is Freshness.AWAITING_CAPTURE and "STATEMENT_FOR_PAST_MEETING_NOT_CAPTURED" in missed.reasons
    none = build(statements=(), calendars=(CAL,)).fomc
    assert none.statement is None and none.consistency == "NO_STATEMENT"
    nocal = build(statements=REAL).fomc
    assert nocal.in_calendar == "CALENDAR_UNAVAILABLE" and "NO_FOMC_CALENDAR_KNOWN" in nocal.reasons


def test_conflicting_copies_of_one_statement_fail_closed():
    copy_ = REAL[3].model_copy(update={"target_upper_percent": D("4.5"),
                                       "provenance": REAL[3].provenance.model_copy(update={"received_timestamp": datetime(2026, 9, 18, tzinfo=UTC)})})
    fomc = build(statements=[*REAL, copy_], calendars=(CAL,)).fomc
    assert fomc.statement is None and "CONFLICTING_STATEMENT_COPIES" in fomc.reasons


# ============================================================================= ETF
SEC = json.loads((F / "sec_company_tickers_exchange_subset.json").read_text())
APPROVED = EtfProvider(provider_id="test_provider", name="Test provider", state=ProviderState.APPROVED,
                       reason="TEST_ONLY", documentation_url="https://example.invalid", approval_reference="test-approval-1")
T_ETF = datetime(2026, 10, 21, 22, tzinfo=UTC)


def obs(ticker, metric=EtfMetric.NET_FLOW_USD, raw="1000000", basis=ValueBasis.REPORTED, day=date(2026, 10, 20),
        provider="test_provider", received=datetime(2026, 10, 21, 12, tzinfo=UTC)):
    unit = etf_module.UNITS[metric]
    return EtfObservation(provider_id=provider, ticker=ticker, metric=metric, trade_date=day, raw_value=raw,
                          value=None if raw is None else D(raw), unit=unit, basis=basis, methodology="test fixture",
                          as_of=None, published_at=None,
                          provenance=SourceProvenance(source=provider, source_type="test", received_timestamp=received))


def etf(observations=(), providers=PROVIDERS + (APPROVED,), at=T_ETF, **kw):
    return build_etf_evidence(evaluation_time=at, providers=providers, observations=tuple(observations), **kw)


def metric(report, m):
    return next(x for x in report.metrics if x.metric is m)


def test_fund_identities_match_sec_edgar_and_mismatches_are_found():
    assert verify_mapping_identity(US_SPOT_BTC_ETFS, SEC) == ()
    wrong = US_SPOT_BTC_ETFS.model_copy(update={"funds": tuple(
        f.model_copy(update={"cik": 1}) if f.ticker == "IBIT" else f for f in US_SPOT_BTC_ETFS.funds)})
    assert verify_mapping_identity(wrong, SEC) == ("IBIT:IDENTITY_MISMATCH",)
    assert verify_mapping_identity(US_SPOT_BTC_ETFS, {"fields": ["x"], "data": []}) == ("SEC_TICKER_FILE_SHAPE_UNEXPECTED",)
    assert [f.ticker for f in US_SPOT_BTC_ETFS.applicable()] == ["ARKB", "BITB", "BRRR", "BTC", "BTCO", "BTCW", "EZBC",
                                                                  "FBTC", "GBTC", "HODL", "IBIT"]


def test_default_providers_yield_explicit_unavailability_and_no_numbers():
    flows = [obs(f.ticker, provider="sosovalue") for f in US_SPOT_BTC_ETFS.applicable()]
    r = build_etf_evidence(evaluation_time=T_ETF, observations=tuple(flows))
    assert r.provider_state == "NO_APPROVED_PROVIDER" and r.excluded_unapproved == len(flows)
    for m in r.metrics:
        assert m.coverage == "NONE" and m.aggregate.value is None and m.aggregate.reason == "NO_APPROVED_ETF_PROVIDER"
        assert all(f.value.value is None and f.status.value == "NO_APPROVED_PROVIDER" for f in m.funds)
    assert {p.provider_id: p.state for p in r.providers} == {"farside": ProviderState.NOT_SUITABLE,
                                                             "sosovalue": ProviderState.UNVERIFIED,
                                                             "glassnode": ProviderState.UNVERIFIED,
                                                             "ishares_website": ProviderState.NOT_SUITABLE}
    data = r.model_dump()
    data["metrics"][0]["aggregate"] = {"value": D(1), "unit": "USD", "reason": None}
    with pytest.raises(ValidationError):
        EtfEvidenceReport.model_validate(data)


def test_complete_coverage_aggregates_and_partial_coverage_does_not():
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    full = etf([obs(t, raw=str(10 * (i + 1))) for i, t in enumerate(funds)])
    m = metric(full, EtfMetric.NET_FLOW_USD)
    assert m.coverage == "COMPLETE" and m.aggregate.value == D(sum(10 * (i + 1) for i in range(len(funds))))
    partial = metric(etf([obs(t) for t in funds[:-1]]), EtfMetric.NET_FLOW_USD)
    assert partial.coverage == "PARTIAL" and partial.aggregate.value is None
    assert partial.reasons == (f"INCOMPLETE_FUND_COVERAGE:{funds[-1]}",)
    assert "MSBT" in full.unverified_applicability and all(f.ticker != "MSBT" for f in m.funds)


def test_provider_null_mixed_basis_and_conflicts_block_aggregates():
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    nulled = metric(etf([obs(t, raw=None if t == "IBIT" else "5") for t in funds]), EtfMetric.NET_FLOW_USD)
    ibit = next(f for f in nulled.funds if f.ticker == "IBIT")
    assert ibit.status.value == "PROVIDER_NULL" and ibit.value.value is None and nulled.aggregate.value is None
    mixed = metric(etf([obs(t, basis=ValueBasis.PROVIDER_ESTIMATE if t == "GBTC" else ValueBasis.REPORTED) for t in funds]),
                   EtfMetric.NET_FLOW_USD)
    assert mixed.aggregate.value is None and "MIXED_VALUE_BASIS" in mixed.reasons
    conflict = metric(etf([obs(t) for t in funds] + [obs("IBIT", raw="7")]), EtfMetric.NET_FLOW_USD)
    assert next(f for f in conflict.funds if f.ticker == "IBIT").status.value == "CONFLICT"


def test_volume_and_assets_never_become_flows():
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    r = etf([obs(t, metric=EtfMetric.TRADING_VOLUME_SHARES, raw="100") for t in funds] +
            [obs(t, metric=EtfMetric.NET_ASSETS_USD, raw="1000") for t in funds])
    assert metric(r, EtfMetric.TRADING_VOLUME_SHARES).aggregate.value == D(100 * len(funds))
    flow = metric(r, EtfMetric.NET_FLOW_USD)
    assert flow.coverage == "NONE" and flow.aggregate.value is None and all(f.value.value is None for f in flow.funds)
    with pytest.raises(ValidationError):
        obs("IBIT", basis=ValueBasis.TRAID_DERIVED)
    with pytest.raises(ValidationError):
        obs("IBIT").model_copy(update={"unit": "shares"}).model_validate(dict(obs("IBIT").model_dump(), unit="shares"))


def test_etf_point_in_time_and_revisions():
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    first = [obs(t, raw="10") for t in funds]
    revised = obs("IBIT", raw="12", received=datetime(2026, 10, 21, 20, tzinfo=UTC))
    future = obs("FBTC", raw="999", received=datetime(2026, 10, 22, tzinfo=UTC))
    r = etf(first + [revised, future])
    m = metric(r, EtfMetric.NET_FLOW_USD)
    assert next(f for f in m.funds if f.ticker == "IBIT").value.value == D(12)     # latest known receipt
    assert next(f for f in m.funds if f.ticker == "FBTC").value.value == D(10)
    assert r.excluded_after_evaluation == 1
    early = metric(etf(first + [revised], at=datetime(2026, 10, 21, 13, tzinfo=UTC)), EtfMetric.NET_FLOW_USD)
    assert next(f for f in early.funds if f.ticker == "IBIT").value.value == D(10)


def test_invalid_providers_mappings_and_tickers_are_rejected():
    with pytest.raises(ValidationError):
        EtfProvider(provider_id="x", name="x", state=ProviderState.APPROVED, reason="r", documentation_url="u")
    with pytest.raises(ValueError):
        etf(providers=(APPROVED, APPROVED.model_copy(update={"provider_id": "other"})))
    with pytest.raises(ValueError, match="ETF_TICKER_NOT_IN_MAPPING"):
        etf([obs("SPY")])
    with pytest.raises(ValidationError):
        AssetEtfMapping(asset="BTC", jurisdiction="US", mapping_version="v", identity_source="s",
                        identity_retrieved_on=date(2026, 1, 1), funds=tuple(reversed(US_SPOT_BTC_ETFS.funds)))
    with pytest.raises(ValidationError):
        EtfFund(ticker="ibit", registrant_name="x", cik=1, exchange="x", applicability=Applicability.UNVERIFIED,
                applicability_evidence="x")


def test_etf_evidence_is_deterministic():
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    observations = [obs(t, raw="10.0" if i % 2 else "10") for i, t in enumerate(funds)] + [obs("IBIT", raw="10.00")]
    observations[-1] = obs("IBIT", raw="10.000")
    baseline = etf(observations).model_dump_json()
    for perm in itertools.islice(itertools.permutations(observations), 0, 30, 3):
        with localcontext() as ctx:
            ctx.prec = 2
            assert etf(list(perm)).model_dump_json() == baseline


# ===================================================================== safety
def test_no_output_can_authorize_trades_or_carry_ai_or_surprise_semantics():
    banned = ("trade", "order", "signal", "authoriz", "recommend", "surprise", "score", "predict", "direction", "ai_")
    seen = set()

    def walk(cls):
        if cls in seen or not (isinstance(cls, type) and issubclass(cls, BaseModel)):
            return
        seen.add(cls)
        for name, field in cls.model_fields.items():
            if name == "trade_date":    # the ETF market date, not an instruction
                continue
            assert not any(b in name.lower() for b in banned), (cls.__name__, name)
            for arg in getattr(field.annotation, "__args__", ()) + (field.annotation,):
                walk(arg)
    walk(MacroEvidenceReport)
    walk(EtfEvidenceReport)
    assert "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION" in MacroEvidenceReport.model_fields["limitations"].default
    assert "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION" in EtfEvidenceReport.model_fields["limitations"].default
    for mod in (evidence_module, etf_module):
        source = inspect.getsource(mod)
        for banned_import in ("urllib", "requests", "openai", "anthropic", "bedrock", "datetime.now", "import random"):
            assert banned_import not in source


def test_conflicting_captures_at_one_receipt_fail_closed():
    at = S + timedelta(minutes=5)
    s = series(build(caps=captures(at) + captures(at, payload=with_value("2026-09", "340.000"))))
    assert s.known_value.value is None and s.known_value.reason == "CONFLICTING_CAPTURES_AT_ONE_RECEIPT_TIME"
    assert s.release_value.value is None and "CONFLICTING_RELEASE_WINDOW_CAPTURES" in s.reasons
    same = series(build(caps=captures(at) + captures(at, payload=with_value("2026-09", "336.9400"))))
    assert same.known_value.value == D("336.94") and same.release_value.value == D("336.94")   # one value, two spellings


def test_future_dated_etf_observations_are_excluded():
    funds = [f.ticker for f in US_SPOT_BTC_ETFS.applicable()]
    base = [obs(t) for t in funds]
    future_day = obs("IBIT", raw="5", day=date(2026, 10, 22))
    future_asof = obs("IBIT", raw="5").model_copy(update={"as_of": datetime(2026, 10, 22, tzinfo=UTC)})
    r = etf(base + [future_day, future_asof])
    assert r.excluded_after_evaluation == 2
    assert next(f for f in metric(r, EtfMetric.NET_FLOW_USD).funds if f.ticker == "IBIT").value.value == D(1000000)


def test_release_window_boundaries_are_exact():
    at_release = series(build(caps=captures(S)))
    assert at_release.known_vintage is Vintage.RELEASE_WINDOW and at_release.release_value.value == D("336.940")
    just_before = build(caps=captures(S - timedelta(microseconds=1)))
    assert len(just_before.inconsistent_bls_captures) == 2
    # The next period's release is listed twice with different times, so it is not used as a due release;
    # the window still closes at its earliest listed time, and a capture after that is not the release value.
    conflict = CPI_SCHEDULE + (sched("2026-10", date(2026, 11, 12)),)
    late = series(build(at=N + timedelta(days=3), schedules=conflict, caps=captures(N, payload=without("2026-10"))))
    assert late.reference_period == "2026-09" and late.known_vintage is Vintage.UNKNOWN_WINDOW
    assert late.release_value.value is None
    inside = series(build(at=N + timedelta(days=3), schedules=conflict,
                          caps=captures(N - timedelta(microseconds=1), payload=without("2026-10"))))
    assert inside.known_vintage is Vintage.RELEASE_WINDOW


def test_a_statement_is_unknowable_before_publication_even_if_construction_was_bypassed():
    forged = FomcStatement.model_construct(**{**REAL[3].__dict__, "provenance": REAL[3].provenance.model_copy(
        update={"received_timestamp": datetime(2026, 9, 16, 17, tzinfo=UTC)})})
    r = build(at=datetime(2026, 9, 16, 17, 30, tzinfo=UTC), statements=[*REAL[:3], forged], calendars=(CAL,))
    assert r.excluded_after_evaluation.fomc_statements == 1 and r.fomc.statement.statement_date == date(2026, 7, 29)
