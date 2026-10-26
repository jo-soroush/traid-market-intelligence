"""Regression tests for the seven defects confirmed by the independent C13 implementation audit.

REAL official components and REAL C12 code/fixtures; SYNTHETIC_TEST manual records and fund link
(no human record exists); SYN edits of real bytes where a test needs a later or altered copy.
Each test reproduces the audit's failure mode and checks the fail-closed, order-, duplication- and
context-independent behaviour required by the remediation.
"""
from datetime import datetime, timedelta, timezone
import decimal
from decimal import Decimal, localcontext
from http.client import HTTPException, IncompleteRead, LineTooLong, RemoteDisconnected
import itertools
import json
import re
import socket
import ssl

import pytest

from news_support import (  # noqa: F401  (autouse fixture)
    DOCS, NOW, TEST_POLICY, _no_network, body, claim, curate, official, records, retimed, retrieval,
)
from test_news_macro_adapter import (
    REAL, REVISED, AT, decision, fomc_time, latest_fomc, one, report as c12_report, run as macro_run, schedule, value,
)
from test_news_qualification import edited_record, pi_record, qualify, replace
from traid.news import verify
from traid.news.curation import normalize
from traid.news.macro_adapter import C12MacroEvaluator
from traid.news.models import (
    DEFAULT_POLICY, FactOutcome, FrMetadataRecord, ManualPassageVerification, OfficialEvidence, RecordPurpose,
    VerificationState, canonical_json, decimal_text,
)
import traid.news.sources as sources
from traid.news.sources import GovInfoClient, HttpResponse, http_get, parse_fr_document
from traid.news.text import html_text, normalize_passage

UTC = timezone.utc
S = VerificationState
E = official()
E_PAIR = official(("2024-00743", "2022-14310"))          # Fix 1: the approval and disapproval orders
E_ONE = official(("2024-00743",))                         # Fix 3/4 permutations
NASDAQ, ARCA = "SR-NASDAQ-2023-016", "SR-NYSEARCA-2021-90"


def run(c, *curations, T=NOW, ev=E, policy=TEST_POLICY, macro=None):
    report = verify(claims=(c,), curations=tuple(curations), evidence=ev, evaluation_time=T, policy=policy, macro=macro)
    return report.results[0]


def dump(x) -> str:
    return x.model_dump_json()


def states(result) -> dict:
    return {fr.frame_key: fr.state for fr in result.frames}


# ===================================================================== Fix 1: event identity collision
COLLIDE = "SEC disapproved SR-NASDAQ-2023-016 and SR-NYSEARCA-2021-90, and approved SR-NASDAQ-2023-016"


def nasdaq_arca(c, multi="a", single="b", *, order=(0, 1), prop_order=(0, 1), split=False, duplicate=False):
    """A two-subject DISAPPROVED event plus a one-subject APPROVED event, under caller-chosen ids."""
    events = [(multi, "REG_EVENT", {"subjects": (NASDAQ, ARCA), "action": "DISAPPROVED"}),
              (single, "REG_EVENT", {"subjects": (NASDAQ,), "action": "APPROVED"})]
    props = [("p-multi", multi, [("ACTION", "DISAPPROVED")]), ("p-single", single, [("ACTION", "APPROVED")])]
    if split:
        props += [("p-multi-2", multi, [("ACTION", "DISAPPROVED")])]
    events, props = [events[i] for i in order], [props[i] for i in prop_order] + props[2:]
    if duplicate:
        events, props = events + events, props + props[:1]
    return curate(c, events, props)


EXPECTED_FRAMES = {f"EVT:{NASDAQ}:APPROVED": S.CONFIRMED,              # 2024-00743 approval order
                   f"EVT:{NASDAQ}:DISAPPROVED": S.UNVERIFIED,          # no disapproval known: absence is never evidence
                   f"EVT:{ARCA}:DISAPPROVED": S.CONFIRMED}             # 2022-14310 disapproval order


def test_fix1_nasdaq_arca_generated_id_collision_loses_no_assertion():
    """The audit's case: a caller id equal to the old generated key "<id>#<subject>" overwrote the
    expanded Nasdaq DISAPPROVED assertion, leaving an unsupported CONFIRMED."""
    c = claim(COLLIDE)
    for multi, single in (("e", f"e#{NASDAQ}"), ("e", f"e#{ARCA}"), (f"x#{ARCA}", "x"), ("a", "b")):
        r = run(c, nasdaq_arca(c, multi, single), ev=E_PAIR)
        assert states(r) == EXPECTED_FRAMES, (multi, single)
        assert r.state is S.PARTIALLY_CONFIRMED, (multi, single)


def test_fix1_full_report_bytes_invariant_under_renaming_splits_duplicates_and_permutations():
    c = claim(COLLIDE)
    baseline = dump(run(c, nasdaq_arca(c), ev=E_PAIR))
    names = ["a", "e", f"e#{NASDAQ}", f"e#{ARCA}", f"#{NASDAQ}", NASDAQ]
    variants = 0
    for multi, single in itertools.permutations(names, 2):
        for order, prop_order in itertools.product(((0, 1), (1, 0)), repeat=2):
            for split, duplicate in ((False, False), (True, False), (False, True)):
                cur = nasdaq_arca(c, multi, single, order=order, prop_order=prop_order, split=split, duplicate=duplicate)
                assert dump(run(c, cur, ev=E_PAIR)) == baseline, (multi, single, order, prop_order, split, duplicate)
                variants += 1
    assert variants == len(names) * (len(names) - 1) * 12


def test_fix1_splitting_the_multi_subject_event_by_hand_is_the_same_claim():
    c = claim(COLLIDE)
    by_hand = curate(c, [(f"m#{NASDAQ}", "REG_EVENT", {"subjects": (NASDAQ,), "action": "DISAPPROVED"}),
                         ("m", "REG_EVENT", {"subjects": (ARCA,), "action": "DISAPPROVED"}),
                         (f"m#{ARCA}", "REG_EVENT", {"subjects": (NASDAQ,), "action": "APPROVED"})],
                     [("p1", f"m#{NASDAQ}", [("ACTION", "DISAPPROVED")]), ("p2", "m", [("ACTION", "DISAPPROVED")]),
                      ("p3", f"m#{ARCA}", [("ACTION", "APPROVED")])])
    assert dump(run(c, by_hand, ev=E_PAIR)) == dump(run(c, nasdaq_arca(c), ev=E_PAIR))


def test_fix1_distinct_declarations_bind_to_the_declared_event_only():
    """A declaration naming the caller id "e#..." must not attach to the expansion of "e"."""
    c = claim("SEC approved SR-NASDAQ-2023-016 on January 10, 2024 and approved SR-NASDAQ-2023-016")
    events = [("e", "REG_EVENT", {"subjects": (NASDAQ, ARCA), "action": "APPROVED"}),
              (f"e#{NASDAQ}", "REG_EVENT", {"subjects": (NASDAQ,), "action": "APPROVED"})]
    props = [("p1", "e", [("ACTION", "APPROVED"), ("DATE", "2024-01-10", "ORDERED_ON")]), ("p2", f"e#{NASDAQ}", [("ACTION", "APPROVED")])]
    undeclared = run(c, curate(c, events, props), ev=E_PAIR)
    assert undeclared.state is S.UNVERIFIED and undeclared.reasons[0].startswith("EVENT_ASSOCIATION_UNDETERMINED")
    renamed = [("x", *events[0][1:]), ("y", *events[1][1:])]
    renamed_props = [("p1", "x", props[0][2]), ("p2", "y", props[1][2])]
    assert dump(run(c, curate(c, renamed, renamed_props), ev=E_PAIR)) == dump(undeclared)
    declared = run(c, curate(c, events, props, distinct=(("e", f"e#{NASDAQ}"),)), ev=E_PAIR)
    assert dump(declared) == dump(run(c, curate(c, renamed, renamed_props, distinct=(("x", "y"),)), ev=E_PAIR))
    assert declared.state is S.CONFIRMED


# ===================================================================== Fix 2: decimal context independence
CONTEXTS = {
    "prec3": dict(prec=3),
    "prec28": dict(prec=28),
    "prec1_floor": dict(prec=1, rounding=decimal.ROUND_FLOOR),
    "prec2_traps": dict(prec=2, traps=[decimal.Inexact, decimal.Rounded, decimal.InvalidOperation]),
    "no_traps": dict(prec=5, traps=[]),
}


def under(context: dict, fn):
    with localcontext() as ctx:
        for k, v in context.items():
            if k == "traps":
                for signal in ctx.traps:
                    ctx.traps[signal] = signal in v
            else:
                setattr(ctx, k, v)
        return fn()


def macro_report_bytes(c, cur, rep, at):
    out = verify(claims=(c,), curations=(cur,), evidence=OfficialEvidence(), evaluation_time=at, macro=C12MacroEvaluator(rep))
    return dump(out)


def test_fix2_target_range_3_751_versus_3_75_under_precision_3_and_28():
    rep = c12_report()                                                    # built once, outside the contexts under test
    assert (rep.fomc.statement.target_lower_percent, rep.fomc.statement.target_upper_percent) == (Decimal("3.75"), Decimal("4.00"))
    c, cur = decision("2026-09-16", "RAISE", [("TARGET_RANGE", "3.751-4")])
    outputs = {name: under(ctx, lambda: macro_report_bytes(c, cur, rep, datetime(2026, 10, 21, 20, tzinfo=UTC)))
               for name, ctx in CONTEXTS.items()}
    assert len(set(outputs.values())) == 1, "the serialized report depends on the ambient decimal context"
    result = json.loads(outputs["prec3"])["results"][0]
    target = next(f for fr in result["frames"] for f in fr["facts"] if f["field"] == "TARGET_RANGE")
    assert target["asserted"] == "3.751-4" and target["outcome"] == "UNRESOLVED"     # never rounded to 3.75
    assert result["state"] == "PARTIALLY_CONFIRMED"


def test_fix2_derived_change_and_bls_values_are_compared_exactly_in_every_context():
    rep = c12_report()
    assert rep.fomc.range_change_since_previous.value.copy_abs() == Decimal("0.25")
    for asserted in ("0.2", "0.3", "0.251"):              # abs() under precision 1 used to round 0.25 to 0.2
        c, cur = decision("2026-09-16", "RAISE", [("CHANGE_SIZE", asserted, "DERIVED_COMPARISON")])
        outs = {under(ctx, lambda: macro_report_bytes(c, cur, rep, datetime(2026, 10, 21, 20, tzinfo=UTC))) for ctx in CONTEXTS.values()}
        assert len(outs) == 1 and json.loads(outs.pop())["results"][0]["state"] == "PARTIALLY_CONFIRMED", asserted
    bls = REVISED()
    for asserted, expected in (("337.1004", "UNVERIFIED"), ("337.10", "CONFIRMED"), ("336.9404", "UNVERIFIED")):
        c, cur = value("CUUR0000SA0", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", asserted)
        outs = {under(ctx, lambda: macro_report_bytes(c, cur, bls, AT)) for ctx in CONTEXTS.values()}
        assert len(outs) == 1, asserted
        assert json.loads(outs.pop())["results"][0]["state"] == expected, asserted


def test_fix2_normalization_digest_and_canonical_json_are_context_free():
    c = claim("CPI was 337.1004")
    cur = curate(c, [("e", "MACRO_VALUE", {"series": "CUUR0000SA0", "period": "2026-09", "scope": "AS_PUBLISHED_AT_SOME_RECEIPT"})],
                 [("p", "e", [("VALUE", "337.10040"), ("UNIT", "index")])])
    forms = {under(ctx, lambda: normalize(c, cur, lambda name: (None, "UNUSED")).form) for ctx in CONTEXTS.values()}
    assert len(forms) == 1 and '"337.1004"' in forms.pop()
    values = [Decimal("3.751"), Decimal("-0.0500"), Decimal("1E+3"), Decimal("123456789.123456789"), Decimal("-0")]
    texts = {under(ctx, lambda: canonical_json(values)) for ctx in CONTEXTS.values()}
    assert texts == {'["3.751","-0.05","1000","123456789.123456789","0"]'}
    for v in values:
        assert Decimal(decimal_text(v)) == v                                  # exact round trip, never rounded


def test_fix2_oversized_exponents_are_invalid_values_not_huge_strings():
    c = claim("CPI was 1E+999999999")
    for bad in ("1E+999999999", "1E-999999999", "1" * 65):
        cur = curate(c, [("e", "MACRO_VALUE", {"series": "CUUR0000SA0", "period": "2026-09", "scope": "AS_PUBLISHED_AT_SOME_RECEIPT"})],
                     [("p", "e", [("VALUE", bad)])])
        r = run(c, cur)
        assert r.state is S.UNVERIFIED and r.reasons == ("CURATION_INVALID:VALUE:VALUE",), bad


# ===================================================================== Fix 3: cross-document corrections
CORRECTION_AT = datetime(2026, 10, 23, 23, tzinfo=UTC)


def correction(number: str, of: str = "2024-00743", at: datetime = CORRECTION_AT) -> FrMetadataRecord:
    """SYN: a correcting document's FR metadata, built from the real 2024-00743 payload shape."""
    raw = json.loads(body("2024-00743", "FEDERAL_REGISTER_JSON"))
    payload = dict(raw, document_number=number, correction_of=of, corrections=[], title=f"Correction to {of}")
    record = parse_fr_document(json.dumps(payload).encode(), requested=number,
                               source_url=f"https://www.federalregister.gov/api/v1/documents/{number}.json", retrieved_at=at)
    assert isinstance(record, FrMetadataRecord), record
    return record


def approval_claim(received=datetime(2026, 10, 23, 22, tzinfo=UTC)):
    c = claim("FR 2024-00743 approved SR-NASDAQ-2023-016", received=received)
    return c, curate(c, [("e", "REG_DOC", {"document_number": "2024-00743"})], [("p", "e", [("ACTION", "APPROVED"), ("SUBJECT", NASDAQ)])])


def test_fix3_correction_published_as_another_document_disqualifies_the_original():
    assert run(*approval_claim()).state is S.CONFIRMED
    own = next(m for m in E.fr_metadata if m.document_number == "2024-00743")
    assert own.corrections == () and own.correction_of is None             # the original's own metadata never mentions it
    for number in ("C1-2024-00743", "2024-99999"):
        ev = replace(E, fr_metadata=E.fr_metadata + (correction(number),))
        r = run(*approval_claim(), ev=ev)
        assert r.state is S.UNVERIFIED, number
        assert "DOCUMENT_NOT_QUALIFIED:CORRECTION_CONTENT_UNVERIFIED" in r.reasons, number


def test_fix3_before_exactly_at_and_after_the_correction_availability():
    ev = replace(E, fr_metadata=E.fr_metadata + (correction("C1-2024-00743"),))
    c, cur = approval_claim()
    before = run(c, cur, T=CORRECTION_AT - timedelta(microseconds=1), ev=ev)
    assert before.state is S.CONFIRMED and before.excluded_after_evaluation.fr_metadata == 1
    assert dump(before) == dump(run(c, cur, T=CORRECTION_AT - timedelta(microseconds=1), ev=E)).replace(
        '"fr_metadata":0', '"fr_metadata":1')                             # I3: only the exclusion count differs
    for T in (CORRECTION_AT, CORRECTION_AT + timedelta(hours=1)):
        assert "DOCUMENT_NOT_QUALIFIED:CORRECTION_CONTENT_UNVERIFIED" in run(c, cur, T=T, ev=ev).reasons, T


def test_fix3_correction_result_is_independent_of_record_order_and_duplication():
    fix = (correction("C1-2024-00743"), correction("2024-99999", at=CORRECTION_AT + timedelta(minutes=5)))
    c, cur = approval_claim()
    outputs = set()
    for order in itertools.permutations(E_ONE.fr_metadata + fix):
        outputs.add(dump(run(c, cur, ev=replace(E_ONE, fr_metadata=order + order[:2]))))
    assert len(outputs) == 1 and "CORRECTION_CONTENT_UNVERIFIED" in outputs.pop()


def test_fix3_corrections_of_other_documents_and_the_correction_itself():
    ev = replace(E, fr_metadata=E.fr_metadata + (correction("C1-2022-14310", of="2022-14310"),))
    assert run(*approval_claim(), ev=ev).state is S.CONFIRMED             # unrelated correction: 2024-00743 unaffected
    assert qualify("2022-14310", ev).reason is None                       # the helper passes no cross-document corrections
    c = claim("FR C1-2022-14310 is a document")
    corr = verify(claims=(c,), curations=(), evidence=ev, evaluation_time=NOW, policy=TEST_POLICY)
    assert corr.results[0].state is S.UNVERIFIED                         # nothing is ever qualified from a correction


# ===================================================================== Fix 4: adverse later source records
LATER = datetime(2026, 10, 23, 21, tzinfo=UTC)


def revision_with_record(absent_checks, record_id="SYN-REV-LATER", at=LATER):
    """SYN: a later PDF retrieval with different bytes and its own (synthetic) record, identical passages."""
    pdf = retrieval("2024-00743", "GOVINFO_PDF", retrieved_at=at, data=b"%PDF-1.7 regenerated")
    rec = ManualPassageVerification.model_validate({**edited_record("2024-00743").model_dump(), "record_id": record_id,
                                                    "pdf_sha256": pdf.sha256, "pdf_retrieved_at": at, "verified_at": at,
                                                    "recorded_at": at, "absent_checks": list(absent_checks)})
    return pdf, rec


def with_revision(ev, absent_checks, **kw):
    pdf, rec = revision_with_record(absent_checks, **kw)
    return replace(ev, pdf=ev.pdf + (pdf,), manual_records=ev.manual_records + (rec,))


ADVERSE = {
    "second_operative_rendered": ["NO_SECOND_HEADING", "NO_SECOND_TERMINATOR", "SECOND_OPERATIVE_SENTENCE_RENDERED"],
    "contradictory_checks": ["NO_SECOND_OPERATIVE_SENTENCE", "NO_SECOND_HEADING", "NO_SECOND_TERMINATOR",
                             "SECOND_OPERATIVE_SENTENCE_RENDERED"],
    "missing_confirmation": ["NO_SECOND_OPERATIVE_SENTENCE", "NO_SECOND_HEADING"],
}


@pytest.mark.parametrize("case", sorted(ADVERSE))
def test_fix4_later_pdf_verification_disqualifier_is_not_hidden_by_revision_classification(case):
    ev = with_revision(E, ADVERSE[case])
    assert qualify("2024-00743", ev).reason == "UNCLASSIFIED_SEC_NOTICE"
    r = run(*approval_claim(), ev=ev)
    assert r.state is S.UNVERIFIED and "DOCUMENT_NOT_QUALIFIED:UNCLASSIFIED_SEC_NOTICE" in r.reasons
    clean = with_revision(E, ["NO_SECOND_OPERATIVE_SENTENCE", "NO_SECOND_HEADING", "NO_SECOND_TERMINATOR"])
    q = qualify("2024-00743", clean)
    assert q.reason is None and "NONMATERIAL_REVISION:2024-00743" in q.limitations      # the control still qualifies


def test_fix4_later_pdf_record_cutoff_boundaries_and_permutations():
    ev = with_revision(E_ONE, ADVERSE["second_operative_rendered"])
    c, cur = approval_claim(received=LATER - timedelta(hours=1))
    assert run(c, cur, T=LATER - timedelta(microseconds=1), ev=ev).state is S.CONFIRMED     # not yet known: no lookahead
    for T in (LATER, LATER + timedelta(days=1)):
        assert run(c, cur, T=T, ev=ev).state is S.UNVERIFIED
    outputs = set()
    for pdfs in itertools.permutations(ev.pdf):
        for recs in itertools.permutations(ev.manual_records):
            outputs.add(dump(run(c, cur, ev=replace(ev, pdf=pdfs + pdfs, manual_records=recs + recs[:1]))))
    assert len(outputs) == 1


def html_with_issue(issue: str) -> bytes:
    raw = body("2024-00743", "GOVINFO_HTML")
    changed = raw.replace(b"Volume 89, Number 11 (", f"Volume 89, Number {issue} (".encode(), 1)
    assert changed != raw
    return changed


@pytest.mark.parametrize("earlier_is_bad", [False, True])
def test_fix4_inconsistent_html_issue_number_in_any_copy_fails_closed(earlier_is_bad):
    good = retrieval("2024-00743", "GOVINFO_HTML")
    bad = retrieval("2024-00743", "GOVINFO_HTML", retrieved_at=LATER if not earlier_is_bad else good.retrieved_at - timedelta(hours=1),
                    data=html_with_issue("12"))
    ev = replace(E_ONE, html=E_ONE.html + (bad,))
    assert qualify("2024-00743", ev).reason == "PAGE_HEADER_MISMATCH:ISSUE"
    outputs = {dump(run(*approval_claim(), ev=replace(ev, html=order))) for order in itertools.permutations(ev.html)}
    assert len(outputs) == 1 and "PAGE_HEADER_MISMATCH:ISSUE" in outputs.pop()
    if not earlier_is_bad:
        early = approval_claim(received=LATER - timedelta(hours=1))
        assert run(*early, T=LATER - timedelta(microseconds=1), ev=ev).state is S.CONFIRMED
        assert run(*early, T=LATER, ev=ev).state is S.UNVERIFIED


def test_fix4_every_public_inspection_record_must_match_the_filed_line():
    first = pi_record("2024-01-16T08:45:00.000-05:00")
    same_instant_other_offset = pi_record("2024-01-16T13:45:00.000Z", at=first.retrieved_at + timedelta(hours=1))
    assert first.filed_at == same_instant_other_offset.filed_at
    assert qualify("2024-00743", replace(E, public_inspection=(first,))).reason is None
    for order in itertools.permutations((first, same_instant_other_offset)):
        assert qualify("2024-00743", replace(E, public_inspection=order)).reason == "CONFLICTING_OFFICIAL_EVIDENCE:FILED_LINE"


def test_fix4_smallest_reason_when_several_records_fail():
    pdf2, rec2 = revision_with_record(ADVERSE["second_operative_rendered"], record_id="SYN-REV-A")
    pdf3, rec3 = revision_with_record(["NO_SECOND_OPERATIVE_SENTENCE", "NO_SECOND_HEADING", "NO_SECOND_TERMINATOR"],
                                      record_id="SYN-REV-B", at=LATER + timedelta(hours=1))
    rec3 = ManualPassageVerification.model_validate({**rec3.model_dump(), "passages": [
        {**p.model_dump(), "fr_printed_page": 40000} if p.kind.value == "TERMINATOR" else p.model_dump() for p in rec3.passages]})
    pdf3 = pdf3.model_copy(update={"sha256": "b" * 64})
    rec3 = rec3.model_copy(update={"pdf_sha256": "b" * 64})
    ev = replace(E_ONE, pdf=E_ONE.pdf + (pdf2, pdf3), manual_records=E_ONE.manual_records + (rec2, rec3))
    reasons = {qualify("2024-00743", replace(ev, manual_records=order)).reason for order in itertools.permutations(ev.manual_records)}
    assert reasons == {"PASSAGE_OUTSIDE_DOCUMENT_PAGES"}                  # smaller than UNCLASSIFIED_SEC_NOTICE


def test_fix4_two_different_records_under_one_id_are_never_collapsed():
    base = edited_record("2024-00743")
    adverse = base.model_copy(update={"absent_checks": tuple(base.absent_checks) + ("SECOND_OPERATIVE_SENTENCE_RENDERED",)})
    retimed_twin = base.model_copy(update={"recorded_at": base.recorded_at + timedelta(minutes=1)})
    for other in (adverse, retimed_twin):
        reasons = {qualify("2024-00743", replace(E_ONE, manual_records=order)).reason
                   for order in itertools.permutations((base, other))}
        assert reasons == {"CONFLICTING_MANUAL_VERIFICATIONS"}


# ===================================================================== Fix 5: fund provenance
def fund_claim(subject="FUND:IBIT", text="SEC approved the rule change to list IBIT"):
    c = claim(text)
    return c, curate(c, [("e", "REG_EVENT", {"subjects": (subject,), "action": "RULE_CHANGE_APPROVED"})],
                     [("p", "e", [("ACTION", "RULE_CHANGE_APPROVED")])])


def test_fix5_fund_resolution_references_are_accessible_in_the_evidence():
    r = run(*fund_claim())
    assert r.state is S.CONFIRMED
    (frame,) = r.frames
    (res,) = frame.fund_resolutions
    link = next(l for l in E.fund_links if l.link_id == res.link_id)                  # the link exists in the inputs
    assert (res.file_number, res.name_in_document, res.ticker, res.cik, res.sro, res.document_number) == \
        (link.file_number, link.name_in_document, link.ticker, link.cik, link.sro, link.document_number)
    assert res.identity_evidence == link.identity_evidence and res.link_curated_at == link.curated_at
    assert frame.frame_key == f"EVT:{res.file_number}:APPROVED"                      # the frame is about the resolved file
    name_record = next(m for m in E.manual_records if m.record_id == res.name_passage.manual_record_id)
    assert name_record.purpose is RecordPurpose.FUND_NAME and name_record.record_id == link.name_record_id
    assert name_record.qualifying_record_id == res.qualifying_record_id
    qualifying = next(m for m in E.manual_records if m.record_id == res.qualifying_record_id)
    assert qualifying.purpose is RecordPurpose.QUALIFYING and qualifying.document_number == res.document_number
    assert qualify(res.document_number, E).document.qualifying_record_id == res.qualifying_record_id
    assert normalize_passage(res.name_in_document) in res.name_passage.normalized_text
    assert res.name_passage.normalized_text == normalize_passage(name_record.passages[0].text)
    html = min((h for h in E.html if h.document_number == res.document_number), key=lambda h: (h.retrieved_at, h.sha256))
    page, offset = res.name_passage.html_location
    text = html_text(html.body.decode("utf-8"))
    assert text[offset:offset + len(res.name_passage.normalized_text)] == res.name_passage.normalized_text
    assert res.available_at == max(link.curated_at, link.identity_evidence.received_timestamp, name_record.available_at,
                                   qualify(res.document_number, E).document.available_at)


def test_fix5_ticker_name_and_spelling_variants_serialize_identically():
    outputs = set()
    for subject in ("FUND:IBIT", "FUND:iShares Bitcoin Trust", "FUND:iShares   Bitcoin Trust"):
        c, cur = fund_claim(subject, text="SEC approved the rule change")
        outputs.add(dump(run(c, cur)))
    assert len(outputs) == 1


def test_fix5_stable_under_link_permutation_and_duplication():
    c, cur = fund_claim()
    base = dump(run(c, cur))
    twin = E.fund_links[0].model_copy(update={"link_id": "SYN-LINK-IBIT-COPY"})
    outputs = set()
    for links in itertools.permutations(E.fund_links + E.fund_links + (twin,)):
        outputs.add(dump(run(c, cur, ev=replace(E, fund_links=links))))
    assert len(outputs) == 1
    (res_ids,) = {tuple(r.link_id for r in fr.fund_resolutions) for fr in run(c, cur, ev=replace(E, fund_links=E.fund_links + (twin,))).frames}
    assert res_ids == ("SYN-LINK-IBIT", "SYN-LINK-IBIT-COPY")                         # every link relied on is shown
    assert dump(run(c, cur, ev=replace(E, fund_links=E.fund_links + E.fund_links))) == base


def test_fix5_no_resolution_evidence_when_the_fund_does_not_resolve():
    at = datetime(2024, 1, 17, 12, tzinfo=UTC)
    c, cur = fund_claim()
    c = claim(c.text, received=at)
    cur = cur.model_copy(update={"claim_id": c.claim_id, "curated_at": at})
    late = run(c, cur, T=datetime(2024, 1, 18, tzinfo=UTC), ev=retimed(at, link_at=datetime(2026, 10, 23, tzinfo=UTC)))
    assert late.reasons == ("FUND_LINK_NOT_AVAILABLE_AT_T",) and all(fr.fund_resolutions == () for fr in late.frames)
    production = run(*fund_claim(), policy=DEFAULT_POLICY)
    assert production.state is S.UNVERIFIED and all(fr.fund_resolutions == () for fr in production.frames)


def test_fix5_document_subject_fact_carries_resolution_too():
    c = claim("FR 2023-21948 instituted proceedings on IBIT")
    cur = curate(c, [("e", "REG_DOC", {"document_number": "2023-21948"})],
                 [("p", "e", [("ACTION", "INSTITUTED_PROCEEDINGS"), ("SUBJECT", "FUND:IBIT")])])
    r = run(c, cur)
    assert r.state is S.CONFIRMED
    assert [x.link_id for x in r.frames[0].fund_resolutions] == ["SYN-LINK-IBIT"]


# ===================================================================== Fix 6: C12 selectors
def resolve_selector(report, path: str):
    """Walk a C12 field path on the real report; every segment must be a declared model field."""
    obj = report
    for part in path.split("."):
        m = re.fullmatch(r"([a-z_]+)(?:\[([^\]]+)\])?", part)
        assert m is not None, path
        assert m.group(1) in type(obj).model_fields, (path, m.group(1), type(obj).__name__)
        obj = getattr(obj, m.group(1))
        if m.group(2) is not None:
            key = m.group(2)
            obj = obj[int(key)] if key.isdigit() else next(x for x in obj if x.series_id == key)
        assert obj is not None, path
    return obj


def selectors(result) -> set[str]:
    return {c.c12_field_path for fr in result.frames for f in fr.facts for c in f.citations if c.c12_field_path}


def test_fix6_target_range_cites_the_real_lower_and_upper_fields():
    rep = c12_report()
    r = macro_run(*decision("2026-09-16", "RAISE", [("TARGET_RANGE", "3.75-4.00")]), rep)
    target = next(f for fr in r.frames for f in fr.facts if f.field == "TARGET_RANGE")
    paths = {c.c12_field_path for c in target.citations}
    assert paths == {"fomc.statement.target_lower_percent", "fomc.statement.target_upper_percent"}
    assert [resolve_selector(rep, p) for p in sorted(paths)] == [Decimal("3.75"), Decimal("4.00")]
    old = macro_run(*decision("2026-07-29", "MAINTAIN", [("TARGET_RANGE", "3.50-3.75")]), rep)
    assert {"fomc.previous_statement.target_lower_percent", "fomc.previous_statement.target_upper_percent"} <= selectors(old)


def test_fix6_every_emitted_selector_resolves_on_the_real_c12_report():
    fomc = c12_report()
    at = datetime(2026, 10, 28, 19, tzinfo=UTC)
    timed = c12_report(at=at, schedules=(fomc_time(),))
    c40 = claim("The FOMC statement is due at 2pm EDT on Oct 28", received=at - timedelta(hours=1))
    c40_cur = curate(c40, [("s", "FOMC_SCHEDULE", {"meeting_start": "2026-10-27", "meeting_end": "2026-10-28"})],
                     [("p", "s", [("SCHEDULED_ON", "2026-10-27/2026-10-28"), ("ANNOUNCEMENT_TIME", "2026-10-28T14:00:00-04:00")])])
    bls = REVISED()
    se = next(s for s in bls.series if s.series_id == "CUUR0000SA0")
    runs = [
        (fomc, macro_run(*decision("2026-09-16", "RAISE", [("TARGET_RANGE", "3.75-4.00"), ("CHANGE_SIZE", "0.25", "STATED_IN_DECISION")]), fomc)),
        (fomc, macro_run(*decision("2026-09-16", "RAISE", [("CHANGE_SIZE", "0.25", "DERIVED_COMPARISON")]), fomc)),
        (fomc, macro_run(*decision("2026-07-29", "MAINTAIN", [("TARGET_RANGE", "3.50-3.75")]), fomc)),
        (fomc, macro_run(*one("FOMC_CURRENT_RANGE", {}, [("TARGET_RANGE", "3.75-4.00")]), fomc)),
        (fomc, macro_run(*latest_fomc("2026-07-29"), fomc)),
        (fomc, macro_run(*schedule(extra=[("PROJECTIONS", "true" if fomc.fomc.next_meeting.projections else "false")]), fomc)),
        (timed, macro_run(c40, c40_cur, timed, at=at)),
        (bls, macro_run(*value("CUUR0000SA0", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "337.100", se.unit), bls, at=AT)),
        (bls, macro_run(*value("CUUR0000SA0", "2026-09", "AS_PUBLISHED_AT_SOME_RECEIPT", "336.940"), bls, at=AT)),
        (bls, macro_run(*value("CUUR0000SA0", "2026-08", "AS_PUBLISHED_AT_SOME_RECEIPT", str(se.previous_known.value)), bls, at=AT)),
        (bls, macro_run(*value("CUUR0000SA0", "2026-09", "CURRENT", "337.100"), bls, at=AT)),
        (bls, macro_run(*one("MACRO_VALUE", {"series": "CUUR0000SA0", "period": "2026-09", "scope": "AS_PUBLISHED_AT_SOME_RECEIPT"},
                             [("VALUE", "337.100"), ("PRELIMINARY", "true" if se.preliminary else "false")], at=AT), bls, at=AT)),
    ]
    emitted = set()
    for rep, result in runs:
        for path in selectors(result):
            resolve_selector(rep, path)
            emitted.add(re.sub(r"\[[A-Z0-9]+\]", "[SID]", re.sub(r"\[\d+\]", "[i]", path)))
    assert emitted == {
        "fomc.statement.action", "fomc.statement.target_lower_percent", "fomc.statement.target_upper_percent",
        "fomc.statement.stated_change_percentage_points", "fomc.range_change_since_previous",
        "fomc.previous_statement.action", "fomc.previous_statement.target_lower_percent",
        "fomc.previous_statement.target_upper_percent", "fomc.statement", "fomc.previous_statement", "fomc.next_meeting",
        "fomc.next_meeting.projections", "fomc.expected_announcement_at",
        "series[SID].unit", "series[SID].known_value", "series[SID].revisions[i]", "series[SID].previous_known",
        "series[SID].revisions", "series[SID].preliminary",
    }
    assert not any("target_range" in p for p in emitted)


def test_fix6_adapter_source_names_no_selector_outside_the_c12_models():
    from traid.macro.evidence import FomcEvidence, MacroEvidenceReport, SeriesEvidence
    from traid.macro.models import FomcMeeting, FomcStatement
    src = (sources.__file__.replace("sources.py", "macro_adapter.py"))
    text = open(src, encoding="utf-8").read()
    fields = set(MacroEvidenceReport.model_fields) | set(FomcEvidence.model_fields) | set(SeriesEvidence.model_fields) \
        | set(FomcStatement.model_fields) | set(FomcMeeting.model_fields)
    for literal in re.findall(r'(?:"|\{path\})((?:\.[a-z_]+)+)(?:"|\})', text) + re.findall(r'"(fomc(?:\.[a-z_]+)*)"', text):
        for segment in literal.strip(".").split("."):
            assert segment in fields, (literal, segment)


# ===================================================================== Fix 7: interrupted HTTP reads
class _Response:
    def __init__(self, reads, headers=None, status=200):
        self._reads = list(reads)
        self.status = status
        self.headers = headers or {"Content-Type": "application/pdf"}

    def read(self, n):
        item = self._reads.pop(0) if self._reads else b""
        if isinstance(item, BaseException):
            raise item
        return item

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_opener(monkeypatch, response_or_error):
    seen = {}

    class Opener:
        def open(self, request, timeout):
            seen["url"], seen["timeout"] = request.full_url, timeout
            if isinstance(response_or_error, BaseException):
                raise response_or_error
            return response_or_error

    def build(*handlers):
        seen["handlers"] = handlers
        return Opener()
    monkeypatch.setattr(sources, "build_opener", build)
    return seen


URL = "https://www.govinfo.gov/content/pkg/FR-2024-01-17/pdf/2024-00743.pdf"


@pytest.mark.parametrize("error, failure", [
    (IncompleteRead(b"%PDF-partial", 1000), "INCOMPLETE_READ"),
    (LineTooLong("chunk size"), "HTTP_PROTOCOL_ERROR"),
    (HTTPException("bad chunk"), "HTTP_PROTOCOL_ERROR"),
    (ConnectionResetError("reset"), "CONNECTION_FAILED"),
    (ssl.SSLError("bad record mac"), "CONNECTION_FAILED"),
])
def test_fix7_interrupted_body_reads_discard_partial_bytes(monkeypatch, error, failure):
    seen = fake_opener(monkeypatch, _Response([b"%PDF-1.7 first chunk", error]))
    response = http_get(URL, cap=1024, timeout=5.0)
    assert response == HttpResponse(status=0, failure=failure) and response.body is None
    assert any(isinstance(h, sources._NoRedirect) for h in seen["handlers"])          # no-redirect policy kept
    assert sources.accept_response("PDF", response) == f"SOURCE_UNAVAILABLE:{failure}"


def test_fix7_timeouts_and_connection_level_failures(monkeypatch):
    fake_opener(monkeypatch, _Response([b"x", socket.timeout("read timed out")]))
    assert http_get(URL, cap=1024, timeout=5.0) == HttpResponse(status=0, timed_out=True)
    fake_opener(monkeypatch, RemoteDisconnected("closed without response"))
    assert http_get(URL, cap=1024, timeout=5.0) == HttpResponse(status=0, failure="HTTP_PROTOCOL_ERROR")
    fake_opener(monkeypatch, _Response([b"x" * 2048]))                                 # bound still enforced
    assert http_get(URL, cap=1024, timeout=5.0).truncated is True


@pytest.mark.parametrize("error, reason", [
    (IncompleteRead(b"partial", 10), "SOURCE_UNAVAILABLE:INCOMPLETE_READ"),
    (RemoteDisconnected("gone"), "SOURCE_UNAVAILABLE:HTTP_PROTOCOL_ERROR"),
    (ConnectionAbortedError("aborted"), "SOURCE_UNAVAILABLE:CONNECTION_FAILED"),
    (TimeoutError("slow"), "SOURCE_UNAVAILABLE:TIMEOUT"),
])
def test_fix7_client_returns_a_deterministic_unavailable_outcome(error, reason):
    def transport(url, cap, timeout):
        raise error
    meta = next(m for m in E.fr_metadata if m.document_number == "2024-00743")
    client = GovInfoClient(transport=transport, clock=lambda: NOW, budget=2)
    first, second = client.fetch("PDF", meta), client.fetch("PDF", meta)
    assert first == second and first.record is None and first.reason == reason
    assert client.remaining == 0                                                        # counted, never retried


# ===================================================================== production stays fail-closed
def test_production_policy_keeps_every_remediation_claim_unverified():
    """No human record exists: under the default policy no ETF claim above is concluded, whatever the fixes."""
    c = claim(COLLIDE)
    claims = [(c, nasdaq_arca(c, "e", f"e#{NASDAQ}")), approval_claim(), fund_claim()]
    evidence = [E, replace(E, fr_metadata=E.fr_metadata + (correction("C1-2024-00743"),)),
                with_revision(E, ADVERSE["second_operative_rendered"])]
    for ev in evidence:
        for c, cur in claims:
            r = run(c, cur, ev=ev, policy=DEFAULT_POLICY)
            assert r.state is S.UNVERIFIED
            assert all(f.outcome is FactOutcome.UNRESOLVED for fr in r.frames for f in fr.facts)
            assert all(fr.fund_resolutions == () for fr in r.frames)
