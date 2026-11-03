"""R1: an optional source or category suffix may never attribute an assertion to something other than the evidence
that supports it. Complete-response tests on the shared T1/T2 fixtures (E004 flow BUY_DOMINANT, E005 funding
LONGS_PAY_SHORTS, E001 direction, E006 regime; C12 owns none of the C10 observations)."""
import pytest

from test_ai_default_deny import CPI3, FOMC, claim_put
from test_ai_narrative import DIRECTION, FLOW, FUNDING, MACRO, REGIME, VOL, put, verdict
from test_ai_validation import T1_REQ, T2_REQ, T2_SEL, base, ids

SRC = "SOURCE_NOT_EVIDENCED"
C11 = ids(T1_REQ, category="C11")[0]
ALL = [FLOW, FUNDING, DIRECTION, REGIME, VOL, MACRO, C11]
TIME = next(t["value"] for i in T1_REQ["structured"] if i["evidence_id"] == FLOW for t in i["times"])


@pytest.mark.parametrize("statement", [
    f"The cited funding state is LONGS_PAY_SHORTS in {FLOW}.",
    f"The cited flow state is BUY_DOMINANT in {FUNDING}.",
    "Funding indicates longs pay shorts in C12.",
    "C10 classified flow as BUY_DOMINANT in C12.",
    "C10 classified flow as BUY_DOMINANT in C11.",
    f"The BTC market state was BUY_DOMINANT in {FUNDING}.",
    f"The cited buy-side pressure reflects BUY_DOMINANT in {FUNDING}.",
    f"Flow is BUY_DOMINANT in {FUNDING}.",
    f"The cited regime is TRENDING_UP in {DIRECTION}.",
    f"Funding indicates longs pay shorts in {FLOW}.",
    f"Funding evidence is described in {FLOW}.", f"Flow evidence is partial in {FUNDING}.",
    f"Funding evidence is described in {MACRO}.",
    "Flow is BUY_DOMINANT in the cited funding item.", "Funding is LONGS_PAY_SHORTS in the cited flow item.",
    f"Flow is BUY_DOMINANT at {TIME}.", "Flow is BUY_DOMINANT in C10.",
])
def test_r1_a_source_suffix_cannot_attribute_an_assertion_elsewhere(statement):
    assert verdict(put(statement, ALL)) == SRC, statement


def test_r1_the_same_holds_for_claims_facts_anchors_and_evidence_remarks():
    false = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "FALSE")["claim_id"]
    other = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "CONFIRMED")
    other_fact = other["frames"][0]["facts"][0]["fact_id"]
    own_fact = next(f["fact_id"] for c in T1_REQ["assessed_claims"] if c["claim_id"] == false
                    for fr in c["frames"] for f in fr["facts"] if f["outcome"] == "SUPPORTED")
    refuting = next(f["fact_id"] for c in T1_REQ["assessed_claims"] if c["claim_id"] == false
                    for fr in c["frames"] for f in fr["facts"] if f["outcome"] == "CONTRADICTED")
    for statement in (f"Claim {false} has the assessed state FALSE in {other['claim_id']}.",
                      f"Claim {false} has the assessed state FALSE in {other_fact}.",
                      f"Fact {own_fact} is supported for claim {false} in {other_fact}."):
        assert verdict(claim_put(false, statement, [own_fact, refuting, other_fact, other["claim_id"]])) == SRC, statement
    out = base()
    out["anchor_assessments"][3]["statement"] = "Anchor A04 is consistent with the cited evidence in C12."
    out["anchor_assessments"][3]["evidence_ids"] = [FLOW, MACRO]
    assert verdict(out) == SRC
    out = base()
    out["summary"]["statement"] = "The evidence at the evaluation time is described in C12."
    out["summary"]["refs"] = [DIRECTION, MACRO]
    assert verdict(out) == SRC


def test_r1_t2_category_and_source_mismatches_are_rejected():
    for statement in (f"The cited fomc state is CURRENT in {CPI3}.", "The cited fomc state is CURRENT in C13.",
                      "C12 classified fomc as CURRENT in C10."):
        out = base(T2_REQ)
        out["context_notes"] = [{"statement": statement, "refs": [FOMC, CPI3], "numbers": []}]
        assert verdict(out, T2_SEL) != "VALID", statement
    out = base(T2_REQ)
    out["context_notes"] = [{"statement": f"The cited fomc state is CURRENT in {CPI3}.", "refs": [FOMC, CPI3],
                             "numbers": []}]
    assert verdict(out, T2_SEL) == SRC


@pytest.mark.parametrize("statement,refs", [
    (f"The cited funding state is LONGS_PAY_SHORTS in {FUNDING}.", [FUNDING, FLOW]),
    (f"The cited flow state is BUY_DOMINANT in {FLOW}.", [FUNDING, FLOW]),
    (f"Funding indicates longs pay shorts in {FUNDING}.", [FUNDING, FLOW]),
    (f"C10 classified flow as BUY_DOMINANT in {FLOW}.", [FUNDING, FLOW]),
    (f"The BTC market state was BUY_DOMINANT in {FLOW}.", [FLOW, FUNDING]),
    (f"The cited buy-side pressure reflects BUY_DOMINANT in {FLOW}.", [FLOW, FUNDING]),
    (f"Funding evidence is described in {FUNDING}.", [FUNDING, FLOW]),
    (f"Flow evidence is partial in {FLOW}.", [FLOW]),
    ("Flow is BUY_DOMINANT in the cited item.", [FLOW]), ("Flow is BUY_DOMINANT in the cited flow item.", [FLOW]),
    ("The cited funding state is LONGS_PAY_SHORTS on the 1h interval.", [FUNDING]),
    ("Flow is BUY_DOMINANT at the evaluation time.", [FLOW]),
    (f"The evidence at the evaluation time is described in {FLOW}.", [FLOW, FUNDING]),
    ("Crowding evidence is unavailable in the cited category.", [FLOW]),
])
def test_r1_correct_citation_supported_suffixes_stay_valid(statement, refs):
    assert verdict(put(statement, refs)) == "VALID", statement


def test_r1_the_structured_refs_are_not_the_textual_suffix():
    # citing both items in refs[] does not let a suffix swap them, and a suffix cannot replace a citation
    assert verdict(put(f"Funding indicates longs pay shorts in {FLOW}.", [FUNDING, FLOW])) == SRC
    assert verdict(put(f"Funding indicates longs pay shorts in {FUNDING}.", [FLOW])) != "VALID"
    out = base()
    out["anchor_assessments"][4]["statement"] = f"Anchor A05 is consistent with the cited evidence in {FUNDING}."
    assert verdict(out) == "VALID"
