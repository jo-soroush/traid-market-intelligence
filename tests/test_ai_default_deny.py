"""F6 final pass: default deny. Every model-written statement must be an approved construction bound to evidence;
vocabulary decides nothing. Covers the four verified blockers F1-F4, every construction the prompt teaches, and the
unmatched-prose rule, all as complete responses."""
import copy

import pytest

from ai_support import restate_anchors  # noqa: F401
from test_ai_narrative import DIRECTION, FLOW, FUNDING, MACRO, REGIME, VOL, put, verdict, with_states
from test_ai_validation import T1_REQ, T1_SEL, T2_REQ, T2_SEL, base, ids
from traid.ai.prompts import SYSTEM_PROMPT

UC = "UNSUPPORTED_CONSTRUCTION"
LIQ = ids(T1_REQ, subject="liquidity")[0]
C11 = ids(T1_REQ, category="C11")[0]
CPI3 = ids(T2_REQ, category="C12_MACRO", subject="CUUR0000SA0")[0]
FOMC = ids(T2_REQ, category="C12_MACRO", subject="fomc")[0]


def item_value(request, eid, suffix):
    item = next(i for i in request["structured"] + request["contextual"] if i["evidence_id"] == eid)
    return next(v for v in item["values"] if v["field_path"].endswith(suffix))


def claim_put(claim_id, statement, refs, section="claim_notes"):
    out = base()
    if section == "claim_notes":
        note = next(n for n in out["claim_notes"] if n["claim_id"] == claim_id)
        note.update(statement=statement, refs=[claim_id, *refs], numbers=[])
    else:
        out["uncertainties"][0] = {"statement": statement, "refs": list(refs), "numbers": []}
    return out


# F1 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "Ride the move given the cited evidence from the item here.",
    "The cited evidence points toward cashing out.",
    "A wager on the rebound fits the cited observations.",
    "The economy contracted during the cited period.",
])
def test_f1_unmatched_prose_is_rejected(statement):
    assert verdict(put(statement, [FLOW])) == UC, statement
    out = base(T2_REQ)
    out["summary"]["statement"] = statement
    assert verdict(out, T2_SEL) == UC, statement


@pytest.mark.parametrize("statement", [
    "The harbour looks calm in the cited window.", "Cats are wonderful companions here.",
    "Evidence is interesting in the cited item.", "The cited item contains numbers and letters.",
    "Things are developing in the cited window.", "Nothing unusual is visible in the cited item.",
    "The cited item was reviewed by the team.", "Results are consistent with expectations in the item.",
    "The outcome remains open for the cited item.", "This statement is neutral and short enough.",
])
def test_f1_unmatched_statements_are_rejected_whatever_their_vocabulary(statement):
    for section, refs in (("summary", [FLOW]), ("context", [MACRO]), ("uncertainty", [FLOW])):
        assert verdict(put(statement, refs, section)) == UC, (section, statement)


# F2 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement,refs", [
    ("Funding evidence is unavailable.", [FLOW]),                  # eligible funding evidence exists
    ("Flow evidence is missing.", [FLOW]),
    ("Funding evidence is unavailable in the cited category.", [FUNDING]),
    ("Direction evidence is unavailable.", [DIRECTION]),
    ("Funding evidence is partial in the cited item.", [FUNDING]),   # nothing is withheld for funding
    ("Crowding evidence is described by the cited item.", [FLOW]),   # it is unavailable, not described
    ("Crowding evidence is partial in the cited item.", [FLOW]),
    ("Funding evidence is described in the cited item.", [FLOW]),   # funding is supplied but not cited here
])
def test_f2_availability_must_match_the_selected_evidence(statement, refs):
    assert verdict(put(statement, refs)) in ("STATUS_NOT_EVIDENCED",), statement


def test_f2_true_availability_statements_are_accepted():
    assert verdict(put("Crowding evidence is unavailable.", [FLOW])) == "VALID"
    assert verdict(put("Flow evidence is partial in the cited item.", [FLOW])) == "VALID"       # values are withheld
    assert verdict(put("Funding evidence is described in the cited item.", [FUNDING])) == "VALID"
    assert verdict(put("Funding evidence is available in the cited item.", [FUNDING])) == "VALID"
    out = base()
    out["uncertainties"][0] = {"statement": "The category CAT:C12_ETF is excluded.", "refs": ["CAT:C12_ETF"],
                               "numbers": []}
    assert verdict(out) == "VALID"
    out["uncertainties"][0]["statement"] = "The category CAT:C12_ETF is not supplied."          # its state is excluded
    assert verdict(out) == "STATUS_NOT_EVIDENCED"
    out["uncertainties"][0]["statement"] = "The category CAT:C12_ETF is partial."
    assert verdict(out) == "STATUS_NOT_EVIDENCED"


def test_f2_distinguishes_absent_item_partial_evidence_and_category_status():
    # an item that is absent versus one that is present with withheld values versus a whole category status
    assert verdict(put("Crowding evidence is unavailable.", [FLOW])) == "VALID"                  # absent, reason listed
    assert verdict(put("Crowding evidence is missing.", [FLOW])) == "VALID"
    assert verdict(put("Flow evidence is unavailable.", [FLOW])) == "STATUS_NOT_EVIDENCED"      # present
    assert verdict(put("Flow evidence is partial.", [FLOW])) == "VALID"                          # present, withheld
    out = base()
    out["uncertainties"][0] = {"statement": "Some evidence categories are unavailable or only partly included.",
                               "refs": ["CAT:C12_ETF"], "numbers": []}
    assert verdict(out) == "VALID"
    # when the request lists every category as included, the general sentence is false
    ctx = T1_SEL.context
    from traid.ai.models import CategoryState
    all_in = {c: (CategoryState.INCLUDED if s is not CategoryState.NOT_USED_BY_TASK else s)
              for c, s in ctx.categories.items()}
    import dataclasses
    sel = dataclasses.replace(T1_SEL, context=dataclasses.replace(ctx, categories=all_in))
    out = base()
    out["uncertainties"][0] = {"statement": "Some evidence categories are unavailable or only partly included.",
                               "refs": [FLOW], "numbers": []}
    assert verdict(out, sel) == "STATUS_NOT_EVIDENCED"


# F3 -------------------------------------------------------------------------------------------------------------
def test_f3_a_fact_of_another_claim_never_supports_a_false_claim():
    false = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "FALSE")["claim_id"]
    other = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "CONFIRMED")
    other_fact = other["frames"][0]["facts"][0]["fact_id"]
    for statement in (f"Fact {other_fact} is supported for claim {false}.",
                      f"Claim {false} has the assessed state CONFIRMED.",
                      f"Claim {false} is verified by {other_fact}.",
                      f"Claim {false} is confirmed by {other_fact}."):
        assert verdict(claim_put(false, statement, [other_fact])) != "VALID", statement
        assert verdict(claim_put(false, statement, [false, other_fact], "uncertainties")) != "VALID", statement
    assert verdict(claim_put(false, f"Fact {other_fact} is supported for claim {false}.", [other_fact])) == \
        "CLAIM_NOT_EVIDENCED"


def test_f3_every_claim_assertion_is_bound_to_its_own_claim_state_and_facts():
    claims = {c["claim_id"]: c for c in T1_REQ["assessed_claims"]}
    false = next(k for k, c in claims.items() if c["state"] == "FALSE")
    facts = {f["fact_id"]: f for fr in claims[false]["frames"] for f in fr["facts"]}
    refuting = next(k for k, f in facts.items() if f["outcome"] == "CONTRADICTED")
    supporting = next(k for k, f in facts.items() if f["outcome"] == "SUPPORTED")
    good = [f"Claim {false} has the assessed state FALSE.",
            f"Fact {supporting} is supported for claim {false}.",
            f"Fact {refuting} is contradicted for claim {false}.",
            f"Claim {false} asserted {facts[refuting]['claim_asserted']}, which {refuting} contradicts."]
    for statement in good:
        assert verdict(claim_put(false, statement, [refuting, supporting])) == "VALID", statement
    bad = [f"Fact {supporting} is contradicted for claim {false}.", f"Fact {refuting} is supported for claim {false}.",
           f"Claim {false} asserted {facts[refuting]['claim_asserted']}, which {supporting} contradicts.",
           f"Claim {false} asserted {facts[supporting]['claim_asserted']}, which {refuting} contradicts.",
           f"Fact {refuting} is unresolved for claim {false}.", f"Fact {supporting} is superseded for claim {false}."]
    for statement in bad:
        assert verdict(claim_put(false, statement, [refuting, supporting])) != "VALID", statement
    # a note about one claim cannot make assertions about another claim, even a true one
    other = next(k for k in claims if k != false)
    other_fact = next(f["fact_id"] for fr in claims[other]["frames"] for f in fr["facts"])
    assert verdict(claim_put(false, f"Fact {other_fact} is supported for claim {other}.", [other_fact, other])) == \
        "CLAIM_NOT_EVIDENCED"
    # a fact that is cited but not named by the construction's own claim
    assert verdict(claim_put(false, f"Claim {false} has the assessed state FALSE.", [refuting])) == "VALID"
    assert verdict(claim_put(false, f"Claim {false} has the assessed state FALSE and fact {supporting} is "
                                    f"supported for claim {other}.", [supporting])) != "VALID"


# F4 -------------------------------------------------------------------------------------------------------------
FID = FUNDING
FV = item_value(T1_REQ, FUNDING, "funding.latest_rate")
FT = FV["displays"][0]
FN = [(FV["value_id"], FT)]


def numeric(statement, refs, numbers, request=T1_REQ, sel=T1_SEL):
    out = base(request)
    out["uncertainties"].append({"statement": statement, "refs": list(refs),
                                 "numbers": [{"value_id": v, "text": t} for v, t in numbers]})
    from test_ai_narrative import verdict as v
    return v(out, sel)


@pytest.mark.parametrize("statement", [
    f"The latest funding rate was {FT} per day in {FID}.",
    f"The latest funding rate was {FT} as a daily payment in {FID}.",
    f"The latest funding rate was {FT} per eight hours in {FID}.",
    f"The latest funding rate was {FT} annualized in {FID}.",
    f"The latest funding rate was {FT} per week in {FID}.",
    f"The latest funding rate was {FT} per hour after fees in {FID}.",
    f"The latest funding rate was {FT} yesterday in {FID}.",
    f"The latest funding rate was {FT} per hour on average in {FID}.",
    f"The latest funding rate was {FT} per hour, a high payment.",
])
def test_f4_hourly_funding_is_never_another_interval_and_qualifiers_are_rejected(statement):
    assert numeric(statement, [FID], FN) != "VALID", statement


@pytest.mark.parametrize("statement", [
    f"The latest funding rate was {FT} per hour in {FID}.",
    f"The latest funding rate was {FT} as a fraction in {FID}.",
    f"The latest funding rate was {FT} in {FID}.",
    f"The latest funding rate was {FT} at the evaluation time.",
    f"The cited value is {FT} as a fraction in {FID}.",
    f"The BTC funding rate was {FT} per hour in {FID}.",
])
def test_f4_the_supported_numeric_constructions_are_accepted(statement):
    assert numeric(statement, [FID], FN) == "VALID", statement


def test_f4_numbers_stay_bound_to_subject_metric_unit_and_source():
    flow = item_value(T1_REQ, FLOW, "window_buy_volume")
    ft = flow["displays"][-1]
    fn = [(flow["value_id"], ft)]
    assert numeric(f"The window buy volume was {ft} BTC in {FLOW}.", [FLOW], fn) == "VALID"
    for bad in (f"The window buy volume was {ft} USD in {FLOW}.",             # wrong unit
                f"The latest funding rate was {ft} BTC in {FLOW}.",           # another metric's words
                f"The window buy volume was {ft} BTC in {FUNDING}.",          # another item as the source
                f"The window sell volume was {ft} BTC in {FLOW}.",            # a different metric
                f"The window buy volume was {ft} BTC today in {FLOW}."):      # a time qualifier
        assert numeric(bad, [FLOW, FUNDING], fn) != "VALID", bad
    # the declared value must be the one written, and a value cannot be declared and left unwritten
    assert numeric(f"The latest funding rate was {FT} in {FID}.", [FID], []) != "VALID"
    assert numeric(f"The evidence is described in {FID}.", [FID], FN) != "VALID"
    # source semantics: a linked value is reachable through its cited fact, and only through that fact
    cpi = item_value(T2_REQ, CPI3, "known_value")
    fact = next(f for c in T2_REQ["assessed_claims"] for fr in c["frames"] for f in fr["facts"]
                if f["linked_value_ids"] == [cpi["value_id"]])["fact_id"]
    n = [(cpi["value_id"], cpi["value"])]
    assert numeric(f"The CPI level was {cpi['value']} in {fact}.", [fact], n, T2_REQ, T2_SEL) == "VALID"
    assert numeric(f"The CPI level was {cpi['value']} in {CPI3}.", [CPI3], n, T2_REQ, T2_SEL) == "VALID"
    assert numeric(f"The CPI level was {cpi['value']} per day in {CPI3}.", [CPI3], n, T2_REQ, T2_SEL) != "VALID"


# approved constructions: every form the prompt teaches has a complete-response test ---------------------------------
def anchor(out, anchor_id, extra):
    a = next(x for x in out["anchor_assessments"] if x["anchor_id"] == anchor_id)
    a["statement"] += " " + extra
    return a


TAUGHT_T1 = [
    ("The cited flow state is BUY_DOMINANT.", [FLOW]), ("Flow is BUY_DOMINANT.", [FLOW]),
    ("C10 classified flow as BUY_DOMINANT.", [FLOW]), ("The BTC market state was BUY_DOMINANT.", [FLOW]),
    ("The cited buy-side pressure reflects BUY_DOMINANT.", [FLOW]),
    ("Funding indicates longs pay shorts.", [FUNDING]),
    ("The observed direction condition is bullish; the cited direction state is TRENDING_UP.", [DIRECTION]),
    ("The cited volatility state is NOT_HIGH.", [VOL]), ("Liquidity is NOT_THIN.", [LIQ]),
    ("The cited regime is TRENDING_UP.", [REGIME]),
    ("Flow evidence is described.", [FLOW]), ("Flow evidence is partial.", [FLOW]),
    ("Crowding evidence is unavailable.", [FLOW]),
    ("The evidence at the evaluation time is described in E004.", [FLOW]), ("C10 evidence is described.", [FLOW]),
]


@pytest.mark.parametrize("statement,refs", TAUGHT_T1)
def test_every_t1_form_the_prompt_teaches_is_a_valid_complete_response(statement, refs):
    for section in ("summary", "uncertainty"):
        assert verdict(put(statement, refs, section)) == "VALID", (section, statement)
    if "bullish" in statement:                           # the bullish form is a whole statement of its own
        return
    out = base()
    anchor(out, "A04", statement)
    out["anchor_assessments"][3]["evidence_ids"] = sorted(set(out["anchor_assessments"][3]["evidence_ids"] + refs))
    assert verdict(out) == "VALID", statement


def test_the_remaining_t1_forms_the_prompt_teaches():
    # category status, claim, fact and asserted value, anchor stances, numbers
    out = base()
    out["uncertainties"][0] = {"statement": "The category CAT:C12_ETF is excluded.", "refs": ["CAT:C12_ETF"], "numbers": []}
    assert verdict(out) == "VALID"
    false = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "FALSE")["claim_id"]
    refuting = next(f["fact_id"] for c in T1_REQ["assessed_claims"] if c["claim_id"] == false
                    for fr in c["frames"] for f in fr["facts"] if f["outcome"] == "CONTRADICTED")
    assert verdict(claim_put(false, f"Claim {false} has the assessed state FALSE.", [refuting])) == "VALID"
    for stance, phrase in (("SUPPORTS", "consistent with"), ("CONTRADICTS", "inconsistent with"),
                           ("MIXED", "partly consistent with"), ("NOT_ASSESSABLE", "not assessable from")):
        out = base()
        out["anchor_assessments"][0]["stance"] = stance
        restate_anchors(out)
        assert phrase in out["anchor_assessments"][0]["statement"]
        out["anchor_assessments"][1]["stance"] = "SUPPORTS"
        restate_anchors(out)
        assert verdict(out) == "VALID", stance
    assert numeric(f"The latest funding rate was {FT} as a fraction in {FID}.", [FID], FN) == "VALID"


def test_every_t2_form_the_prompt_teaches_is_a_valid_complete_response():
    cpi = item_value(T2_REQ, CPI3, "known_value")
    for statement, refs, numbers in (
            ("The cited fomc state is CURRENT.", [FOMC], []), ("C12 classified fomc as CURRENT.", [FOMC], []),
            ("The evidence at the evaluation time is described in " + CPI3 + ".", [CPI3], []),
            ("C12 evidence is described.", [CPI3], []),
            (f"The CPI level was {cpi['value']} in {CPI3}.", [CPI3], [{"value_id": cpi["value_id"], "text": cpi["value"]}])):
        out = base(T2_REQ)
        out["context_notes"] = [{"statement": statement, "refs": refs, "numbers": numbers}]
        assert verdict(out, T2_SEL) == "VALID", statement


def test_anchor_assessments_state_their_anchor_and_stance_exactly_once():
    out = base()
    out["anchor_assessments"][0]["statement"] = "Direction evidence is described."
    assert verdict(out) == "ANCHOR_NOT_EVIDENCED"                                    # no anchor construction
    out = base()
    out["anchor_assessments"][0]["stance"] = "CONTRADICTS"                          # wording says consistent
    assert verdict(out) == "ANCHOR_NOT_EVIDENCED"
    out = base()
    out["anchor_assessments"][0]["statement"] = "Anchor A02 is consistent with the cited evidence in E001."
    assert verdict(out) == "ANCHOR_NOT_EVIDENCED"                                    # another anchor
    out = base()
    out["anchor_assessments"][0]["statement"] += " Anchor A01 is consistent with the cited evidence in E001 again."
    assert verdict(out) == "ANCHOR_NOT_EVIDENCED"                                    # twice
    out = base()
    out["context_notes"] = [{"statement": "Anchor A01 is consistent with the cited evidence in E002.",
                             "refs": [ids(T1_REQ, category="C12_MACRO")[0]], "numbers": []}]
    assert verdict(out) != "VALID"                                                   # not outside anchor_assessments


def test_the_prompt_states_the_default_deny_rule_and_every_construction():
    for text in ("Default deny", "The cited X state is S.", "The BTC market state was BUY_DOMINANT.",
                 "Funding indicates longs pay shorts.", "bullish", "X evidence is unavailable.", "CAT:C12_ETF",
                 "Claim N001 has the assessed state S.", "Fact N001.F01 is supported for claim", "asserted",
                 "Anchor A01 is consistent with the cited evidence", "described in E001", "per hour",
                 "never \"per day\""):
        assert text in SYSTEM_PROMPT or text.replace('never "per day"', 'never "per day"') in SYSTEM_PROMPT, text


def test_repeated_validation_is_deterministic():
    for out in (put("Funding indicates longs pay shorts.", [FUNDING]), put("Ride the move given the cited evidence.", [FLOW]),
                put("Funding evidence is unavailable.", [FLOW])):
        assert len({verdict(copy.deepcopy(out)) for _ in range(5)}) == 1


def test_complete_t1_and_t2_responses_are_valid():
    assert verdict(base()) == "VALID"
    assert verdict(base(T2_REQ), T2_SEL) == "VALID"
