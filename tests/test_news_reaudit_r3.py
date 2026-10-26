"""Regression tests for the third independent C13 re-audit: P4 duplication invariance of
``excluded_after_evaluation``.

Inputs available after T are counted, never used (I1, P7). An exact duplicate of an excluded input
must not change the complete serialized report (P4); genuinely distinct excluded inputs still count
separately. Equality is the canonical equality that already deduplicates admitted inputs.

REAL official components and C12 code; SYNTHETIC_TEST manual records, fund link and later copies.
"""
from datetime import timedelta
import itertools

import pytest

from news_support import NOW, TEST_POLICY, _no_network, claim, curate, records, retrieval  # noqa: F401
from test_news_macro_adapter import C12MacroEvaluator, decision, report as c12_report, T as MACRO_T
from test_news_qualification import edited_record, pi_record, replace
from test_news_remediation import E, approval_claim, correction, fund_claim
from traid.news import verify
from traid.news.models import DocketListing, ManualPassageVerification, OfficialEvidence, RecordPurpose, sha256_hex

FUTURE = NOW + timedelta(hours=1)
CUTS = {"before": FUTURE - timedelta(microseconds=1), "at": FUTURE, "after": FUTURE + timedelta(hours=1)}
N = "2024-00743"
(C1, CUR1), (C2, CUR2) = approval_claim(), fund_claim()
CLAIMS, CURATIONS = (C1, C2), (CUR1, CUR2)
FUND_NAME = next(r for r in records() if r.purpose is RecordPurpose.FUND_NAME)


def later_record(base, record_id, at=FUTURE):
    return ManualPassageVerification.model_validate({**base.model_dump(), "record_id": record_id, "verified_at": at, "recorded_at": at})


def listing(digest):
    return DocketListing(file_number="SR-NYSEARCA-2021-90", query_url="q", count=2, returned=2, pages_fetched=1, complete=True,
                         document_numbers=("2022-14310", "2024-00743"), retrieved_at=FUTURE, payload_digest=sha256_hex(digest))


def late_claim(text):
    return claim(text, received=FUTURE, source_id=text)


# category -> (where the input goes, ExcludedCounts field, two excluded inputs with different canonical identities)
CATEGORIES = {
    "claims": ("claims", "claims", (late_claim("SEC approved SR-NASDAQ-2023-016 again"), late_claim("A different later claim"))),
    "curations": ("curations", "curations", tuple(
        curate(C1, [("e", "REG_DOC", {"document_number": N})], [("p", "e", [("ACTION", "APPROVED")])], curated_at=FUTURE,
               curation_id=cid) for cid in ("cur-late-1", "cur-late-2"))),
    "fund_links": ("fund_links", "fund_links", tuple(
        E.fund_links[0].model_copy(update={"link_id": lid, "curated_at": FUTURE}) for lid in ("SYN-LINK-LATE-1", "SYN-LINK-LATE-2"))),
    "fr_metadata": ("fr_metadata", "fr_metadata",
                    (correction("2024-99999", of="2022-14310", at=FUTURE), correction("2024-99998", of="2022-14310", at=FUTURE))),
    "public_inspection": ("public_inspection", "public_inspection",
                          (pi_record("2024-01-16T08:45:00.000-05:00", at=FUTURE), pi_record("2024-01-16T13:45:00.000Z", at=FUTURE))),
    "docket_listings": ("docket_listings", "docket_listings", (listing("later-1"), listing("later-2"))),
    "html": ("html", "html", (retrieval(N, "GOVINFO_HTML", retrieved_at=FUTURE),
                              retrieval(N, "GOVINFO_HTML", retrieved_at=FUTURE + timedelta(seconds=1)))),
    "pdf": ("pdf", "pdf", (retrieval(N, "GOVINFO_PDF", retrieved_at=FUTURE),
                           retrieval(N, "GOVINFO_PDF", retrieved_at=FUTURE, data=b"%PDF-1.7 a later regeneration"))),
    "mods": ("mods", "mods", (retrieval(N, "GOVINFO_MODS", retrieved_at=FUTURE),
                              retrieval(N, "GOVINFO_MODS", retrieved_at=FUTURE + timedelta(seconds=1)))),
    "qualifying_records": ("manual_records", "manual_records",
                           (later_record(edited_record(N), "SYN-LATE-Q1"), later_record(edited_record(N), "SYN-LATE-Q2"))),
    "fund_name_records": ("manual_records", "manual_records",
                          (later_record(FUND_NAME, "SYN-LATE-NAME-1"), later_record(FUND_NAME, "SYN-LATE-NAME-2"))),
}


def report_json(where: str, extra: tuple, T, base_order=False) -> str:
    claims, curations, groups = CLAIMS, CURATIONS, {}
    if where == "claims":
        claims = claims + extra
    elif where == "curations":
        curations = curations + extra
    else:
        groups[where] = getattr(E, where) + extra
    ev = replace(E, **groups) if groups else E
    if base_order:                                                       # the admitted inputs reversed as well
        ev = OfficialEvidence.model_validate({k: tuple(reversed(getattr(ev, k))) for k in OfficialEvidence.model_fields
                                              if k != "schema_version"})
        claims, curations = tuple(reversed(claims)), tuple(reversed(curations))
    out = verify(claims=claims, curations=curations, evidence=ev, evaluation_time=T, policy=TEST_POLICY)
    return out.model_dump_json()


def counts(json_text: str, field: str) -> int:
    from traid.news.models import VerificationReport
    return getattr(VerificationReport.model_validate_json(json_text).excluded_after_evaluation, field)


def arrangements(items: tuple) -> set[tuple]:
    """Every order of the multiset (small), plus the duplicates interleaved: insertion order never matters."""
    return set(itertools.permutations(items))


def test_codex_case_one_versus_two_identical_future_fr_metadata_records():
    future = CATEGORIES["fr_metadata"][2][0]
    one = report_json("fr_metadata", (future,), NOW)
    two = report_json("fr_metadata", (future, future), NOW)
    assert two == one                                                    # pre-fix: fr_metadata 2 versus 1
    assert counts(one, "fr_metadata") == 1


@pytest.mark.parametrize("category", sorted(CATEGORIES))
@pytest.mark.parametrize("cut", sorted(CUTS))
def test_exact_duplicates_of_an_input_never_change_the_complete_report(category, cut):
    where, field, (x, _) = CATEGORIES[category]
    T = CUTS[cut]
    reference = report_json(where, (x,), T)
    for k in (2, 3, 5):
        assert report_json(where, (x,) * k, T) == reference, (category, cut, k)
    assert report_json(where, (x, x), T, base_order=True) == reference
    excluded = counts(reference, field)
    assert excluded == (1 if cut == "before" else 0), (category, cut)     # exact cutoff: available at T is admitted
    assert counts(report_json(where, (), T), field) == 0


@pytest.mark.parametrize("category", sorted(CATEGORIES))
def test_distinct_excluded_inputs_still_count_separately_whatever_the_multiplicity_and_order(category):
    where, field, (x, y) = CATEGORIES[category]
    assert x != y and x.model_dump_json() != y.model_dump_json()
    T = CUTS["before"]
    reference = report_json(where, (x, y), T)
    assert counts(reference, field) == 2
    for order in arrangements((x, x, y, y, y)):
        assert report_json(where, order, T) == reference, category
    assert counts(report_json(where, (y,), T), field) == 1


def test_fund_name_and_qualifying_records_are_counted_together_but_distinctly():
    q, name = CATEGORIES["qualifying_records"][2][0], CATEGORIES["fund_name_records"][2][0]
    T = CUTS["before"]
    reference = report_json("manual_records", (q, name), T)
    assert counts(reference, "manual_records") == 2
    for order in arrangements((q, q, name, name)):
        assert report_json("manual_records", order, T) == reference


def test_every_category_duplicated_at_once_at_every_cutoff():
    for cut, T in CUTS.items():
        single = {"claims": CLAIMS, "curations": CURATIONS}
        doubled = {"claims": CLAIMS, "curations": CURATIONS}
        groups1, groups2 = {}, {}
        for where, _, (x, y) in CATEGORIES.values():
            target1 = single if where in ("claims", "curations") else groups1
            target2 = doubled if where in ("claims", "curations") else groups2
            target1[where] = target1.get(where, getattr(E, where, ())) + (x, y)
            target2[where] = target2.get(where, getattr(E, where, ())) + (y, x, x, y, y)
        a = verify(claims=single["claims"], curations=single["curations"], evidence=replace(E, **groups1), evaluation_time=T,
                   policy=TEST_POLICY)
        b = verify(claims=doubled["claims"], curations=doubled["curations"], evidence=replace(E, **groups2), evaluation_time=T,
                   policy=TEST_POLICY)
        assert a.model_dump_json() == b.model_dump_json(), cut
        if cut == "before":
            assert a.excluded_after_evaluation.manual_records == 4 and a.excluded_after_evaluation.claims == 2


def test_decisions_facts_provenance_and_digests_are_unchanged_by_the_count_fix():
    """P7: adding a later input changes only the exclusion counts, as before the fix."""
    for category, (where, field, (x, _)) in CATEGORIES.items():
        with_later = report_json(where, (x, x), CUTS["before"])
        without = report_json(where, (), CUTS["before"])
        assert with_later.replace(f'"{field}":1', f'"{field}":0') == without, category


def test_c12_path_report_is_invariant_under_duplicated_excluded_news_inputs():
    """C12 inputs are point-in-time filtered by C12 itself; the shared news filter applies around them."""
    rep = c12_report()
    c, cur = decision("2026-09-16", "HOLD", at=MACRO_T)
    late = late_claim("A later macro claim")
    late_cur = curate(c, [("e", "FOMC_DECISION", {"board_date": "2026-09-16"})], [("p", "e", [("ACTION", "HOLD")])],
                      curated_at=MACRO_T + timedelta(hours=1), curation_id="cur-late")
    outputs = set()
    for k in (1, 2, 3):
        out = verify(claims=(c,) + (late,) * k, curations=(cur,) + (late_cur,) * k, evidence=OfficialEvidence(),
                     evaluation_time=MACRO_T, macro=C12MacroEvaluator(rep))
        assert out.excluded_after_evaluation.claims == 1 and out.excluded_after_evaluation.curations == 1
        outputs.add(out.model_dump_json())
    assert len(outputs) == 1
