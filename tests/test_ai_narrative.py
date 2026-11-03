"""F6 narrative-authority policy and evidence predicates (c14-narrative-policy-5), on complete responses.

Every case replaces one model-written statement in an otherwise valid T1 or T2 response, so the intended policy is
what decides. Acceptance is lexical and evidence-bound; it never proves a sentence is not advice."""
import copy
import dataclasses
import json

import pytest

from ai_support import reply  # noqa: F401
from test_ai_validation import T1_REQ, T1_SEL, T2_REQ, T2_SEL, TS, base, ids
from traid.ai.models import Category
from traid.ai.prompts import NARRATIVE_POLICY_VERSION, PROMPT_DIGEST, PROMPT_ID, SYSTEM_PROMPT
from traid.ai.validation import PROHIBITED_LANGUAGE_VERSION, validate_reply

FLOW, FUNDING, DIRECTION, REGIME, VOL = (ids(T1_REQ, subject=s)[0] for s in
                                         ("flow", "funding", "direction", "regime", "volatility"))
MACRO = ids(T1_REQ, category="C12_MACRO")[0]
CLAIM = T1_REQ["assessed_claims"][0]["claim_id"]
P = "PROHIBITED_TRADE_LANGUAGE"


def verdict(out, sel=T1_SEL):
    v = validate_reply(reply(out), sel.context, TS)
    return "VALID" if v.valid else v.code


def with_states(sel, **states):
    """The same request context with other C10 states, as another market would produce them."""
    ctx, items, lits = sel.context, dict(sel.context.items), dict(sel.context.literals)
    for eid, state in states.items():
        old = items[eid].state
        items[eid] = items[eid].model_copy(update={"state": state})
        lits[eid] = (lits[eid] - {old}) | {state}
    return dataclasses.replace(sel, context=dataclasses.replace(ctx, items=items, literals=lits))


def put(statement, refs, section="summary", request=T1_REQ, numbers=()):
    out = base(request)
    nums = [{"value_id": v, "text": t} for v, t in numbers]
    if section == "summary":
        out["summary"] = {"statement": statement, "refs": list(refs), "numbers": nums}
    elif section == "anchor":
        a = out["anchor_assessments"][0]
        a.update(statement=statement, evidence_ids=list(refs), numbers=nums)
    elif section == "context":
        out["context_notes"] = [{"statement": statement, "refs": list(refs), "numbers": nums}]
    elif section == "claim":
        c = out["claim_notes"][0]
        c.update(statement=statement, refs=[c["claim_id"], *refs], numbers=nums)
    elif section == "uncertainty":
        out["uncertainties"][0] = {"statement": statement, "refs": list(refs), "numbers": nums}
    return out


# ------------------------------------------------------------------------------ accepted when supported
@pytest.mark.parametrize("statement,refs", [
    (f"The cited flow state is BUY_DOMINANT in {FLOW}.", [FLOW]),
    ("C10 classified flow as BUY_DOMINANT.", [FLOW]),
    ("The BTC market state was BUY_DOMINANT.", [FLOW]),                       # BUY_DOMINANT names only the flow dimension
    ("The cited buy-side pressure reflects BUY_DOMINANT.", [FLOW]),
    ("Funding indicates longs pay shorts.", [FUNDING]),
    ("Funding is LONGS_PAY_SHORTS on the cited interval.", [FUNDING]),
    ("The observed direction condition is bullish; the cited direction state is TRENDING_UP.", [DIRECTION]),
    ("The cited regime is TRENDING_UP and the cited direction state is TRENDING_UP.", [REGIME, DIRECTION]),
])
def test_supported_descriptive_statements_are_accepted(statement, refs):
    assert verdict(put(statement, refs)) == "VALID", statement


def test_sell_side_states_need_the_matching_state():
    sel = with_states(T1_SEL, **{FLOW: "SELL_DOMINANT", FUNDING: "SHORTS_PAY_LONGS", DIRECTION: "TRENDING_DOWN"})
    ok = [("The cited sell-side pressure reflects SELL_DOMINANT.", [FLOW]),
          ("Funding indicates shorts pay longs.", [FUNDING]),
          ("The observed direction condition is bearish; the cited direction state is TRENDING_DOWN.", [DIRECTION])]
    for statement, refs in ok:
        assert verdict(put(statement, refs), sel) == "VALID", statement
    # the same sentences against the default evidence (BUY_DOMINANT, LONGS_PAY_SHORTS, TRENDING_UP) are false
    for statement, refs in ok:
        assert verdict(put(statement, refs)) in ("STATE_NOT_EVIDENCED", "SENTIMENT_NOT_EVIDENCED", "UNSUPPORTED_CHARACTER"), statement


def test_complete_t1_and_t2_responses_stay_valid():
    assert verdict(base()) == "VALID"
    assert verdict(base(T2_REQ), T2_SEL) == "VALID"


# ------------------------------------------------------------------------------ explicit and indirect instructions
INSTRUCTIONS = [
    "Buy Bitcoin now given the cited evidence from the item.",
    "Buy BTC at the evaluation time with the cited evidence.",
    "Open a long position given the cited evidence.",
    "You should sell immediately given the cited evidence.",
    "Reduce exposure based on this analysis of the evidence.",
    "Consider hedging based on this evidence from the cited item.",
    "The market will certainly surge tomorrow given the cited evidence.",
    "Go long here given the cited evidence from the item.",
    "Short the market given the cited evidence from the item.",
    "Increase leverage given the cited evidence from the item.",
    "Take profits quickly when the cited evidence turns here.",
    "Allocate capital given the cited evidence from the item.",
    "Position sizing follows the cited evidence from the item.",
    "A stop loss follows the cited evidence from the item.",
    "A stop-loss follows the cited evidence from the item.",
    "The entry follows the cited evidence from the item here.",
    "This is a guaranteed profitable trade given the cited evidence.",
    "Traders may wish to reverse long positions given the evidence.",
    "Holders could increase short exposure given the cited evidence.",
    "Whales might fall further given the cited evidence from the item.",
    "Flip to short given the cited evidence from the item here.",
    "Do not hold longs given the cited evidence from the item here.",
    "Now is a good opportunity given the cited evidence from the item.",
    "This is a bullish signal given the cited evidence from the item.",
    "The forecast follows the cited evidence from the item here.",
]


@pytest.mark.parametrize("statement", INSTRUCTIONS)
def test_instructions_and_predictions_are_rejected(statement):
    assert verdict(put(statement, [FLOW])) == P, statement


@pytest.mark.parametrize("statement", [
    f"Flow is BUY_DOMINANT in {FLOW}; go long.",                               # semicolon clause
    f"Flow is BUY_DOMINANT in {FLOW}, so buy now.",                             # explanatory clause
    f"Flow is BUY_DOMINANT in {FLOW} and holders should act.",                  # conjunction clause
    f"Flow is BUY_DOMINANT in {FLOW}: reduce exposure.",                        # colon clause
    f"Flow is BUY_DOMINANT in {FLOW}. Reduce exposure.",                        # second sentence
    f"Flow is BUY_DOMINANT in {FLOW}, then open a long position.",
    f"Flow is BUY_DOMINANT in {FLOW}, which is why consider hedging.",
    f"Funding is LONGS_PAY_SHORTS but avoid new longs given {FLOW}.",
])
def test_a_valid_description_followed_by_an_instruction_is_rejected(statement):
    out = put(statement, [FLOW, FUNDING])
    assert verdict(out) == P, statement


@pytest.mark.parametrize("statement", [
    "BUY the cited evidence from the item here.", "bUy the cited evidence from the item here.",
    "YOU SHOULD sell the cited evidence from the item.", "Sell-immediately given the cited evidence here.",
    "Buy-and-hold given the cited evidence from the item.", "Re-enter given the cited evidence from the item here.",
])
def test_case_and_hyphenation_do_not_hide_instructions(statement):
    assert verdict(put(statement, [FLOW])) == P, statement


def test_a_stop_loss_instruction_is_rejected_even_with_a_valid_bound_number():
    value = next(v for i in T1_REQ["structured"] if i["evidence_id"] == "E003" for v in i["values"] if v["unit"] == "bps")
    text = value["displays"][0]
    out = put(f"Set a stop loss at {text} bps given the cited item.", ["E003"], numbers=[(value["value_id"], text)])
    assert verdict(out) == P
    ok = put(f"The cited spread is {text} bps in the cited item.", ["E003"], numbers=[(value["value_id"], text)])
    assert verdict(ok) == "VALID"


@pytest.mark.parametrize("section", ["summary", "anchor", "context", "claim", "uncertainty"])
def test_every_model_written_section_is_screened(section):
    refs = [MACRO] if section == "context" else [FLOW]
    assert verdict(put("Buy now given the cited evidence from the item.", refs, section)) == P
    out = put("Whale evidence is described by the cited item; go long.", refs, section)
    assert verdict(out) == P


def test_code_generated_anchor_text_is_not_screened():
    ctx = T1_SEL.context
    anchors = dict(ctx.anchors)
    anchors["A04"] = anchors["A04"].model_copy(update={"statement": "Buy now and go long with leverage."})
    sel = dataclasses.replace(T1_SEL, context=dataclasses.replace(ctx, anchors=anchors))
    assert verdict(base(), sel) == "VALID"


# ------------------------------------------------------------------------------ independent adversarial probes
ADVERSARIAL = [
 "Shorting is attractive given the cited evidence from the item.", "Price is going to rise given the cited evidence here.",
 "The market is about to rally given the cited evidence here.", "BTC is undervalued given the cited evidence from the item.",
 "Whales are positioned for upside given the cited evidence here.", "I think the cited evidence supports a long bias here.",
 "Rotate into BTC given the cited evidence from the item here.", "De-risk given the cited evidence from the item here.",
 "Hold the cited longs given the evidence from the item here.", "Dont sell given the cited evidence from the item here.",
 "Don't sell given the cited evidence from the item here.", "Never short given the cited evidence from the item here.",
 "Perhaps selling longs is wise given the cited evidence here.", "Set TP and SL given the cited evidence from the item.",
 "The setup is bullishly positioned given the cited evidence.", "Funding is LONGS_PAY_SHORTS, which supports going long.",
 "Longs, close out given the cited evidence from the item here.", "Cover shorts given the cited evidence from the item here.",
 "Load up on the cited longs given the evidence from the item.", "Dollar cost average given the cited evidence from the item.",
 "Fade the cited move given the evidence from the item here.", "Ape into the cited longs given the evidence from the item.",
 "Scalp the cited move given the evidence from the item here.", "Trade the cited move given the evidence from the item here.",
 "The cited move is a buying opportunity given the evidence.", "Time to buy given the cited evidence from the item here.",
 "Sellers will be exhausted given the cited evidence from the item.", "The cited evidence supports adding longs here at the item.",
 "Upward momentum continues given the cited direction evidence here.",
 "Flow is BUY_DOMINANT so price rises next given the evidence here.",
]


@pytest.mark.parametrize("statement", ADVERSARIAL)
def test_independent_adversarial_instructions_and_predictions_are_rejected(statement):
    assert verdict(put(statement, [FLOW, DIRECTION, FUNDING])) != "VALID", statement


@pytest.mark.parametrize("statement,refs", [
    ("Liquidity is NOT_THIN in the cited liquidity item.", [ids(T1_REQ, subject="liquidity")[0]]),
    ("Volatility is NOT_HIGH in the cited volatility item.", [VOL]),
    ("The regime is TRENDING_UP in the cited regime item.", [REGIME]),
    ("Crowding evidence is unavailable.", [FLOW]),
    ("The cited direction state is TRENDING_UP in the cited window.", [DIRECTION]),
    ("Funding is LONGS_PAY_SHORTS and flow is BUY_DOMINANT in the cited window.", [FLOW, FUNDING]),
])
def test_independent_descriptive_probes_are_accepted(statement, refs):
    assert verdict(put(statement, refs)) == "VALID", statement


# ------------------------------------------------------------------------------ evidence predicates
@pytest.mark.parametrize("statement,refs,code", [
    (f"Funding indicates shorts pay longs in {FUNDING}.", [FUNDING], "STATE_NOT_EVIDENCED"),
    ("Funding is SHORTS_PAY_LONGS on the cited interval.", [FUNDING], "UNSUPPORTED_CHARACTER"),   # not a literal here
    ("The cited flow state is SELL_DOMINANT.", [FLOW], "UNSUPPORTED_CHARACTER"),
    ("Sell pressure is described by the cited flow evidence.", [FLOW], "STATE_NOT_EVIDENCED"),
    ("Sellers are described by the cited flow evidence.", [FLOW], "STATE_NOT_EVIDENCED"),
    ("Buy pressure is described by the cited funding evidence.", [FUNDING], "STATE_NOT_EVIDENCED"),    # uncited flow
    ("Flow is BUY_DOMINANT.", [FUNDING], "UNSUPPORTED_CHARACTER"),                                   # label not cited
    ("Flow is BUY_DOMINANT and flow is not SELL_DOMINANT.", [FLOW], "UNSUPPORTED_CHARACTER"),
    ("Buyers and sellers are described by the cited flow evidence.", [FLOW], "STATE_NOT_EVIDENCED"),
    ("Flow is not BUY_DOMINANT in the cited item.", [FLOW], "STATE_NOT_EVIDENCED"),                   # negated
    ("Funding is BUY_DOMINANT in the cited funding item.", [FUNDING, FLOW], "STATE_NOT_EVIDENCED"),   # wrong subject
    ("Flow and funding are BUY_DOMINANT and LONGS_PAY_SHORTS.", [FLOW, FUNDING], "STATE_NOT_EVIDENCED"),
    ("Funding is LONGS_PAY_SHORTS while flow is LONGS_PAY_SHORTS.", [FLOW, FUNDING], "STATE_NOT_EVIDENCED"),
    ("The cited direction state is TRENDING_UP and funding is TRENDING_UP.", [DIRECTION, FUNDING],
     "STATE_NOT_EVIDENCED"),
    ("The cited state is TRENDING_UP in the cited item.", [DIRECTION], "STATE_NOT_EVIDENCED"),        # ambiguous subject
    ("The cited trend is trending up in the cited funding item.", [FUNDING], "STATE_NOT_EVIDENCED"),
    ("Directional momentum is described by the cited funding evidence.", [FUNDING], "STATE_NOT_EVIDENCED"),
])
def test_asserted_states_need_cited_eligible_evidence_of_that_subject(statement, refs, code):
    expected = {code, "UNSUPPORTED_CONSTRUCTION"} if code == "STATE_NOT_EVIDENCED" else {code}
    assert verdict(put(statement, refs)) in expected, statement


def test_mixed_true_and_false_assertions_in_one_statement_are_rejected():
    out = put(f"Flow is BUY_DOMINANT in {FLOW}; funding indicates shorts pay longs.", [FLOW, FUNDING])
    assert verdict(out) == "STATE_NOT_EVIDENCED"
    out = put(f"Funding indicates longs pay shorts in {FUNDING}; funding indicates shorts pay longs.", [FUNDING])
    assert verdict(out) == "STATE_NOT_EVIDENCED"


@pytest.mark.parametrize("statement", [
    "Long positions experienced liquidations.", "Short positions were liquidated in the window here.",
    "Shorts faced liquidation pressure in the cited window.", "Longs liquidated in the cited window here.",
    "The liquidation of longs is described by the cited item.", "Liquidations hit shorts in the cited item.",
])
def test_liquidation_side_claims_are_rejected_without_side_evidence(statement):
    assert verdict(put(statement, [FLOW])) == "LIQUIDATION_SIDE_UNSUPPORTED", statement


def test_liquidation_without_a_side_is_not_a_side_claim():
    # without a cited liquidation item no liquidation statement can be supported, with or without a side
    assert verdict(put("Liquidation evidence is described by the cited item here.", [FLOW])) != "VALID"
    assert verdict(put("Liquidation evidence is unavailable for the cited category.", [FLOW])) == "VALID"


# ------------------------------------------------------------------------------ bullish and bearish
GOOD = "The observed direction condition is bullish; the cited direction state is TRENDING_UP."


@pytest.mark.parametrize("statement,refs,code", [
    (GOOD.replace("bullish", "bearish"), [DIRECTION], "SENTIMENT_NOT_EVIDENCED"),        # opposite word
    ("The observed direction condition is bearish; the cited direction state is TRENDING_UP.", [DIRECTION],
     "SENTIMENT_NOT_EVIDENCED"),
    ("The observed direction condition is bullish.", [DIRECTION], "SENTIMENT_NOT_EVIDENCED"),   # no state label
    (GOOD, [FLOW], "UNSUPPORTED_CHARACTER"),                                               # direction item not cited
    (GOOD, [REGIME], "STATE_NOT_EVIDENCED"),                                           # regime is not direction
    ("The flow condition is bullish; the cited direction state is TRENDING_UP.", [DIRECTION],
     "SENTIMENT_NOT_EVIDENCED"),                                                           # not the observed direction
    ("The observed direction condition is bullish; the cited funding state is LONGS_PAY_SHORTS.", [DIRECTION, FUNDING],
     "SENTIMENT_NOT_EVIDENCED"),
    ("The observed direction condition is bullish and bearish; the cited direction state is TRENDING_UP.",
     [DIRECTION], "SENTIMENT_NOT_EVIDENCED"),
    ("The observed direction condition is bullish; the cited direction state is TRENDING_UP and RANGING.",
     [DIRECTION], "STATE_NOT_EVIDENCED"),
    ("The observed direction condition is bullish, so buy.", [DIRECTION], P),
    ("The observed direction condition is bullish; expect more upside.", [DIRECTION], P),
    ("Funding is bullish given the cited evidence.", [FUNDING], "SENTIMENT_NOT_EVIDENCED"),
    ("Whale evidence is bearish given the cited item.", [FLOW], "SENTIMENT_NOT_EVIDENCED"),
])
def test_bullish_and_bearish_only_as_the_observed_direction_state(statement, refs, code):
    assert verdict(put(statement, refs)) == code, statement


def test_bullish_needs_the_matching_direction_state_and_never_unknown_or_ranging():
    for state, word in (("TRENDING_DOWN", "bullish"), ("RANGING", "bullish"), ("RANGING", "bearish")):
        sel = with_states(T1_SEL, **{DIRECTION: state})
        statement = f"The observed direction condition is {word}; the cited direction state is {state}."
        assert verdict(put(statement, [DIRECTION]), sel) == "SENTIMENT_NOT_EVIDENCED", (state, word)
    sel = with_states(T1_SEL, **{DIRECTION: "UNKNOWN"})
    assert verdict(put(GOOD, [DIRECTION]), sel) == "UNSUPPORTED_CHARACTER"


def test_bullish_is_never_accepted_in_the_macro_task():
    sentence = "The observed direction condition is bullish in the cited macro item here."
    out = base(T2_REQ)
    out["summary"]["statement"] = f"{sentence} {out['summary']['refs'][0]}"
    assert verdict(out, T2_SEL) == "SENTIMENT_NOT_EVIDENCED"


# ------------------------------------------------------------------------------ canonical labels and aliases
@pytest.mark.parametrize("statement", [
    "Order flow is buy-dominant in the cited item.", "Order flow is sell-dominant in the cited item.",
    "The cited flow is Buy-Dominant in the item.", "The cited flow is buydominant in the item here.",
    "The cited funding is longs-pay-shorts in the item.", "The cited funding is shorts-pay-longs in the item.",
    "The cited direction is trending-up in the item here.", "The cited direction is TrendingDown in the item.",
])
def test_aliases_of_canonical_states_are_rejected(statement):
    assert verdict(put(statement, [FLOW, FUNDING, DIRECTION])) == "STATE_ALIAS", statement


def test_lowercase_and_underscore_labels_are_not_labels():
    assert verdict(put("The cited flow state is buy_dominant in the item.", [FLOW])) == "UNSUPPORTED_CHARACTER"
    assert verdict(put("The cited flow state is Buy_Dominant in the item.", [FLOW])) == "UNSUPPORTED_CHARACTER"
    assert verdict(put("The cited flow state is buy dominant in the item.", [FLOW])) == P


# ------------------------------------------------------------------------------ C10 to C13 as words
def test_category_words_are_admitted_only_beside_cited_evidence_of_that_category():
    assert verdict(put("C10 classified the cited flow state as BUY_DOMINANT.", [FLOW])) == "VALID"
    assert verdict(put("C10 evidence is described by the cited item here.", [FLOW])) == "VALID"
    assert verdict(put("C12 evidence is described by the cited item here.", [FLOW, MACRO])) == "VALID"
    assert verdict(put("C11 evidence is described by the cited item here.", [FLOW])) == "TOKEN_INVALID"
    assert verdict(put("C12 evidence is described by the cited item here.", [FLOW])) == "TOKEN_INVALID"
    assert verdict(put("C13 evidence is described by the cited item here.", [FLOW])) == "TOKEN_INVALID"
    assert verdict(put("C14 evidence is described by the cited item here.", [FLOW])) == "TOKEN_INVALID"
    assert verdict(put("c10 evidence is described by the cited item here.", [FLOW])) == "TOKEN_INVALID"
    assert verdict(put("C10-C13 evidence is described by the cited item.", [FLOW])) == "TOKEN_INVALID"


def test_category_words_are_not_references():
    for bad in ("C10", "C12", "C13", "C13.F01"):
        out = base()
        out["uncertainties"][0]["refs"] = [bad]
        assert verdict(out) == "UNKNOWN_REFERENCE", bad
    out = base()
    out["summary"]["refs"] = ["C10"]
    assert verdict(out) == "UNKNOWN_REFERENCE"


def test_cross_category_attribution_is_rejected():
    c11 = ids(T1_REQ, category="C11")[0]
    out = put("C11 classified the cited flow state as BUY_DOMINANT.", [FLOW, c11])
    assert verdict(out) in ("CROSS_CATEGORY_ATTRIBUTION", "STATE_NOT_EVIDENCED")
    out = put("C12 reports that funding indicates longs pay shorts.", [FUNDING, MACRO])
    assert verdict(out) == "CROSS_CATEGORY_ATTRIBUTION"
    assert verdict(put("C10 evidence is described.", [FLOW, MACRO])) == "VALID"
    assert verdict(put("C12 evidence is described.", [FLOW, MACRO])) == "VALID"


def test_missing_categories_are_not_turned_into_evidence_claims():
    out = base()
    out["uncertainties"][0] = {"statement": "C12 evidence is described as present in the uncertainty section.",
                               "refs": ["CAT:C12_ETF"], "numbers": []}
    assert verdict(out) == "TOKEN_INVALID"                       # a CAT reference is not eligible cited evidence


def test_c13_claims_are_not_verified_facts():
    out = put("C13 verified the claim in the cited claim note here.", [], "claim")
    assert verdict(out) == "CLAIM_CITED_AS_FACT"
    assert verdict(put("C13 evidence is described.", [], "claim")) == "VALID"
    fact = next(f for c in T1_REQ["assessed_claims"] for fr in c["frames"] for f in fr["facts"]
                if f["outcome"] == "SUPPORTED")
    owner = next(c["claim_id"] for c in T1_REQ["assessed_claims"] for fr in c["frames"] for f in fr["facts"]
                 if f["fact_id"] == fact["fact_id"])
    out = base()
    note = next(n for n in out["claim_notes"] if n["claim_id"] == owner)
    note["statement"] = "C13 verified the cited fact in the cited claim note here."
    note["refs"] = [owner, fact["fact_id"]]
    assert verdict(out) != "VALID"                            # a supporting fact is cited, but prose is still denied
    note["statement"] = f"Fact {fact['fact_id']} is supported for claim {owner}."
    assert verdict(out) == "VALID"


def test_t2_does_not_admit_c10_or_c11_or_asset_conclusions():
    ref = T2_REQ["summary_ref"] if "summary_ref" in T2_REQ else base(T2_REQ)["summary"]["refs"][0]
    for word in ("C10", "C11"):
        out = base(T2_REQ)
        out["summary"]["statement"] = f"{word} evidence is described by {ref} here."
        assert verdict(out, T2_SEL) == "TOKEN_INVALID", word
    out = base(T2_REQ)
    out["summary"]["statement"] = f"C12 evidence is described by {ref} here."
    assert verdict(out, T2_SEL) == "VALID"
    for statement in ("The CPI print supports a bullish view of Bitcoin here.", "Funding is described for BTC here.",
                      "Order flow is buy-dominant for the cited macro item.", "The cited buy-side pressure matters."):
        out = base(T2_REQ)
        out["summary"]["statement"] = f"{statement} {ref}"
        assert verdict(out, T2_SEL) != "VALID", statement


# ------------------------------------------------------------------------------ macro wording is not blocked
@pytest.mark.parametrize("statement", [
    "The federal funds target range is described by the cited item here.",
    "Short-term rates are described by the cited item here.",
    "The cited index is described for the US here.",
    "US inflation is described by the cited item here.",
    "A hedge fund is not described by the cited item here.",
    "Trading volume is not described by the cited item here.",
    "Increase in the index is not asserted by the cited item here.",
])
def test_ordinary_macro_wording_is_not_blocked(statement):
    out = base(T2_REQ)
    out["summary"]["statement"] = f"{statement} {out['summary']['refs'][0]}"
    code = verdict(out, T2_SEL)
    assert code not in (P, "STATE_NOT_EVIDENCED", "LIQUIDATION_SIDE_UNSUPPORTED"), (statement, code)


# ------------------------------------------------------------------------------ versions
def test_policy_version_prompt_digest_and_prompt_text_agree():
    assert PROMPT_ID == "c14-prompt-5"
    assert PROHIBITED_LANGUAGE_VERSION == NARRATIVE_POLICY_VERSION == "c14-narrative-policy-5"
    assert NARRATIVE_POLICY_VERSION in SYSTEM_PROMPT                    # so PROMPT_DIGEST covers the policy version
    assert T1_SEL.request.prompt_id == PROMPT_ID and T1_SEL.request.prompt_digest == PROMPT_DIGEST
    for label in ("BUY_DOMINANT", "SELL_DOMINANT", "TRENDING_UP", "TRENDING_DOWN", "LONGS_PAY_SHORTS",
                  "SHORTS_PAY_LONGS", "C10", "C13", "bullish", "bearish"):
        assert label in SYSTEM_PROMPT
