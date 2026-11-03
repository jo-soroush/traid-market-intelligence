"""F6 audit findings B1-B8 (independent Codex audit), as complete-response regressions, plus an independent
probe set and a small measurement. Every statement replaces one model-written statement in an otherwise valid
response; the policy is lexical and evidence-bound and never proves a sentence is not advice."""
import json

import pytest

from test_ai_narrative import (  # noqa: F401
    CLAIM, DIRECTION, FLOW, FUNDING, MACRO, REGIME, VOL, P, GOOD, put, verdict, with_states,
)
from test_ai_validation import T1_REQ, T1_SEL, T2_REQ, T2_SEL, base, ids

REJECTED = ("PROHIBITED_TRADE_LANGUAGE", "UNSUPPORTED_CONSTRUCTION", "STATE_NOT_EVIDENCED",
            "SENTIMENT_NOT_EVIDENCED", "STATE_ALIAS", "LIQUIDATION_SIDE_UNSUPPORTED", "CLAIM_CITED_AS_FACT",
            "CROSS_CATEGORY_ATTRIBUTION", "UNSUPPORTED_CHARACTER", "TOKEN_INVALID")


def rejected(statement, refs=(FLOW,), **kw):
    code = verdict(put(statement, list(refs), **kw), kw.pop("sel", T1_SEL) if False else T1_SEL)
    assert code != "VALID", statement
    assert code in REJECTED, (statement, code)


# B1 -------------------------------------------------------------------------------------------------------------
B1 = [
    "Kindly purchase Bitcoin given the cited evidence.",
    "It is prudent to purchase Bitcoin given the cited evidence.",
    "The evidence favors purchasing Bitcoin.",
    "A purchase of Bitcoin is prudent given the cited evidence.",
    "Acquiring Bitcoin here is the sensible course given the cited evidence.",
    "A purchase is warranted given the cited evidence from the item.",
    "The cited evidence makes this a good moment to acquire Bitcoin.",
    "Accumulating exposure is the better course given the cited evidence.",
    "Bitcoin looks cheap given the cited evidence from the item here.",
    "Positioning long is the better choice given the cited evidence.",
    "Offloading holdings is sensible given the cited evidence from the item.",
    "The evidence argues for disposing of Bitcoin holdings here.",
    "Expanding positions is warranted given the cited evidence here.",
    "It would be better to wait for the cited evidence to change.",
    "Bitcoin is therefore a good candidate for acquisition given the item.",
]


@pytest.mark.parametrize("statement", B1)
def test_b1_recommendations_without_imperative_syntax_are_rejected(statement):
    rejected(statement)


def test_b1_a_valid_label_does_not_license_a_recommendation():
    rejected("Flow is BUY_DOMINANT; a purchase of Bitcoin is prudent.", [FLOW])


# B2 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "The observed direction condition is bullish next week; the cited direction state is TRENDING_UP.",
    GOOD + " The observed funding condition is bullish.",
    "The observed direction condition is bullish; the cited direction state is TRENDING_UP; the observed funding "
    "condition is bullish.",
    "The observed direction condition is bullish; the cited direction state is TRENDING_UP, so risk is low.",
    "The observed direction condition is bullish today; the cited direction state is TRENDING_UP.",
])
def test_b2_only_the_exact_observed_direction_construction_passes(statement):
    rejected(statement, [DIRECTION, FUNDING])
    assert verdict(put(GOOD, [DIRECTION])) == "VALID"


# B3 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "Funding is described by flow as BUY_DOMINANT.",
    "Funding is BUY_DOMINANT according to the cited flow item.",
    "The cited funding state is BUY_DOMINANT in the cited flow item.",
    "Flow and funding are described as BUY_DOMINANT.",
])
def test_b3_a_flow_state_is_never_an_assertion_about_funding(statement):
    rejected(statement, [FLOW, FUNDING])


# B4 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "Funding is negative in the cited window.",
    "Funding indicates longs receive payments from shorts.",
    "Funding is positive in the cited window.",
    "Funding improved in the cited window.",
    "Funding indicates shorts pay longs in the cited window.",
])
def test_b4_funding_statements_must_match_the_evidence_polarity(statement):
    rejected(statement, [FUNDING])          # the evidence is LONGS_PAY_SHORTS
    assert verdict(put("Funding indicates longs pay shorts in the cited window.", [FUNDING])) == "VALID"


# B5 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "Buyers were liquidated in the cited window.", "Sellers were liquidated in the cited window.",
    "Liquidations occurred in the cited window.", "Longs were liquidated in the cited window.",
    "Flow shows that buyers faced liquidation in the cited window.",
])
def test_b5_flow_is_not_liquidation_evidence(statement):
    rejected(statement, [FLOW])


# B6 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "Volatility is not-high in the cited item.", "Volatility is nothigh in the cited item.",
    "Volatility is high in the cited item.", "Volatility is Not-High in the cited item.",
])
def test_b6_volatility_states_must_match_not_high(statement):
    rejected(statement, [VOL])
    assert verdict(put("Volatility is NOT_HIGH in the cited item.", [VOL])) == "VALID"


def test_b6_flow_state_must_match_buy_dominant():
    rejected("The flow state is balanced in the cited item.", [FLOW])
    rejected("The flow state is BALANCED in the cited item.", [FLOW])
    assert verdict(put("The flow state is BUY_DOMINANT in the cited item.", [FLOW])) == "VALID"


def test_b6_ordinary_uses_of_high_are_not_state_assertions():
    out = base(T2_REQ)
    out["summary"]["statement"] = f"A high degree of uncertainty remains in {out['summary']['refs'][0]} here."
    # default deny: free prose is not accepted, but the word "high" is not mistaken for a state label or an alias
    assert verdict(out, T2_SEL) == "UNSUPPORTED_CONSTRUCTION"
    assert verdict(put("A high degree of uncertainty remains for the cited item.", [FLOW])) == "UNSUPPORTED_CONSTRUCTION"
    assert verdict(put("High-volatility conditions are described by the cited item.", [FLOW])) == "UNSUPPORTED_CONSTRUCTION"


# B7 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement,refs", [
    ("Buy pressure weakened in the cited window.", [FLOW]), ("Buy pressure increased in the cited window.", [FLOW]),
    ("Funding improved in the cited window.", [FUNDING]), ("The trend strengthened in the cited window.", [DIRECTION]),
    ("Liquidations accelerated in the cited window.", [FLOW]), ("Flow turned BUY_DOMINANT in the cited window.", [FLOW]),
    ("Flow is now BUY_DOMINANT after the cited window.", [FLOW]),
    ("Volatility has risen in the cited window.", [VOL]),
])
def test_b7_one_observation_never_proves_a_change_over_time(statement, refs):
    rejected(statement, refs)


# B8 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement", [
    "C12 reports buy pressure in the cited item.", "C12 reports BUY_DOMINANT flow in the cited item.",
    "C13 reports that flow is BUY_DOMINANT in the cited item.",
])
def test_b8_a_category_never_vouches_for_another_categorys_state(statement):
    rejected(statement, [FLOW, MACRO])


@pytest.mark.parametrize("statement", [
    "The cited claim is verified fact.", "The cited claim is a fact in the claim note.",
    "The cited claim is true in the claim note here.", "The claim is confirmed by the cited claim note.",
])
def test_b8_a_claim_is_not_a_verified_fact(statement):
    assert verdict(put(statement, [], "claim")) == "CLAIM_CITED_AS_FACT", statement


# independent probes (not from the audit) -------------------------------------------------------------------------
ADVICE_PROBES = [
    "Acquisition of the asset looks appealing given the cited item here.",
    "The prudent course is to purchase on the cited evidence from the item.",
    "Going with the cited flow means purchasing more Bitcoin here.",
    "The cited item argues that traders should add to their position.",
    "A sale of the holdings seems advisable given the cited evidence.",
    "Divesting the asset seems the wiser option given the cited evidence.",
    "Shorting Bitcoin looks favorable given the cited item from the evidence.",
    "Cash is a better place to be given the cited evidence from the item.",
    "Bitcoin is a strong candidate for new capital given the cited item.",
    "Pick up some Bitcoin given the cited evidence from the item here.",
    "Flow is BUY_DOMINANT; Bitcoin deserves fresh capital on that basis.",
    "Funding indicates longs pay shorts; paring long exposure makes sense.",
    "Funding indicates longs pay shorts, which makes short positions attractive.",
    "The cited flow state is BUY_DOMINANT, so Bitcoin merits fresh purchases.",
    "Trimming risk makes sense given the cited evidence from the item here.",
    "Stay patient and let the cited evidence play out from the item here.",
]
LEGIT_PROBES = [
    ("Flow is BUY_DOMINANT in the cited window.", [FLOW]),
    ("The cited flow state is BUY_DOMINANT in E004.", [FLOW]),
    ("C10 classified the funding state as LONGS_PAY_SHORTS.", [FUNDING]),
    ("The cited regime is TRENDING_UP in the cited item.", [REGIME]),
    ("The cited direction state is TRENDING_UP at the evaluation time.", [DIRECTION]),
    ("The cited volatility state is NOT_HIGH at the evaluation time.", [VOL]),
    ("Crowding evidence is unavailable for the cited category.", [FLOW]),
    ("Flow evidence is partial in the cited category.", [FLOW]),
    ("The cited sell-side pressure reflects BUY_DOMINANT.", []),                     # deliberately wrong: see below
]


def test_independent_advice_probes_are_rejected():
    wrong = [s for s in ADVICE_PROBES if verdict(put(s, [FLOW, FUNDING, DIRECTION])) == "VALID"]
    assert wrong == []


def test_independent_legitimate_probes_are_accepted_and_wrong_ones_rejected():
    for statement, refs in LEGIT_PROBES[:-1]:
        assert verdict(put(statement, refs)) == "VALID", statement
    assert verdict(put("The cited sell-side pressure reflects BUY_DOMINANT.", [FLOW])) != "VALID"


def test_validation_is_deterministic():
    out = put("Funding indicates longs pay shorts in the cited window.", [FUNDING])
    assert len({verdict(out) for _ in range(5)}) == 1
    out = put("Kindly purchase Bitcoin given the cited evidence.", [FLOW])
    assert len({verdict(out) for _ in range(5)}) == 1 and verdict(out) != "VALID"


def test_complete_t1_and_t2_responses_remain_acceptable():
    assert verdict(base()) == "VALID"
    assert verdict(base(T2_REQ), T2_SEL) == "VALID"


# measured probe set: written independently of the audit examples ------------------------------------------------
LIQ = ids(T1_REQ, subject="liquidity")[0]
MEASURED_PROHIBITED = [
 "Patience is advisable here given the cited evidence from the item.", "Now looks like the moment to act on the cited evidence.",
 "The cited evidence supports acting on it now from the item here.", "Position accordingly given the cited evidence from the item.",
 "Capital should flow in given the cited evidence from the item.", "One approach is to reduce exposure given the cited evidence.",
 "Participants might step aside given the cited evidence from the item.", "Cautious holders may sit this out given the cited evidence.",
 "Take a defensive stance given the cited evidence from the item.", "Defensive positioning is warranted given the cited evidence.",
 "Prefer cash given the cited evidence from the item here.", "The cited evidence is a reason to be cautious from the item.",
 "Better safe than sorry given the cited evidence from the item.", "Risk appetite should be lowered given the cited evidence.",
 "This is the time for patience given the cited evidence here.", "The cited evidence is an invitation to accumulate more.",
 "Flow is BUY_DOMINANT; participants are wise to lean in.", "Funding indicates longs pay shorts; fading longs makes sense.",
 "The cited direction state is TRENDING_UP; ride the move.", "The cited regime is TRENDING_UP, so stay with the trend.",
 "Stablecoins look safer than Bitcoin given the cited evidence.", "Selling into strength is typical after this evidence.",
 "Bitcoin is expected to extend gains given the cited evidence.", "The cited flow is BUY_DOMINANT which bodes well for price.",
 "An ideal entry is near given the cited evidence from the item.", "Traders ought to respect the cited evidence from the item.",
 "Buyers are in control, so upside is likely given the item.", "Do nothing rash given the cited evidence from the item here.",
 "Go with the cited evidence and ride the wave from the item.", "Funding indicates longs pay shorts; that favors bears.",
]
MEASURED_LEGITIMATE = [
    ("Flow is BUY_DOMINANT at the evaluation time.", [FLOW]),
    ("C10 classified flow as BUY_DOMINANT at the evaluation time.", [FLOW]),
    ("The cited funding state is LONGS_PAY_SHORTS on the 1h interval.", [FUNDING]),
    ("Funding indicates longs pay shorts at the evaluation time.", [FUNDING]),
    ("The cited direction state is TRENDING_UP and the cited volatility state is NOT_HIGH.", [DIRECTION, VOL]),
    ("Liquidity is NOT_THIN in the cited item.", [LIQ]), ("The cited regime is TRENDING_UP at the evaluation time.", [REGIME]),
    ("Crowding evidence is unavailable in the cited category.", [FLOW]),
    ("Funding evidence is described by the cited item.", [FUNDING]),
    ("Flow evidence is partial in the cited item.", [FLOW]),
    ("The category CAT:C12_ETF is excluded.", [FLOW, "CAT:C12_ETF"]),
    ("The evidence at the evaluation time is described in E004.", [FLOW]),
    ("C10 evidence is described.", [FLOW]),
    ("The BTC market state was BUY_DOMINANT.", [FLOW]),
    ("The cited buy-side pressure reflects BUY_DOMINANT.", [FLOW]),
]


def test_measured_probe_set_has_no_wrong_accepts_and_no_wrong_rejects():
    wrongly_accepted = [s for s in MEASURED_PROHIBITED if verdict(put(s, [FLOW, FUNDING, DIRECTION])) == "VALID"]
    wrongly_rejected = [(s, verdict(put(s, r))) for s, r in MEASURED_LEGITIMATE if verdict(put(s, r)) != "VALID"]
    assert (len(MEASURED_PROHIBITED), len(MEASURED_LEGITIMATE)) == (30, 15)
    assert wrongly_accepted == [] and wrongly_rejected == []


def _value(subject):
    item = next(i for i in T1_REQ["structured"] if i["subject"] == subject)
    return item["evidence_id"], item["values"][0]


def test_numeric_statements_need_the_values_own_subject_and_stay_bound():
    fid, fv = _value("funding")
    text = fv["displays"][0]
    num = [(fv["value_id"], text)]
    assert verdict(put(f"The latest funding rate was {text} as a fraction in {fid}.", [fid], numbers=num)) == "VALID"
    assert verdict(put(f"The BTC funding rate was {text} in {fid}.", [fid], numbers=num)) == "VALID"
    # the same funding value described as a flow value, or with a trading conclusion, is rejected
    for bad in (f"The cited flow value is {text} in {fid}.", f"The funding rate was {text}, so purchase Bitcoin.",
                f"The funding rate was {text} in {fid}, which makes shorting attractive.",
                f"The funding rate was {text} in {fid}; buy pressure weakened."):
        assert verdict(put(bad, [fid], numbers=num)) != "VALID", bad
    gid, gv = _value("flow")
    gtext = gv["displays"][0]
    assert verdict(put(f"The window buy volume was {gtext} BTC in {gid}.", [gid],
                       numbers=[(gv["value_id"], gtext)])) == "VALID"
    assert verdict(put(f"The funding rate was {gtext} BTC in {gid}.", [gid], numbers=[(gv["value_id"], gtext)])) != "VALID"


def test_a_neutral_clause_may_follow_an_assertion_but_nothing_else():
    assert verdict(put(f"Flow is BUY_DOMINANT in {FLOW}; the evidence is cited in {FLOW}.", [FLOW])) == "VALID"
    assert verdict(put(f"Flow is BUY_DOMINANT in {FLOW}; ride the move.", [FLOW])) != "VALID"
    assert verdict(put(f"Flow is BUY_DOMINANT in {FLOW}; the market looks strong.", [FLOW])) != "VALID"


def test_modals_are_admitted_only_when_negated():
    assert verdict(put("The cited item might reflect a change in the evidence here.", [FLOW])) != "VALID"
    # a negated modal passes the modal rule, but free prose still fails default deny
    assert verdict(put("The claim could not be verified from the cited item.", [FLOW])) == "UNSUPPORTED_CONSTRUCTION"


def test_every_form_the_prompt_teaches_is_accepted():
    """The prompt and the validator must agree: each example sentence the prompt gives validates when supported."""
    fid, fv = _value("funding")
    text = fv["displays"][0]
    cases = [
        ("The cited flow state is BUY_DOMINANT.", [FLOW], ()), ("Flow is BUY_DOMINANT.", [FLOW], ()),
        ("C10 classified flow as BUY_DOMINANT.", [FLOW], ()), ("The BTC market state was BUY_DOMINANT.", [FLOW], ()),
        ("The cited buy-side pressure reflects BUY_DOMINANT.", [FLOW], ()),
        ("Funding indicates longs pay shorts.", [FUNDING], ()),
        (GOOD, [DIRECTION], ()), ("Flow evidence is described.", [FLOW], ()),
        ("Crowding evidence is unavailable.", [FLOW], ()),
        (f"The latest funding rate was {text} as a fraction in {fid}.", [fid], [(fv["value_id"], text)]),
    ]
    for statement, refs, nums in cases:
        assert verdict(put(statement, refs, numbers=nums)) == "VALID", statement
    for form in ('"The cited X state is S."', '"The BTC market state was BUY_DOMINANT."',
                 '"The cited buy-side pressure reflects BUY_DOMINANT."', '"Funding indicates longs pay shorts."'):
        assert form in SYSTEM_PROMPT, form
    assert "Default deny" in SYSTEM_PROMPT and "negated" in SYSTEM_PROMPT


from traid.ai.prompts import SYSTEM_PROMPT  # noqa: E402
