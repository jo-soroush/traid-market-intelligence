"""A category remark ("C10 evidence is described in E004.") may name as its textual source only eligible cited evidence of
that same category. Complete-response tests on the shared T1 fixture: E004 C10 flow, E009 C12 macro, E007 C11 whale
aggregate, N001 a C13 claim; refs[] always holds the evidence, so only the textual suffix is under test."""
import pytest

from test_ai_default_deny import claim_put
from test_ai_narrative import FLOW, FUNDING, MACRO, put, verdict
from test_ai_validation import T1_REQ, base, ids

C11 = ids(T1_REQ, category="C11")[0]
CLAIM = T1_REQ["assessed_claims"][0]
CLAIM_ID, FACT_ID = CLAIM["claim_id"], CLAIM["frames"][0]["facts"][0]["fact_id"]
OTHER = T1_REQ["assessed_claims"][1]
OTHER_ID, OTHER_FACT = OTHER["claim_id"], OTHER["frames"][0]["facts"][0]["fact_id"]
SRC = "SOURCE_NOT_EVIDENCED"
BOTH = [FLOW, MACRO]


@pytest.mark.parametrize("statement,refs", [
    (f"C10 evidence is described in {MACRO}.", BOTH),                 # the audit cases: a C12 source for a C10 remark
    (f"C12 evidence is described in {FLOW}.", BOTH),                  # and the reverse
    (f"C10 evidence is described in {C11}.", [FLOW, C11]),
    (f"C11 evidence is described in {FLOW}.", [FLOW, C11]),
    (f"C11 evidence is described in {MACRO}.", [C11, MACRO]),
    (f"C12 evidence is described in {C11}.", [MACRO, C11]),
])
def test_a_category_remark_cannot_name_another_categorys_evidence(statement, refs):
    assert verdict(put(statement, refs)) == SRC, statement


def test_one_wrong_source_among_right_ones_is_not_accepted():
    # "and" starts a new clause, which is then not an approved construction on its own
    assert verdict(put(f"C10 evidence is described in {FUNDING} and {MACRO}.", [FLOW, FUNDING, MACRO])) != "VALID"
    assert verdict(put(f"C10 evidence is described in {FUNDING} in {MACRO}.", [FLOW, FUNDING, MACRO])) == SRC


def test_a_c13_remark_cannot_name_items_or_unrelated_claims():
    assert verdict(claim_put(CLAIM_ID, f"C13 evidence is described in {FLOW}.", [FLOW])) == SRC
    assert verdict(claim_put(CLAIM_ID, f"C13 evidence is described in {OTHER_ID}.", [OTHER_ID])) == SRC
    assert verdict(claim_put(CLAIM_ID, f"C13 evidence is described in {OTHER_FACT}.", [OTHER_FACT])) == SRC
    assert verdict(claim_put(CLAIM_ID, f"C10 evidence is described in {CLAIM_ID}.", [FLOW])) == SRC


@pytest.mark.parametrize("statement,refs", [
    (f"C10 evidence is described in {FLOW}.", BOTH), (f"C12 evidence is described in {MACRO}.", BOTH),
    (f"C11 evidence is described in {C11}.", [FLOW, C11]), ("C10 evidence is described.", BOTH),
    (f"C10 evidence is described in {FLOW}.", [FLOW, FUNDING]),
    (f"C10 evidence is described in the cited item.", BOTH),
])
def test_a_category_remark_may_name_its_own_categorys_evidence(statement, refs):
    assert verdict(put(statement, refs)) == "VALID", statement


def test_c13_remarks_keep_claim_and_fact_ownership():
    assert verdict(claim_put(CLAIM_ID, f"C13 evidence is described in {CLAIM_ID}.", [])) == "VALID"
    assert verdict(claim_put(CLAIM_ID, f"C13 evidence is described in {FACT_ID}.", [FACT_ID])) == "VALID"
    assert verdict(claim_put(CLAIM_ID, "C13 evidence is described.", [])) == "VALID"


def test_generic_evidence_remarks_keep_their_established_source_behaviour():
    for src in (FLOW, MACRO):
        out = put(f"The evidence at the evaluation time is described in {src}.", BOTH)
        assert verdict(out) == "VALID", src
    assert verdict(put("The evidence at the evaluation time is described in C12.", BOTH)) == SRC   # no category word


def test_category_remarks_in_other_sections_follow_the_same_rule():
    for section, refs in (("uncertainty", BOTH), ("context", [MACRO, C11])):
        bad = put(f"C12 evidence is described in {FLOW}.", list(dict.fromkeys(refs + [FLOW])), section)
        assert verdict(bad) in (SRC, "CONTEXT_REFERENCE_INVALID"), section
    out = base()
    out["anchor_assessments"][3]["statement"] += f" C12 evidence is described in {FLOW}."
    out["anchor_assessments"][3]["evidence_ids"] = BOTH
    assert verdict(out) == SRC
    out["anchor_assessments"][3]["statement"] = out["anchor_assessments"][3]["statement"].replace(
        f"C12 evidence is described in {FLOW}", f"C10 evidence is described in {FLOW}")
    assert verdict(out) == "VALID"
