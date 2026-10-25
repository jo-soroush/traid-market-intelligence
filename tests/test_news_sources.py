"""C13 source access (design §6.5): GovInfo allowlist, bounded retrieval and the Federal Register client.

All transports are fakes; no network is used (the autouse guard fails any connection attempt)."""
from datetime import date, datetime, timezone
from email.message import Message
import io
import json
from urllib.error import HTTPError

import pytest

from news_support import _no_network, body, entry, metadata  # noqa: F401  (autouse fixture)
import traid.news.sources as sources
from traid.news.models import GovInfoHtml, GovInfoModsRetrieval, GovInfoPdf
from traid.news.sources import (
    MAX_BYTES, FederalRegisterClient, GovInfoClient, HttpResponse, accept_response, govinfo_url,
    parse_fr_docket_page, parse_fr_document, parse_fr_public_inspection, validate_govinfo_url,
)

UTC = timezone.utc
D, N = date(2024, 1, 17), "2024-00743"
OFFICIAL = "https://www.govinfo.gov/metadata/granule/FR-2024-01-17/2024-00743/mods.xml"
CLOCK = datetime(2026, 10, 24, tzinfo=UTC)


def test_official_urls_are_the_canonical_constructions():
    meta = metadata(N)
    assert govinfo_url("MODS", D, N) == OFFICIAL == meta.mods_url
    assert govinfo_url("PDF", D, N) == meta.pdf_url
    for kind in ("PDF", "HTML", "MODS"):
        assert validate_govinfo_url(govinfo_url(kind, D, N), kind, D, N) == "OK"


NEGATIVE = {
    "http": ("http://www.govinfo.gov/metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_SCHEME_NOT_HTTPS"),
    "bare-host": ("https://govinfo.gov/metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_HOST_NOT_ALLOWED"),
    "lookalike-host": ("https://www.govinfo.gov.evil.example/metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_HOST_NOT_ALLOWED"),
    "userinfo": ("https://www.govinfo.gov@evil.example/metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_CHARACTERS_REJECTED"),
    "port": ("https://www.govinfo.gov:8443/metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_HOST_NOT_ALLOWED"),
    "uppercase-host": ("https://WWW.GOVINFO.GOV/metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_HOST_NOT_ALLOWED"),
    "query": (OFFICIAL + "?x=1", "URL_QUERY_OR_FRAGMENT_REJECTED"),
    "fragment": (OFFICIAL + "#a", "URL_QUERY_OR_FRAGMENT_REJECTED"),
    "traversal": ("https://www.govinfo.gov/metadata/granule/FR-2024-01-17/../../api/mods.xml", "URL_PATH_TRAVERSAL_REJECTED"),
    "encoded-traversal": ("https://www.govinfo.gov/metadata/granule/FR-2024-01-17/%2e%2e/2024-00743/mods.xml", "URL_CHARACTERS_REJECTED"),
    "double-slash": ("https://www.govinfo.gov/metadata/granule//FR-2024-01-17/2024-00743/mods.xml", "URL_PATH_TRAVERSAL_REJECTED"),
    "wrong-date": ("https://www.govinfo.gov/metadata/granule/FR-2024-01-18/2024-00743/mods.xml", "URL_PACKAGE_DATE_MISMATCH"),
    "invalid-date": ("https://www.govinfo.gov/metadata/granule/FR-2024-13-01/2024-00743/mods.xml", "URL_PACKAGE_DATE_INVALID"),
    "wrong-docno": ("https://www.govinfo.gov/metadata/granule/FR-2024-01-17/2024-00744/mods.xml", "URL_DOCUMENT_NUMBER_MISMATCH"),
    "malformed-docno": ("https://www.govinfo.gov/metadata/granule/FR-2024-01-17/2024-743/mods.xml", "URL_PATH_NOT_ALLOWED"),
    "wrong-file": ("https://www.govinfo.gov/metadata/granule/FR-2024-01-17/2024-00743/premis.xml", "URL_PATH_NOT_ALLOWED"),
    "package-mods": ("https://www.govinfo.gov/metadata/pkg/FR-2024-01-17/mods.xml", "URL_PATH_NOT_ALLOWED"),
    "api-path": ("https://www.govinfo.gov/api/packages/FR-2024-01-17/granules/2024-00743/summary", "URL_PATH_NOT_ALLOWED"),
    "trailing-slash": (OFFICIAL + "/", "URL_PATH_NOT_ALLOWED"),
    "backslash": ("https://www.govinfo.gov\\metadata/granule/FR-2024-01-17/2024-00743/mods.xml", "URL_CHARACTERS_REJECTED"),
    "kind-swap": ("https://www.govinfo.gov/content/pkg/FR-2024-01-17/pdf/2024-00743.pdf", "URL_PATH_NOT_ALLOWED"),
    "control-char": (OFFICIAL.replace("mods", "mo\x7fds"), "URL_CHARACTERS_REJECTED"),
    "non-ascii": (OFFICIAL.replace("granule", "gränule"), "URL_CHARACTERS_REJECTED"),
}


@pytest.mark.parametrize("case", sorted(NEGATIVE))
def test_url_rejections(case):
    url, why = NEGATIVE[case]
    assert validate_govinfo_url(url, "MODS", D, N) == why


def test_url_from_claim_text_or_documents_is_never_used():
    assert validate_govinfo_url(OFFICIAL, "MODS", D, N, origin="CLAIM_TEXT") == "URL_NOT_CONSTRUCTED_BY_TRAID"


XML = {"content-type": "text/xml;charset=UTF-8"}
RESPONSES = {
    "ok": (HttpResponse(200, XML, b"<mods/>"), "OK"),
    "redirect-to-error": (HttpResponse(302, {"location": "https://www.govinfo.gov/error"}),
                          "SOURCE_UNAVAILABLE:REDIRECT_NOT_FOLLOWED:https://www.govinfo.gov/error"),
    "redirect-offsite": (HttpResponse(301, {"location": "https://evil.example/mods.xml"}),
                         "SOURCE_UNAVAILABLE:REDIRECT_NOT_FOLLOWED:https://evil.example/mods.xml"),
    "oversized": (HttpResponse(200, XML, b"x" * (MAX_BYTES["MODS"] + 1)), "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"),
    "truncated": (HttpResponse(200, XML, None, truncated=True), "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"),
    "wrong-content-type": (HttpResponse(200, {"content-type": "text/html"}, b"<html/>"), "SOURCE_UNAVAILABLE:CONTENT_TYPE:text/html"),
    "missing-content-type": (HttpResponse(200, {}, b"<mods/>"), "SOURCE_UNAVAILABLE:CONTENT_TYPE:missing"),
    "timeout": (HttpResponse(0, timed_out=True), "SOURCE_UNAVAILABLE:TIMEOUT"),
    "http-500": (HttpResponse(500), "SOURCE_UNAVAILABLE:HTTP_500"),
    "http-429": (HttpResponse(429), "SOURCE_UNAVAILABLE:HTTP_429"),
    "http-404": (HttpResponse(404), "SOURCE_UNAVAILABLE:HTTP_404"),
    "connection": (HttpResponse(0, failure="CONNECTION_FAILED"), "SOURCE_UNAVAILABLE:CONNECTION_FAILED"),
    "empty": (HttpResponse(200, XML, None), "SOURCE_UNAVAILABLE:EMPTY"),
}


@pytest.mark.parametrize("case", sorted(RESPONSES))
def test_response_acceptance(case):
    response, why = RESPONSES[case]
    assert accept_response("MODS", response) == why


class Fake:
    """Records requested URLs and answers from a script (url -> response), counting calls."""
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, url, cap, timeout):
        self.calls.append((url, cap, timeout))
        answer = self.answers(url) if callable(self.answers) else self.answers[url]
        return answer


def govinfo_answers(url):
    kind = "GOVINFO_PDF" if url.endswith(".pdf") else "GOVINFO_HTML" if url.endswith(".htm") else "GOVINFO_MODS"
    ctype = {"GOVINFO_PDF": "application/pdf", "GOVINFO_HTML": "text/html; charset=utf-8", "GOVINFO_MODS": "text/xml;charset=UTF-8"}[kind]
    return HttpResponse(200, {"content-type": ctype}, body(N, kind))


def test_govinfo_client_builds_bound_records_and_never_keeps_pdf_bytes():
    fake = Fake(govinfo_answers)
    client = GovInfoClient(clock=lambda: CLOCK, transport=fake)
    meta = metadata(N)
    pdf, html, mods = (client.fetch(k, meta).record for k in ("PDF", "HTML", "MODS"))
    assert isinstance(pdf, GovInfoPdf) and not hasattr(pdf, "body")
    assert pdf.sha256 == entry(N, "GOVINFO_PDF")["sha256"] and pdf.retrieved_at == CLOCK
    assert isinstance(html, GovInfoHtml) and html.sha256 == entry(N, "GOVINFO_HTML")["sha256"]
    assert isinstance(mods, GovInfoModsRetrieval) and mods.url == OFFICIAL
    assert [c[0] for c in fake.calls] == [govinfo_url(k, D, N) for k in ("PDF", "HTML", "MODS")]
    assert [c[1] for c in fake.calls] == [MAX_BYTES["PDF"], MAX_BYTES["HTML"], MAX_BYTES["MODS"]]


def test_govinfo_redirect_and_failures_leave_the_component_absent_without_retry():
    fake = Fake(lambda url: HttpResponse(302, {"location": "https://www.govinfo.gov/error"}))
    client = GovInfoClient(clock=lambda: CLOCK, transport=fake)
    got = client.fetch("MODS", metadata(N))
    assert got.record is None and got.reason == "SOURCE_UNAVAILABLE:REDIRECT_NOT_FOLLOWED:https://www.govinfo.gov/error"
    assert len(fake.calls) == 1


def test_request_budget_is_fixed_and_counted():
    fake = Fake(govinfo_answers)
    client = GovInfoClient(clock=lambda: CLOCK, transport=fake, budget=2)
    meta = metadata(N)
    assert client.fetch("PDF", meta).record is not None and client.fetch("HTML", meta).record is not None
    assert client.fetch("MODS", meta).reason == "SOURCE_UNAVAILABLE:REQUEST_BUDGET_EXHAUSTED"
    assert len(fake.calls) == 2
    with pytest.raises(ValueError):
        GovInfoClient(budget=0)


def test_clock_must_be_aware():
    client = GovInfoClient(clock=lambda: datetime(2026, 10, 24), transport=Fake(govinfo_answers))
    with pytest.raises(ValueError):
        client.fetch("MODS", metadata(N))


FR_JSON = {"content-type": "application/json; charset=utf-8"}


def test_federal_register_document_parse_and_failures():
    raw = body(N, "FEDERAL_REGISTER_JSON")
    fake = Fake({sources.fr_document_url(N): HttpResponse(200, FR_JSON, raw)})
    got = FederalRegisterClient(clock=lambda: CLOCK, transport=fake).document(N)
    assert got.record.citation == "89 FR 3008" and got.record.retrieved_at == CLOCK
    assert "FEDERAL_REGISTER_RATE_LIMITS_UNDOCUMENTED" in got.limitations
    for answer, why in ((HttpResponse(429), "SOURCE_UNAVAILABLE:HTTP_429"), (HttpResponse(503), "SOURCE_UNAVAILABLE:HTTP_503"),
                        (HttpResponse(0, timed_out=True), "SOURCE_UNAVAILABLE:TIMEOUT"),
                        (HttpResponse(200, FR_JSON, b"{not json"), "SOURCE_UNAVAILABLE:MALFORMED_JSON"),
                        (HttpResponse(200, FR_JSON, json.dumps({"document_number": N}).encode()), "SOURCE_UNAVAILABLE:MALFORMED_METADATA"),
                        (HttpResponse(200, FR_JSON, raw.replace(b'"2024-00743"', b'"2024-00744"', 1)),
                         "SOURCE_UNAVAILABLE:DOCUMENT_NUMBER_MISMATCH"),
                        (HttpResponse(200, {"content-type": "text/html"}, b"<html>Request Access</html>"),
                         "SOURCE_UNAVAILABLE:CONTENT_TYPE:text/html")):
        fake = Fake(lambda url, a=answer: a)
        assert FederalRegisterClient(clock=lambda: CLOCK, transport=fake).document(N).reason == why
        assert len(fake.calls) == 1                     # no retry loop
    assert FederalRegisterClient(transport=Fake({})).document("2024-743").reason == "DOCUMENT_NUMBER_INVALID"


def test_parse_fr_document_types_are_strict():
    raw = json.loads(body(N, "FEDERAL_REGISTER_JSON"))
    bad = dict(raw, volume="89")
    assert parse_fr_document(json.dumps(bad).encode(), requested=N, source_url="u", retrieved_at=CLOCK) == \
        "SOURCE_UNAVAILABLE:MALFORMED_METADATA"
    record = parse_fr_document(json.dumps(dict(raw, corrections=["C1-2024-26524"])).encode(), requested=N, source_url="u",
                               retrieved_at=CLOCK)
    assert record.corrections == ("C1-2024-26524",)


def test_public_inspection_record():
    payload = json.dumps({"document_number": N, "filed_at": "2024-01-16T08:45:00.000-05:00"}).encode()
    record = parse_fr_public_inspection(payload, requested=N, source_url="u", retrieved_at=CLOCK)
    assert record.filed_at == datetime(2024, 1, 16, 13, 45, tzinfo=UTC) and record.filed_at_source.endswith("-05:00")
    fake = Fake({sources.fr_public_inspection_url(N): HttpResponse(200, FR_JSON, payload)})
    assert FederalRegisterClient(clock=lambda: CLOCK, transport=fake).public_inspection(N).record == \
        record.model_copy(update={"source_url": sources.fr_public_inspection_url(N)})


def test_docket_listing_completeness():
    page = lambda count, numbers, more: HttpResponse(200, FR_JSON, json.dumps(
        {"count": count, "results": [{"document_number": n} for n in numbers],
         **({"next_page_url": "https://www.federalregister.gov/api/v1/documents.json?page=2"} if more else {})}).encode())
    complete = FederalRegisterClient(clock=lambda: CLOCK, transport=Fake(lambda url: page(2, ["2022-14310", "2024-00743"], False)))
    got = complete.docket_listing("SR-NYSEArca-2021-90")
    assert got.record.complete and got.record.file_number == "SR-NYSEARCA-2021-90" and "RESULT_SET_INCOMPLETE" not in got.limitations
    partial = FederalRegisterClient(clock=lambda: CLOCK, transport=Fake(lambda url: page(692, ["2024-00743"], True)))
    got = partial.docket_listing("SR-NYSEARCA-2021-90", max_pages=2)
    assert not got.record.complete and got.record.pages_fetched == 2 and "RESULT_SET_INCOMPLETE" in got.limitations
    assert parse_fr_docket_page(b"[]") == "SOURCE_UNAVAILABLE:MALFORMED_JSON"
    assert FederalRegisterClient(transport=Fake({})).docket_listing("not a file").reason == "FILE_NUMBER_INVALID"


def test_default_transport_never_follows_redirects(monkeypatch):
    """The real opener is configured with the no-redirect handler; a 3xx surfaces as that status."""
    handler = sources._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://www.govinfo.gov/error") is None

    class Opener:
        def open(self, request, timeout):
            assert request.get_header("User-agent") == sources.USER_AGENT
            assert not any("mail" in k.lower() or "auth" in k.lower() or "key" in k.lower() for k in request.headers)
            headers = Message()
            headers["Location"] = "https://www.govinfo.gov/error"
            raise HTTPError(request.full_url, 302, "Found", headers, io.BytesIO(b""))

    monkeypatch.setattr(sources, "build_opener", lambda *handlers: Opener())
    got = sources.http_get(OFFICIAL, cap=100, timeout=5)
    assert got.status == 302 and accept_response("MODS", got) == "SOURCE_UNAVAILABLE:REDIRECT_NOT_FOLLOWED:https://www.govinfo.gov/error"


def test_default_transport_stops_at_the_size_cap(monkeypatch):
    class Response:
        status = 200
        headers = {"Content-Type": "text/xml"}

        def __init__(self):
            self.stream = io.BytesIO(b"x" * 500)

        def read(self, n):
            return self.stream.read(n)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class Opener:
        def open(self, request, timeout):
            return Response()

    monkeypatch.setattr(sources, "build_opener", lambda *handlers: Opener())
    got = sources.http_get(OFFICIAL, cap=100, timeout=5)
    assert got.truncated and len(got.body) == 101 and accept_response("MODS", got) == "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"


def test_default_transport_maps_timeouts(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise TimeoutError()

    monkeypatch.setattr(sources, "build_opener", lambda *handlers: Opener())
    assert sources.http_get(OFFICIAL, cap=100, timeout=0.01).timed_out
