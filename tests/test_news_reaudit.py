"""Regression tests for the three defects confirmed by the independent C13 re-audit.

1. Unbound supersession: a record that is not admitted and bound to a TraID PDF retrieval of the
   same bytes never removes another record (R4 §6.4 item 3: heads per (document, pdf_sha256)).
2. Canonical fund provenance: fund-link evidence is keyed by the frame's resolved file number, so
   every equivalent representation serializes identically, fund_resolutions included.
3. Premature HTTP EOF: a completed fixed-length body must have exactly the declared length.

REAL official components and REAL http.client response parsing; SYNTHETIC_TEST manual records and
fund link (no human record exists).
"""
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import io
import itertools

import pytest

from news_support import NOW, TEST_POLICY, _no_network, body, claim, curate, records, retimed, retrieval  # noqa: F401
from test_news_qualification import edited_record, qualify, replace
from test_news_remediation import (
    ADVERSE, E, E_ONE, approval_claim, dump, fake_opener, revision_with_record, run,
)
from traid.news import verify
from traid.news.models import DEFAULT_POLICY, ManualPassageVerification, RecordPurpose, VerificationState, sha256_hex
import traid.news.sources as sources
from traid.news.sources import GovInfoClient, HttpResponse, MAX_BYTES, accept_response, http_get
from traid.news.text import html_text, normalize_passage

UTC = timezone.utc
S = VerificationState
N = "2024-00743"
BASE = edited_record(N)                                         # available 2026-10-23T20:05Z
ADVERSE_AT = datetime(2026, 10, 23, 20, 30, tzinfo=UTC)
CLAIM_AT = datetime(2026, 10, 23, 20, 40, tzinfo=UTC)
RETRIEVE_AT = datetime(2026, 10, 23, 21, tzinfo=UTC)
REPLACE_AT = datetime(2026, 10, 23, 21, 30, tzinfo=UTC)
CUTOFFS = (REPLACE_AT - timedelta(microseconds=1), REPLACE_AT, REPLACE_AT + timedelta(days=1))
CLEAN = [c.value for c in BASE.absent_checks]


# ===================================================================== Fix 1: unbound supersession
def manual(record_id, *, adverse=False, supersedes=None, at=ADVERSE_AT, **changes) -> ManualPassageVerification:
    checks = ADVERSE["second_operative_rendered"] if adverse else CLEAN
    return ManualPassageVerification.model_validate({**BASE.model_dump(), "record_id": record_id, "absent_checks": checks,
                                                     "verified_at": at, "recorded_at": at, "supersedes": supersedes,
                                                     **changes})


ADV = manual("SYN-ADVERSE", adverse=True)
REVISION_PDF = retrieval(N, "GOVINFO_PDF", retrieved_at=RETRIEVE_AT, data=b"%PDF-1.7 regenerated")
OTHER_URL = next(r for r in records() if r.document_number == "2022-14310" and r.purpose is RecordPurpose.QUALIFYING).pdf_url
UNBOUND = {                                    # the replacement's binding; none is a TraID retrieval of these bytes
    "unretrieved_hash": dict(pdf_sha256=sha256_hex(b"bytes TraID never retrieved")),
    "missing_retrieval": dict(pdf_retrieved_at=RETRIEVE_AT),          # same bytes, retrieval absent from evidence
    "other_document_url": dict(pdf_url=OTHER_URL),
    "bound_to_other_bytes": dict(pdf_sha256=REVISION_PDF.sha256, pdf_retrieved_at=RETRIEVE_AT),
}


def replacement(variant, target="SYN-ADVERSE", record_id="SYN-REPLACEMENT", **kw):
    return manual(record_id, supersedes=target, at=REPLACE_AT, **{**UNBOUND.get(variant, {}), **kw})


def evidence(*recs, pdf=()):
    return replace(E_ONE, pdf=E_ONE.pdf + tuple(pdf), manual_records=recs)


def comparable(result) -> dict:
    """Everything but the input digest and exclusion counts, which identify the inputs, not the verdict."""
    return result.model_dump(mode="json", exclude={"input_digest", "excluded_after_evaluation"})


@pytest.mark.parametrize("variant", sorted(UNBOUND))
def test_fix1_unbound_record_superseding_the_adverse_record_never_restores_confirmed(variant):
    pdf = (REVISION_PDF,) if variant == "bound_to_other_bytes" else ()
    assert qualify(N, evidence(BASE, ADV)).reason == "CONFLICTING_MANUAL_VERIFICATIONS"
    ev = evidence(BASE, ADV, replacement(variant), pdf=pdf)
    assert qualify(N, ev).reason == "CONFLICTING_MANUAL_VERIFICATIONS"     # pre-fix: None (qualified)
    c, cur = approval_claim(received=CLAIM_AT)
    for T in CUTOFFS:                                                     # before, at and after the replacement
        r = run(c, cur, T=T, ev=ev)
        assert r.state is S.UNVERIFIED and "DOCUMENT_NOT_QUALIFIED:CONFLICTING_MANUAL_VERIFICATIONS" in r.reasons, T
        assert comparable(r) == comparable(run(c, cur, T=T, ev=evidence(BASE, ADV, pdf=pdf))), T     # no effect at all


def test_fix1_unbound_supersession_is_stable_under_duplicates_and_reordering():
    c, cur = approval_claim(received=CLAIM_AT)
    recs = (BASE, ADV, replacement("unretrieved_hash"), replacement("missing_retrieval", record_id="SYN-REPLACEMENT-2"))
    outputs = {dump(run(c, cur, ev=evidence(*(order + order[:2])))) for order in itertools.permutations(recs)}
    assert len(outputs) == 1 and "CONFLICTING_MANUAL_VERIFICATIONS" in outputs.pop()


def test_fix1_adverse_later_revision_record_is_not_removed_by_an_unbound_replacement():
    pdf2, rev = revision_with_record(ADVERSE["second_operative_rendered"], record_id="SYN-REV-LATER")
    ev = replace(E_ONE, pdf=E_ONE.pdf + (pdf2,), manual_records=(BASE, rev, replacement("unretrieved_hash", "SYN-REV-LATER")))
    assert qualify(N, ev).reason == "UNCLASSIFIED_SEC_NOTICE"             # pre-fix: PDF_REVISION_UNVERIFIED (evidence lost)


@pytest.mark.parametrize("binding", ["original_retrieval", "later_retrieval_of_the_same_bytes"])
def test_fix1_bound_replacement_follows_the_designed_supersedes_path_only_once_bound_and_available(binding):
    """R4 §6.4 item 3 / R2-10: an admitted record bound to a TraID retrieval of the same bytes may correct an
    earlier record of that retrieval. It acts only from its own availability, and only while its retrieval exists."""
    later = RETRIEVE_AT
    same_bytes = retrieval(N, "GOVINFO_PDF", retrieved_at=later)
    assert same_bytes.sha256 == BASE.pdf_sha256
    fix = replacement(None) if binding == "original_retrieval" else replacement(None, pdf_retrieved_at=later)
    pdf = () if binding == "original_retrieval" else (same_bytes,)
    c, cur = approval_claim(received=CLAIM_AT)
    before, at, after = (run(c, cur, T=T, ev=evidence(BASE, ADV, fix, pdf=pdf)) for T in CUTOFFS)
    assert before.state is S.UNVERIFIED and "DOCUMENT_NOT_QUALIFIED:CONFLICTING_MANUAL_VERIFICATIONS" in before.reasons
    assert at.state is S.CONFIRMED and after.state is S.CONFIRMED
    q = qualify(N, evidence(BASE, ADV, fix, pdf=pdf))
    assert q.reason is None and q.document.qualifying_record_id == BASE.record_id
    if pdf:                                                               # the same record without its retrieval
        for T in CUTOFFS:
            assert run(c, cur, T=T, ev=evidence(BASE, ADV, fix)).state is S.UNVERIFIED, T
    outputs = {dump(run(c, cur, ev=evidence(*(order + order[:1]), pdf=pdf + pdf))) for order in itertools.permutations((BASE, ADV, fix))}
    assert len(outputs) == 1
    for T in CUTOFFS:                                                     # production: never concluded
        assert run(c, cur, T=T, ev=evidence(BASE, ADV, fix, pdf=pdf), policy=DEFAULT_POLICY).state is S.UNVERIFIED


def test_fix1_bound_replacement_that_is_itself_adverse_never_confirms():
    fix = replacement(None, absent_checks=ADVERSE["second_operative_rendered"], target=BASE.record_id)
    assert qualify(N, evidence(BASE, ADV, fix)).reason == "UNCLASSIFIED_SEC_NOTICE"


def test_fix1_supersedes_cycle_among_bound_records_has_no_head():
    a = manual(BASE.record_id, at=BASE.recorded_at, supersedes="SYN-ADVERSE")
    b = manual("SYN-ADVERSE", supersedes=BASE.record_id)
    assert qualify(N, evidence(a, b)).reason == "CONFLICTING_MANUAL_VERIFICATIONS"


# ===================================================================== Fix 2: canonical fund provenance
FILE = "SR-NASDAQ-2023-016"
TEXT = "SEC approved the rule change"


def event_curation(c, events, *, split=False):
    """events: [(event id, subject, action)]; each event's ACTION fact in its own proposition (or split in two)."""
    props = []
    for i, (eid, subject, action) in enumerate(events):
        props.append((f"p{i}", eid, [("ACTION", action)]))
        if split:
            props.append((f"q{i}", eid, [("ACTION", action)]))
    return curate(c, [(eid, "REG_EVENT", {"subjects": (subject,), "action": action}) for eid, subject, action in events], props)


SPELLINGS = [("FUND:IBIT", "RULE_CHANGE_APPROVED"), ("FUND:iShares Bitcoin Trust", "RULE_CHANGE_APPROVED"),
             ("FUND:iShares   Bitcoin Trust", "RULE_CHANGE_APPROVED"), (FILE, "APPROVED"), (FILE, "RULE_CHANGE_APPROVED"),
             ("sr–nasdaq–2023–016", "APPROVED")]


def report_digest(c, cur, ev=E) -> str:
    report = verify(claims=(c,), curations=(cur,), evidence=ev, evaluation_time=NOW, policy=TEST_POLICY)
    return hashlib.sha256(report.model_dump_json().encode()).hexdigest()


def test_fix2_fund_name_ticker_and_linked_file_curations_are_byte_identical():
    c = claim(TEXT)
    outputs, digests = set(), set()
    for subject, action in SPELLINGS:
        cur = event_curation(c, [("e", subject, action)])
        r = run(c, cur)
        assert r.state is S.CONFIRMED and [x.link_id for fr in r.frames for x in fr.fund_resolutions] == ["SYN-LINK-IBIT"], subject
        outputs.add(dump(r))
        digests.add(report_digest(c, cur))
    assert len(outputs) == 1 and len(digests) == 1                        # pre-fix: the file spellings had no evidence


def test_fix2_equivalent_events_under_adversarial_ids_duplicates_and_permutations():
    c = claim(TEXT)
    expected = dump(run(c, event_curation(c, [("e", FILE, "APPROVED")])))
    ids = ["a", "z", f"e#{FILE}", "E1", "E2"]
    outputs = set()
    for x, y in itertools.permutations(ids, 2):
        for order in ((0, 1), (1, 0)):
            events = [(x, "FUND:IBIT", "RULE_CHANGE_APPROVED"), (y, FILE, "APPROVED")]
            events = [events[i] for i in order]
            for split, extra in ((False, []), (True, [("dup", "FUND:iShares Bitcoin Trust", "RULE_CHANGE_APPROVED")])):
                r = run(c, event_curation(c, events + extra, split=split))
                assert [l.link_id for fr in r.frames for l in fr.fund_resolutions] == ["SYN-LINK-IBIT"], (x, y, order, split)
                outputs.add(dump(r))
    assert outputs == {expected}                                          # pre-fix: evidence present or absent by id order


def test_fix2_provenance_references_are_accessible_for_the_file_number_spelling():
    c = claim(TEXT)
    (frame,) = run(c, event_curation(c, [("e", FILE, "APPROVED")])).frames
    (res,) = frame.fund_resolutions
    link = next(l for l in E.fund_links if l.link_id == res.link_id)
    assert (res.file_number, res.name_in_document, res.ticker, res.cik, res.sro, res.document_number,
            res.identity_evidence, res.link_curated_at) == (link.file_number, link.name_in_document, link.ticker, link.cik,
                                                             link.sro, link.document_number, link.identity_evidence, link.curated_at)
    document = qualify(res.document_number, E).document                   # official document identity
    assert res.file_number in document.file_numbers and document.qualifying_record_id == res.qualifying_record_id
    name_record = next(m for m in E.manual_records if m.record_id == res.name_passage.manual_record_id)
    assert name_record.record_id == link.name_record_id and name_record.qualifying_record_id == res.qualifying_record_id
    assert normalize_passage(res.name_in_document) in res.name_passage.normalized_text
    html = min((h for h in E.html if h.document_number == res.document_number), key=lambda h: (h.retrieved_at, h.sha256))
    _, offset = res.name_passage.html_location
    assert html_text(html.body.decode("utf-8"))[offset:offset + len(res.name_passage.normalized_text)] == res.name_passage.normalized_text
    assert res.available_at == max(link.curated_at, link.identity_evidence.received_timestamp, name_record.available_at,
                                   document.available_at)


def test_fix2_deduplication_never_removes_a_link_relied_on():
    c = claim(TEXT)
    twin = E.fund_links[0].model_copy(update={"link_id": "SYN-LINK-IBIT-COPY"})
    outputs = set()
    for subject, action in SPELLINGS[:4]:
        cur = event_curation(c, [("e", subject, action)])
        for links in itertools.permutations(E.fund_links + E.fund_links + (twin,)):
            r = run(c, cur, ev=replace(E, fund_links=links))
            assert [l.link_id for fr in r.frames for l in fr.fund_resolutions] == ["SYN-LINK-IBIT", "SYN-LINK-IBIT-COPY"]
            outputs.add(dump(r))
    assert len(outputs) == 1


def test_fix2_document_subject_fact_carries_the_same_evidence_for_both_spellings():
    c = claim("FR 2023-21948 instituted proceedings on IBIT")
    found = set()
    for subject in ("FUND:IBIT", FILE):
        cur = curate(c, [("e", "REG_DOC", {"document_number": "2023-21948"})],
                     [("p", "e", [("ACTION", "INSTITUTED_PROCEEDINGS"), ("SUBJECT", subject)])])
        r = run(c, cur)
        assert r.state is S.CONFIRMED
        found.add(tuple(x.model_dump_json() for fr in r.frames for x in fr.fund_resolutions))
    assert len(found) == 1 and len(found.pop()) == 1


def test_fix2_no_link_evidence_where_none_is_valid_or_relevant():
    c = claim("SEC disapproved SR-NYSEARCA-2021-90")
    r = run(c, event_curation(c, [("e", "SR-NYSEARCA-2021-90", "DISAPPROVED")]))
    assert r.state is S.CONFIRMED and all(fr.fund_resolutions == () for fr in r.frames)       # no link to this file
    at = datetime(2024, 1, 17, 12, tzinfo=UTC)
    c = claim(TEXT, received=at)
    cur = event_curation(c, [("e", FILE, "APPROVED")]).model_copy(update={"curated_at": at})
    early = run(c, cur, T=datetime(2024, 1, 18, tzinfo=UTC), ev=retimed(at, link_at=datetime(2026, 10, 23, tzinfo=UTC)))
    assert all(fr.fund_resolutions == () for fr in early.frames)          # the link is not yet curated at T
    c = claim(TEXT)
    for subject, action in SPELLINGS[:4]:
        production = run(c, event_curation(c, [("e", subject, action)]), policy=DEFAULT_POLICY)
        assert production.state is S.UNVERIFIED and all(fr.fund_resolutions == () for fr in production.frames)


# ===================================================================== Fix 3: premature HTTP EOF
MODS = body(N, "GOVINFO_MODS")
MODS_URL = "https://www.govinfo.gov/metadata/granule/FR-2024-01-17/2024-00743/mods.xml"
assert len(MODS) == 12091


class _Socket:
    def __init__(self, raw: bytes):
        self._file = io.BytesIO(raw)

    def makefile(self, *args, **kwargs):
        return self._file


def real_response(headers: list[str], payload: bytes) -> http.client.HTTPResponse:
    """A genuine http.client.HTTPResponse parsed from raw bytes (the class urllib returns for https)."""
    raw = ("HTTP/1.1 200 OK\r\n" + "".join(f"{h}\r\n" for h in headers) + "\r\n").encode() + payload
    response = http.client.HTTPResponse(_Socket(raw), method="GET")
    response.begin()
    return response


def chunked(payload: bytes, size: int = 4096) -> bytes:
    parts = [b"%x\r\n%s\r\n" % (len(payload[i:i + size]), payload[i:i + size]) for i in range(0, len(payload), size)]
    return b"".join(parts) + b"0\r\n\r\n"


XML = "Content-Type: text/xml"
META = next(m for m in E.fr_metadata if m.document_number == N)


def fetch_mods(monkeypatch, response):
    seen = fake_opener(monkeypatch, response)
    got = http_get(MODS_URL, cap=MAX_BYTES["MODS"], timeout=5.0)
    assert any(isinstance(h, sources._NoRedirect) for h in seen["handlers"])            # no-redirect policy kept
    return got


def test_fix3_complete_fixed_length_response_is_accepted(monkeypatch):
    got = fetch_mods(monkeypatch, real_response([XML, "Content-Length: 12091"], MODS))
    assert got.status == 200 and got.body == MODS and accept_response("MODS", got) == "OK"


def test_fix3_codex_case_content_length_12191_with_12091_bytes_is_incomplete(monkeypatch):
    got = fetch_mods(monkeypatch, real_response([XML, "Content-Length: 12191"], MODS))
    assert got == HttpResponse(status=0, failure="INCOMPLETE_READ") and got.body is None     # pre-fix: 200, 12091 bytes, OK
    assert accept_response("MODS", got) == "SOURCE_UNAVAILABLE:INCOMPLETE_READ"


@pytest.mark.parametrize("payload", [MODS[:-1], MODS[:1], b""], ids=["one_byte_short", "one_byte", "empty"])
def test_fix3_every_premature_eof_on_a_fixed_length_body_is_incomplete(monkeypatch, payload):
    got = fetch_mods(monkeypatch, real_response([XML, "Content-Length: 12091"], payload))
    assert got == HttpResponse(status=0, failure="INCOMPLETE_READ")


def test_fix3_client_returns_a_deterministic_unavailable_outcome_through_the_default_transport(monkeypatch):
    outcomes = []
    for _ in range(2):
        fake_opener(monkeypatch, real_response([XML, "Content-Length: 12191"], MODS))
        client = GovInfoClient(clock=lambda: NOW, budget=1)
        outcomes.append(client.fetch("MODS", META))
        assert client.remaining == 0                                                     # counted, never retried
    assert outcomes[0] == outcomes[1] and outcomes[0].record is None
    assert outcomes[0].reason == "SOURCE_UNAVAILABLE:INCOMPLETE_READ"
    fake_opener(monkeypatch, real_response([XML, "Content-Length: 12091"], MODS))
    ok = GovInfoClient(clock=lambda: NOW).fetch("MODS", META)
    assert ok.reason is None and ok.record.sha256 == sha256_hex(MODS) and ok.record.byte_length == 12091


def test_fix3_chunked_responses(monkeypatch):
    got = fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: chunked"], chunked(MODS)))
    assert got.body == MODS and accept_response("MODS", got) == "OK"
    cut = chunked(MODS)[:6000]                                            # interrupted inside a chunk
    got = fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: chunked"], cut))
    assert got == HttpResponse(status=0, failure="INCOMPLETE_READ")
    got = fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: chunked"], chunked(MODS)[:-5]))   # no last chunk
    assert got == HttpResponse(status=0, failure="INCOMPLETE_READ")
    both = real_response([XML, "Transfer-Encoding: chunked", "Content-Length: 12091"], chunked(MODS))
    assert fetch_mods(monkeypatch, both) == HttpResponse(status=0, failure="HTTP_PROTOCOL_ERROR")   # RFC 9112 §6.3


def test_fix3_close_delimited_body_without_declared_length(monkeypatch):
    """No Content-Length and no chunking: the body ends at connection close and its length cannot be checked
    (HTTP/1.1 framing). It is accepted as received, still under the size cap; this is a stated limitation."""
    got = fetch_mods(monkeypatch, real_response([XML, "Connection: close"], MODS))
    assert got.body == MODS and accept_response("MODS", got) == "OK"


def test_fix3_oversized_responses_stay_bounded(monkeypatch):
    cap = MAX_BYTES["MODS"]
    declared = fetch_mods(monkeypatch, real_response([XML, f"Content-Length: {cap + 1}"], MODS))   # also a premature EOF
    assert declared.truncated and declared.body is None
    assert accept_response("MODS", declared) == "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"
    big = b"x" * (cap + 10)
    streamed = fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: chunked"], chunked(big, 65536)))
    assert streamed.truncated and len(streamed.body) == cap + 1                          # never read past cap + 1
    assert accept_response("MODS", streamed) == "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"


@pytest.mark.parametrize("headers", [
    ["Content-Length: 12091x"], ["Content-Length: -12091"], ["Content-Length: +12091"], ["Content-Length: 1 2091"],
    ["Content-Length: 12091", "Content-Length: 12191"],
])
def test_fix3_malformed_or_conflicting_declared_length_fails_closed(monkeypatch, headers):
    got = fetch_mods(monkeypatch, real_response([XML] + headers, MODS))
    assert got == HttpResponse(status=0, failure="HTTP_PROTOCOL_ERROR")
    assert accept_response("MODS", got) == "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"


def test_fix3_repeated_identical_content_length_is_one_declaration(monkeypatch):
    got = fetch_mods(monkeypatch, real_response([XML, "Content-Length: 12091", "Content-Length: 12091"], MODS))
    assert got.body == MODS and accept_response("MODS", got) == "OK"


@pytest.mark.parametrize("length, reason", [("12191", "SOURCE_UNAVAILABLE:INCOMPLETE_READ"),
                                            ("12000", "SOURCE_UNAVAILABLE:CONTENT_LENGTH_MISMATCH"),
                                            ("abc", "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"), ("12091", "OK")])
def test_fix3_injected_transport_responses_are_checked_against_their_declared_length(length, reason):
    response = HttpResponse(200, {"content-type": "text/xml", "content-length": length}, MODS)
    assert accept_response("MODS", response) == reason
    client = GovInfoClient(transport=lambda url, cap, timeout: response, clock=lambda: NOW, budget=1)
    fetched = client.fetch("MODS", META)
    assert (fetched.reason or "OK") == reason and (fetched.record is None) == (reason != "OK") and client.remaining == 0
