from datetime import date, datetime, timezone
from decimal import ROUND_DOWN, Decimal, localcontext
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

import traid.macro.bls as bls
import traid.macro.fed as fed
from traid.exchange.errors import AdapterError, AdapterErrorCode, AdapterRateLimitError, ProviderDataError
from traid.macro import BLS_SERIES, PolicyAction
from traid.macro.bls import BlsClient, parse_bls_response
from traid.macro.fed import (
    FederalReserveClient, FeedItem, parse_fomc_calendar, parse_fomc_statement, parse_monetary_feed, statement_items,
)

D = Decimal
UTC = timezone.utc
F = Path(__file__).parent / "fixtures" / "macro"
BLS_REAL = json.loads((F / "bls_v2_timeseries.json").read_text())
SERIES = tuple(sorted(BLS_SERIES))
RX = datetime(2026, 10, 21, 12, tzinfo=UTC)


def fixture(name):
    return (F / name).read_text()


# ======================================================================== BLS
def test_real_bls_response_parses_with_published_semantics():
    caps = {c.series_id: c for c in parse_bls_response(BLS_REAL, SERIES, RX)}
    assert set(caps) == set(SERIES)
    cpi = caps["CUUR0000SA0"]
    latest = cpi.value("2026-09")
    assert (latest.value, latest.raw_value, latest.latest, latest.preliminary) == (D("336.940"), "336.940", True, False)
    oct25 = cpi.value("2025-10")       # not published: 2025 lapse in appropriations
    assert oct25.value is None and oct25.raw_value == "-" and "lapse in appropriations" in oct25.unavailable_reason
    nfp = caps["CES0000000001"].value("2026-09")
    assert nfp.preliminary and nfp.value == D(159044)
    jan = caps["LNS14000000"].value("2026-01")
    assert [f.code for f in jan.footnotes] == ["12"] and "population controls" in jan.footnotes[0].text
    assert cpi.provenance.source == "bls" and cpi.provenance.source_timestamp is None
    assert cpi.provenance.received_timestamp == RX


class Transport:
    def __init__(self, payload):
        self.payload, self.bodies = payload, []

    def __call__(self, body):
        self.bodies.append(body)
        return self.payload


def test_client_sends_documented_body_and_never_stores_the_key():
    t = Transport(BLS_REAL)
    BlsClient(transport=t, clock=lambda: RX).series(SERIES, 2025, 2026)
    assert t.bodies[0] == {"seriesid": list(SERIES), "startyear": "2025", "endyear": "2026"}
    keyed = Transport(BLS_REAL)
    caps = BlsClient(registration_key="SECRET-KEY", transport=keyed, clock=lambda: RX).series(SERIES, 2025, 2026)
    assert keyed.bodies[0]["registrationkey"] == "SECRET-KEY"
    assert all("SECRET-KEY" not in c.model_dump_json() for c in caps)


@pytest.mark.parametrize("kw, args", [
    ({}, (tuple(SERIES) * 7, 2025, 2026)),                           # duplicates
    ({}, (("CUUR0000SA0", "XXXX0000000"), 2025, 2026)),               # not a verified series
    ({}, (SERIES, 2014, 2026)),                                       # 13 years > 10 without a key
    ({"registration_key": "k"}, (SERIES, 2000, 2026)),                # 27 years > 20 with a key
    ({}, (SERIES, 2026, 2025)),
    ({}, ((), 2025, 2026)),
])
def test_requests_outside_documented_limits_are_refused(kw, args):
    with pytest.raises(ValueError):
        BlsClient(transport=Transport(BLS_REAL), clock=lambda: RX, **kw).series(*args)


def _series(sid="CUUR0000SA0", **row):
    base = {"year": "2026", "period": "M09", "periodName": "September", "value": "336.940", "footnotes": [{}]}
    base.update(row)
    return {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": [{"seriesID": sid, "data": [base]}]}}


@pytest.mark.parametrize("payload", [
    _series(period="M13"),                                   # annual average is not a release value
    _series(period="Q03"),
    _series(value="abc"),
    _series(value="NaN"),
    _series(value="-", footnotes=[{}]),                     # unavailable without its reason
    _series(latest="yes"),
    _series(footnotes="none"),
    _series(year="26"),
    {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": [_series()["Results"]["series"][0]] * 2}},
    {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": []}},       # requested series missing
    _series(sid="CUSR0000SA0"),                              # not the requested series
    {"status": "REQUEST_SUCCEEDED"},
    [],
])
def test_changed_or_malformed_bls_payloads_fail_closed(payload):
    with pytest.raises(ProviderDataError):
        parse_bls_response(payload, ("CUUR0000SA0",), RX)


def test_real_unknown_series_response_fails_closed():
    # BLS answers REQUEST_SUCCEEDED with an empty series and a message for an unknown id.
    unknown = json.loads((F / "bls_v2_unknown_series.json").read_text())
    assert unknown["status"] == "REQUEST_SUCCEEDED" and unknown["Results"]["series"][0]["data"] == []
    with pytest.raises(ProviderDataError):
        parse_bls_response(unknown, ("XXXX0000000",), RX)


def test_unprocessed_requests_and_thresholds():
    with pytest.raises(AdapterRateLimitError):
        parse_bls_response({"status": "REQUEST_NOT_PROCESSED", "message": ["daily threshold exceeded"],
                            "Results": {}}, ("CUUR0000SA0",), RX)
    with pytest.raises(AdapterError) as error:
        parse_bls_response({"status": "REQUEST_NOT_PROCESSED", "message": ["unavailable"]}, ("CUUR0000SA0",), RX)
    assert error.value.code is AdapterErrorCode.UNAVAILABLE


def test_bls_http_errors_and_timeouts(monkeypatch):
    client = BlsClient(clock=lambda: RX)
    for exc, kind in ((HTTPError("u", 429, "x", {}, io.BytesIO()), AdapterRateLimitError),
                      (HTTPError("u", 503, "x", {}, io.BytesIO()), AdapterError),
                      (URLError("timed out"), AdapterError), (TimeoutError(), AdapterError)):
        def boom(*a, exc=exc, **k):
            raise exc
        monkeypatch.setattr(bls, "urlopen", boom)
        with pytest.raises(kind):
            client.series(("CUUR0000SA0",), 2026, 2026)


def test_naive_clock_is_rejected():
    with pytest.raises(ValueError):
        BlsClient(transport=Transport(BLS_REAL), clock=lambda: datetime(2026, 10, 21)).series(SERIES, 2025, 2026)


def test_bls_values_do_not_depend_on_ambient_decimal_context():
    baseline = [c.model_dump_json() for c in parse_bls_response(BLS_REAL, SERIES, RX)]
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 2, ROUND_DOWN
        assert [c.model_dump_json() for c in parse_bls_response(BLS_REAL, SERIES, RX)] == baseline


# ================================================================= Federal Reserve
FEED = fixture("fed_press_monetary.xml")


def item(stamp, hour_utc):
    y, m, d = int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])
    return FeedItem(title=fed.STATEMENT_TITLE, url=f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{stamp}a.htm",
                    published_at=datetime(y, m, d, hour_utc, tzinfo=UTC))


def statement(stamp, hour_utc, **kw):
    return parse_fomc_statement(fixture(f"fed_statement_{stamp}a.html"), item=kw.get("it") or item(stamp, hour_utc),
                                received=datetime(2026, 10, 21, tzinfo=UTC))


def test_real_feed_lists_statements_with_gmt_publication_times():
    items = parse_monetary_feed(FEED)
    assert len(items) == 15
    st = statement_items(items)
    assert [i.url[-13:-4] for i in st] == ["20260429a", "20260617a", "20260729a", "20260916a"]
    assert all(i.published_at.tzinfo == UTC and i.published_at.hour == 18 for i in st)   # 2:00 p.m. EDT


@pytest.mark.parametrize("stamp, hour, action, change, lower, upper, zone", [
    ("20260916", 18, PolicyAction.RAISE, D("0.25"), D("3.75"), D("4"), "EDT"),
    ("20260729", 18, PolicyAction.MAINTAIN, None, D("3.5"), D("3.75"), "EDT"),
    ("20260128", 19, PolicyAction.MAINTAIN, None, D("3.5"), D("3.75"), "EST"),        # standard time: 19:00 UTC
    ("20251210", 19, PolicyAction.LOWER, D("0.25"), D("3.5"), D("3.75"), "EST"),
])
def test_real_statements_parse_decision_and_dst_correct_publication_time(stamp, hour, action, change, lower, upper, zone):
    s = statement(stamp, hour)
    assert (s.action, s.change_percentage_points, s.target_lower_percent, s.target_upper_percent) == (action, change, lower, upper)
    assert s.published_at.hour == hour and s.release_time_text.endswith(zone)
    assert s.statement_date.strftime("%Y%m%d") == stamp and "target range for the federal funds rate" in s.decision_text


@pytest.mark.parametrize("stamp, hour", [("20260916", 19), ("20260128", 18)])   # feed time an hour off
def test_feed_and_page_release_times_must_agree(stamp, hour):
    with pytest.raises(ProviderDataError, match="disagree"):
        statement(stamp, hour)


def test_a_stated_zone_contradicting_new_york_dst_is_rejected():
    page = fixture("fed_statement_20260128a.html").replace("2:00 p.m. EST", "2:00 p.m. EDT")
    with pytest.raises(ProviderDataError, match="contradicts America/New_York"):
        parse_fomc_statement(page, item=item("20260128", 18), received=RX)


@pytest.mark.parametrize("edit", [
    lambda p: p.replace("decided to raise", "decided to raise and also decided to raise the target range for the federal "
                        "funds rate by 1/2 percentage point to 4 to 4-1/4 percent; decided to raise"),
    lambda p: p.replace("target range for the federal funds rate", "policy rate"),
    lambda p: p.replace("For release at", "Released"),
    lambda p: p.replace("September 16, 2026", "September 17, 2026"),
    lambda p: p.replace("by 1/4 percentage point", "by 1/3 percentage point"),
    lambda p: p.replace("decided to raise", "decided to maintain"),
    lambda p: p.replace("to 4 percent", "to 3-1/2 percent"),              # upper below lower
])
def test_changed_or_ambiguous_statement_pages_fail_closed(edit):
    page = edit(fixture("fed_statement_20260916a.html"))
    with pytest.raises(ProviderDataError):
        parse_fomc_statement(page, item=item("20260916", 18), received=RX)


def test_non_statement_items_and_receipt_before_publication_are_rejected():
    minutes = FeedItem(title="Minutes of the Federal Open Market Committee", url=item("20260916", 18).url,
                       published_at=datetime(2026, 9, 16, 18, tzinfo=UTC))
    with pytest.raises(ProviderDataError):
        parse_fomc_statement(fixture("fed_statement_20260916a.html"), item=minutes, received=RX)
    with pytest.raises(ProviderDataError):
        parse_fomc_statement(fixture("fed_statement_20260916a.html"), item=item("20260916", 18),
                             received=datetime(2026, 9, 16, 17, tzinfo=UTC))


def test_rate_fractions_are_exact_in_any_decimal_context():
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 1, ROUND_DOWN
        s = statement("20260916", 18)
    assert (s.target_lower_percent, s.target_upper_percent, s.change_percentage_points) == (D("3.75"), D(4), D("0.25"))
    assert fed._fraction("0") == 0 and fed._fraction("5-1/8") == D("5.125")


@pytest.mark.parametrize("doc", [
    '<!DOCTYPE rss [<!ENTITY x "y">]><rss><channel></channel></rss>',
    "<rss><channel><item><title>t</title></item></channel></rss>",
    "<rss><channel><item><title>t</title><link>l</link><pubDate>Wed, 16 Sep 2026 18:00:00</pubDate></item></channel></rss>",
    "<rss><channel><item><title>t</title><link>l</link><pubDate>yesterday</pubDate></item></channel></rss>",
    "<rss><channel>",
    "x" * (fed.MAX_DOCUMENT + 1),
])
def test_malformed_or_unsafe_feeds_are_rejected(doc):
    with pytest.raises(ProviderDataError):
        parse_monetary_feed(doc)


def test_real_calendar_parses_meetings_sep_and_notation_votes():
    cal = parse_fomc_calendar(fixture("fed_fomc_calendar.html"), received=RX)
    meetings = {(m.start_date, m.end_date): m for m in cal.meetings}
    assert len(cal.meetings) == 25
    assert meetings[(date(2026, 9, 15), date(2026, 9, 16))].projections
    assert meetings[(date(2025, 8, 22), date(2025, 8, 22))].notation_vote
    assert (date(2026, 10, 27), date(2026, 10, 28)) in meetings and (date(2027, 12, 7), date(2027, 12, 8)) in meetings


def _cal(month, days, year=2024):
    return (f'<h4>{year} FOMC Meetings</h4><div class="fomc-meeting__month"><strong>{month}</strong></div>'
            f'<div class="fomc-meeting__date">{days}</div>')


def test_cross_month_meetings_and_unknown_formats():
    cal = parse_fomc_calendar(_cal("Apr/May", "30-1"), received=RX)
    assert (cal.meetings[0].start_date, cal.meetings[0].end_date) == (date(2024, 4, 30), date(2024, 5, 1))
    for month, days in (("Apr/May", "30"), ("Smarch", "1-2"), ("June", "16-17 (postponed)"), ("June", "31-32"),
                        ("June", "17-16")):
        with pytest.raises(ProviderDataError):
            parse_fomc_calendar(_cal(month, days), received=RX)
    with pytest.raises(ProviderDataError):
        parse_fomc_calendar("<html>no meetings here</html>", received=RX)


def test_fed_client_fetches_only_verified_paths(monkeypatch):
    pages = {fed.FEED_URL: FEED, fed.CALENDAR_URL: fixture("fed_fomc_calendar.html"),
             item("20260916", 18).url: fixture("fed_statement_20260916a.html")}
    seen = []
    client = FederalReserveClient(transport=lambda url: seen.append(url) or pages[url],
                                  clock=lambda: datetime(2026, 10, 21, tzinfo=UTC))
    items = statement_items(client.feed())
    s = client.statement(items[-1])
    assert s.target_upper_percent == 4 and len(client.calendar().meetings) == 25
    with pytest.raises(AdapterError) as error:
        client._get("https://www.federalreserve.gov/newsevents/speech/other.htm")
    assert error.value.code is AdapterErrorCode.CONTRACT
    assert seen == [fed.FEED_URL, items[-1].url, fed.CALENDAR_URL]

    def raise_429(*a, **k):
        raise HTTPError("u", 429, "x", {}, io.BytesIO())
    monkeypatch.setattr(fed, "urlopen", raise_429)
    with pytest.raises(AdapterRateLimitError):
        FederalReserveClient().feed()
