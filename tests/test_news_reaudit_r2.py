"""Regression tests for the two defects confirmed by the second independent C13 re-audit.

A. Supersession cycles: a cycle among admitted, bound records of one (document, pdf_sha256) is
   CONFLICTING_MANUAL_VERIFICATIONS; cyclic records never vanish, even beside a surviving good record.
B. Transfer-Encoding: only a single exact ``chunked`` coding (as http.client decodes it) is accepted;
   compound, unknown, repeated or contradictory framing fails closed with HTTP_PROTOCOL_ERROR.

REAL official components and REAL http.client response parsing; SYNTHETIC_TEST manual records.
"""
from datetime import timedelta
import itertools

import pytest

from news_support import NOW, _no_network  # noqa: F401  (autouse fixture)
from test_news_qualification import qualify
from test_news_reaudit import (
    ADVERSE_AT, BASE, CLAIM_AT, CUTOFFS, META, MODS, N, REPLACE_AT, XML, chunked, evidence, fetch_mods, manual,
    real_response,
)
from test_news_remediation import approval_claim, dump, run
from traid.news.models import DEFAULT_POLICY, VerificationState
import traid.news.sources as sources
from traid.news.sources import GovInfoClient, HttpResponse, MAX_BYTES, accept_response

S = VerificationState
CONFLICT = "CONFLICTING_MANUAL_VERIFICATIONS"


# ===================================================================== Fix A: supersession cycles
def ring(ids, adverse=(), at=ADVERSE_AT):
    """Records ids[0] -> ids[1] -> ... -> ids[0] (each supersedes the next), the ``adverse`` ones reporting a
    second rendered operative sentence."""
    return tuple(manual(i, adverse=i in adverse, supersedes=ids[(k + 1) % len(ids)], at=at) for k, i in enumerate(ids))


def outcome(*recs, T=NOW):
    c, cur = approval_claim(received=CLAIM_AT)
    return run(c, cur, T=T, ev=evidence(*recs))


@pytest.mark.parametrize("adverse", [("SYN-CYCLE-A",), ("SYN-CYCLE-B",), ()], ids=["A_adverse", "B_adverse", "none_adverse"])
def test_fixA_codex_case_two_record_cycle_beside_a_surviving_good_record(adverse):
    cycle = ring(["SYN-CYCLE-A", "SYN-CYCLE-B"], adverse)
    assert qualify(N, evidence(BASE, *cycle)).reason == CONFLICT          # pre-fix: qualified by BASE alone
    r = outcome(BASE, *cycle)
    assert r.state is S.UNVERIFIED and f"DOCUMENT_NOT_QUALIFIED:{CONFLICT}" in r.reasons


@pytest.mark.parametrize("adverse", [True, False])
def test_fixA_self_cycle_never_disappears(adverse):
    me = manual("SYN-SELF", adverse=adverse, supersedes="SYN-SELF")
    assert qualify(N, evidence(BASE, me)).reason == CONFLICT
    assert qualify(N, evidence(me)).reason == CONFLICT


@pytest.mark.parametrize("length", [3, 4])
def test_fixA_longer_cycles_and_a_chain_feeding_a_cycle(length):
    ids = [f"SYN-RING-{k}" for k in range(length)]
    cycle = ring(ids, adverse=(ids[-1],))
    assert qualify(N, evidence(BASE, *cycle)).reason == CONFLICT
    feeder = manual("SYN-FEEDER", supersedes=ids[0])                     # an acyclic record pointing into the cycle
    assert qualify(N, evidence(BASE, feeder, *cycle)).reason == CONFLICT


def test_fixA_duplicates_and_permutations_give_identical_bytes():
    cycle = ring(["SYN-CYCLE-A", "SYN-CYCLE-B"], ("SYN-CYCLE-A",))
    recs = (BASE,) + cycle
    outputs = {dump(outcome(*(order + order))) for order in itertools.permutations(recs)}
    assert len(outputs) == 1 and CONFLICT in outputs.pop()
    reasons = {qualify(N, evidence(*(order + order[:1]))).reason for order in itertools.permutations(recs)}
    assert reasons == {CONFLICT}


@pytest.mark.parametrize("closing_is_adverse", [True, False])
def test_fixA_before_at_and_after_the_cycle_closes(closing_is_adverse):
    """A (available first) supersedes B; B (available at REPLACE_AT) supersedes A and closes the cycle."""
    a = manual("SYN-CYCLE-A", adverse=not closing_is_adverse, supersedes="SYN-CYCLE-B", at=ADVERSE_AT)
    b = manual("SYN-CYCLE-B", adverse=closing_is_adverse, supersedes="SYN-CYCLE-A", at=REPLACE_AT)
    before, at, after = (outcome(BASE, a, b, T=T) for T in CUTOFFS)
    if closing_is_adverse:
        assert before.state is S.CONFIRMED                               # A is a clean head; B not yet known
    else:
        assert before.state is S.UNVERIFIED and f"DOCUMENT_NOT_QUALIFIED:{CONFLICT}" in before.reasons   # A adverse
    for r in (at, after):                                                # pre-fix: CONFIRMED (both hidden)
        assert r.state is S.UNVERIFIED and f"DOCUMENT_NOT_QUALIFIED:{CONFLICT}" in r.reasons
    for T in CUTOFFS:
        assert dump(outcome(BASE, a, b, T=T)) == dump(outcome(b, a, BASE, BASE, T=T))   # order and duplicates
        c, cur = approval_claim(received=CLAIM_AT)
        assert run(c, cur, T=T, ev=evidence(BASE, a, b), policy=DEFAULT_POLICY).state is S.UNVERIFIED


def test_fixA_valid_acyclic_supersession_still_resolves_to_the_latest_head():
    first = manual("SYN-CHAIN-1", adverse=True)
    second = manual("SYN-CHAIN-2", adverse=True, supersedes="SYN-CHAIN-1", at=ADVERSE_AT + timedelta(minutes=5))
    third = manual("SYN-CHAIN-3", supersedes="SYN-CHAIN-2", at=ADVERSE_AT + timedelta(minutes=10))
    outputs = set()
    for order in itertools.permutations((BASE, first, second, third)):
        q = qualify(N, evidence(*(order + order[:1])))
        assert q.reason is None and q.document.qualifying_record_id == BASE.record_id
        outputs.add(dump(outcome(*order)))
    assert len(outputs) == 1 and outcome(BASE, first, second, third).state is S.CONFIRMED
    assert qualify(N, evidence(BASE, first, second)).reason == CONFLICT  # the chain's head is still adverse
    fork = manual("SYN-FORK", adverse=True, supersedes="SYN-CHAIN-1")    # two heads over one record: compared
    assert qualify(N, evidence(BASE, first, third.model_copy(update={"supersedes": "SYN-CHAIN-1"}), fork)).reason == CONFLICT


# ===================================================================== Fix B: Transfer-Encoding framing
def protocol_error(got):
    return got == HttpResponse(status=0, failure="HTTP_PROTOCOL_ERROR") and accept_response("MODS", got) == \
        "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"


@pytest.mark.parametrize("coding", ["gzip, chunked", "xchunked"])
def test_fixB_codex_cases_fail_closed(monkeypatch, coding):
    response = real_response([XML, f"Transfer-Encoding: {coding}"], chunked(MODS))
    assert response.chunked is False                                     # http.client does not decode them
    got = fetch_mods(monkeypatch, response)
    assert protocol_error(got) and got.body is None                      # pre-fix: OK with the raw chunk framing


@pytest.mark.parametrize("coding", ["chunked", "Chunked", "CHUNKED", " chunked"])
def test_fixB_valid_chunked_response(monkeypatch, coding):
    got = fetch_mods(monkeypatch, real_response([XML, f"Transfer-Encoding:{coding}"], chunked(MODS)))
    assert got.status == 200 and got.body == MODS and accept_response("MODS", got) == "OK"


def test_fixB_missing_terminal_chunk_and_interrupted_chunk_are_incomplete(monkeypatch):
    for payload in (chunked(MODS)[:-5], chunked(MODS)[:6000]):
        got = fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: chunked"], payload))
        assert got == HttpResponse(status=0, failure="INCOMPLETE_READ") and got.body is None


@pytest.mark.parametrize("coding", ["gzip, chunked", "chunked, gzip", "chunked, chunked", "deflate,chunked", "gzip,  chunked"])
def test_fixB_compound_encodings(monkeypatch, coding):
    assert protocol_error(fetch_mods(monkeypatch, real_response([XML, f"Transfer-Encoding: {coding}"], chunked(MODS))))


@pytest.mark.parametrize("coding", ["xchunked", "chunkedx", "gzip", "identity", "compress", "chunked ", "chunked\t", "chunked;q=1"])
def test_fixB_unknown_or_malformed_encodings(monkeypatch, coding):
    assert protocol_error(fetch_mods(monkeypatch, real_response([XML, f"Transfer-Encoding:{coding}"], chunked(MODS))))


@pytest.mark.parametrize("lines", [["chunked", "chunked"], ["gzip", "chunked"], ["chunked", "gzip"], ["chunked", "identity"]])
def test_fixB_duplicate_transfer_encoding_headers(monkeypatch, lines):
    response = real_response([XML] + [f"Transfer-Encoding: {v}" for v in lines], chunked(MODS))
    assert protocol_error(fetch_mods(monkeypatch, response))


@pytest.mark.parametrize("coding", ["chunked", "gzip, chunked", "xchunked"])
def test_fixB_transfer_encoding_plus_content_length(monkeypatch, coding):
    response = real_response([XML, f"Transfer-Encoding: {coding}", f"Content-Length: {len(MODS)}"], chunked(MODS))
    assert protocol_error(fetch_mods(monkeypatch, response))


def test_fixB_fixed_length_complete_and_truncated(monkeypatch):
    got = fetch_mods(monkeypatch, real_response([XML, "Content-Length: 12091"], MODS))
    assert got.body == MODS and accept_response("MODS", got) == "OK"
    got = fetch_mods(monkeypatch, real_response([XML, "Content-Length: 12191"], MODS))
    assert got == HttpResponse(status=0, failure="INCOMPLETE_READ")


def test_fixB_oversized_bodies_stay_bounded_and_framing_is_checked_first(monkeypatch):
    cap = MAX_BYTES["MODS"]
    big = b"x" * (cap + 10)
    streamed = fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: chunked"], chunked(big, 65536)))
    assert streamed.truncated and len(streamed.body) == cap + 1
    assert accept_response("MODS", streamed) == "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"
    declared = fetch_mods(monkeypatch, real_response([XML, f"Content-Length: {cap + 1}"], b""))
    assert declared.truncated and declared.body is None
    assert protocol_error(fetch_mods(monkeypatch, real_response([XML, "Transfer-Encoding: gzip, chunked"], chunked(big, 65536))))


def test_fixB_framing_agrees_with_the_real_transport_on_every_coding():
    codings = ["chunked", "Chunked", " chunked", "chunked ", "gzip, chunked", "xchunked", "identity", "", "chunked, chunked"]
    for coding in codings:
        response = real_response([XML, f"Transfer-Encoding:{coding}"], chunked(MODS))
        ours = sources.framing(list(response.headers.items()))
        assert (ours == sources.CHUNKED) is response.chunked, coding              # accepted only when the transport decodes it


def test_fixB_a_transport_that_disagrees_on_framing_fails_closed(monkeypatch):
    class Disagreeing:
        status = 200

        def __init__(self, headers, chunked_flag):
            self.headers, self.chunked = headers, chunked_flag

        def read(self, n):
            raise AssertionError("nothing may be read")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    for headers, flag in (({"Content-Type": "text/xml", "Transfer-Encoding": "chunked"}, False),
                          ({"Content-Type": "text/xml"}, True)):
        assert protocol_error(fetch_mods(monkeypatch, Disagreeing(headers, flag)))


@pytest.mark.parametrize("headers, reason", [
    ({"transfer-encoding": "gzip, chunked"}, "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"),
    ({"transfer-encoding": "xchunked"}, "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"),
    ({"transfer-encoding": "chunked", "content-length": "12091"}, "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"),
    ({"transfer-encoding": "chunked"}, "OK"),
])
def test_fixB_injected_transport_framing_is_validated(headers, reason):
    response = HttpResponse(200, {"content-type": "text/xml", **headers}, MODS)
    assert accept_response("MODS", response) == reason
    client = GovInfoClient(transport=lambda url, cap, timeout: response, clock=lambda: NOW, budget=1)
    fetched = client.fetch("MODS", META)
    assert (fetched.reason or "OK") == reason and client.remaining == 0
