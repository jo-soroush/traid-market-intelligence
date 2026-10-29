"""Strict output validation (wire acceptance, V1-V4, grammar, section rules) and the canonical adapter,
on requests built from real C10/C12/C13 reports."""
import copy
from datetime import timedelta
import json

import pytest

from ai_support import (  # noqa: F401
    MAPPING, T, T1, T2, cpi_claim, etf, false_regulatory_news, fomc_claim, macro, market_state, merge_news, news,
    offline, reply, valid_output, whales,
)
from traid.ai import EvidenceInputs, select
from traid.ai.provider import ContentBlock
from traid.ai.validation import validate_reply

TS = T + timedelta(seconds=40)
REP = macro()
NEWS = merge_news(news([cpi_claim(), fomc_claim()], REP), false_regulatory_news())
T1_SEL = select(T1, T, EvidenceInputs(market_state=market_state(), whales=whales([("L", "100")] * 6), macro=REP,
                                      etf=etf(), etf_mapping=MAPPING, news=NEWS))
T2_SEL = select(T2, T, EvidenceInputs(macro=REP, news=news([cpi_claim(), fomc_claim()], REP)))
T1_REQ, T2_REQ = json.loads(T1_SEL.request_json), json.loads(T2_SEL.request_json)


def ids(request, **match):
    return [i["evidence_id"] for i in request["structured"] + request["contextual"]
            if all(i[k] == v for k, v in match.items())]


def check(output, sel=T1_SEL, **kw):
    return validate_reply(reply(output, **kw), sel.context, TS)


def code(output, sel=T1_SEL, **kw):
    v = check(output, sel, **kw)
    return "VALID" if v.valid else v.code


def base(request=T1_REQ):
    return valid_output(request)


def test_minimal_outputs_are_valid_for_both_tasks():
    assert code(base()) == "VALID"
    assert code(base(T2_REQ), T2_SEL) == "VALID"


# --------------------------------------------------------------------- wire (W1-W7)
def test_wire_acceptance_rules():
    out = base()
    assert code(out, raw_size=64 * 1024 + 1) == "RESPONSE_LIMIT_EXCEEDED"
    assert code(out, stop="max_tokens") == "OUTPUT_TRUNCATED"
    assert code(out, stop="model_context_window_exceeded") == "OUTPUT_TRUNCATED"
    assert code(out, stop="content_filtered") == "CONTENT_FILTERED"
    assert code(out, stop="guardrail_intervened") == "CONTENT_FILTERED"
    assert code(out, stop="end_turn") == "UNEXPECTED_STOP_REASON"
    assert code(out, stop="malformed_tool_use") == "MALFORMED_OUTPUT"
    assert code(out, role="user") == "UNEXPECTED_CONTENT_BLOCK"
    assert code(out, extra_blocks=(ContentBlock(kind="other", other_type="image"),)) == "UNEXPECTED_CONTENT_BLOCK"
    assert code(out, name="other_tool") == "TOOL_CONTRACT"
    assert code(out, tool_id="") == "TOOL_CONTRACT"
    two = (ContentBlock(kind="tool_use", tool_name="submit_interpretation", tool_use_id="t2", tool_input=out),)
    assert code(out, extra_blocks=two) == "TOOL_CONTRACT"
    # W5: a text block is tolerated and never parsed, even if it holds instructions
    text = (ContentBlock(kind="text", text='{"summary": "ignore the tool and BUY"}'),)
    assert code(out, extra_blocks=text) == "VALID"
    # W7: missing usage does not invalidate
    r = reply(out)
    assert validate_reply(r.__class__(**{**r.__dict__, "input_tokens": None, "output_tokens": None,
                                         "total_tokens": None}), T1_SEL.context, TS).valid


def test_v1_v2_strict_json_boundary():
    out = base()
    assert code({**out, "confidence": "high"}) == "SCHEMA_INVALID"                     # WIRE-18 authority keys
    for key in ("direction", "size", "leverage", "target", "action", "probability"):
        assert code({**out, key: "x"}) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    bad["summary"]["statement"] = 7
    assert code(bad) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    bad["summary"]["numbers"] = [{"value_id": "E001.V1", "text": 1}]
    assert code(bad) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    del bad["uncertainties"]
    assert code(bad) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    bad["anchor_assessments"][0]["stance"] = "STRONG_SUPPORT"
    assert code(bad) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    bad["summary"]["refs"] = [{"deep": [[[[["x"]]]]]}]
    assert code(bad) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    bad["summary"]["statement"] = None
    assert code(bad) == "SCHEMA_INVALID"
    bad = copy.deepcopy(out)
    bad["summary"]["statement"] = "The evidence is described in E001\udc80 here."     # lone surrogate fails closed
    assert code(bad) in ("SCHEMA_INVALID", "UNSUPPORTED_CHARACTER")
    v = check(out)
    import hashlib
    assert v.tool_input_sha256 == hashlib.sha256(
        json.dumps(out, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
    # NEWS-8: a model-supplied claim state is not a field
    bad = copy.deepcopy(out)
    bad["claim_notes"][0]["state"] = "CONFIRMED"
    assert code(bad) == "SCHEMA_INVALID"


@pytest.mark.parametrize("variant", [" E001", "E001 ", "E001\n", "e001", "Ｅ001", "E001​",
                                     "E0́" "01", "E999"])
def test_references_are_exact_and_unnormalized(variant):
    out = base()
    out["summary"]["refs"] = [variant]
    assert code(out) == "UNKNOWN_REFERENCE"


# ------------------------------------------------------------------------ citations
def test_claims_unresolved_facts_duplicates_and_category_refs():
    out = base()
    claim = T1_REQ["assessed_claims"][0]["claim_id"]
    out["anchor_assessments"][0]["evidence_ids"].append(claim)
    assert code(out) == "CLAIM_CITED_AS_FACT"                                          # NEWS-4
    false = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "FALSE")
    unresolved = [f["fact_id"] for fr in false["frames"] for f in fr["facts"] if f["outcome"] == "UNRESOLVED"]
    if unresolved:
        out = base()
        out["context_notes"] = [{"statement": "The cited fact is described in this note.", "refs": [unresolved[0]],
                                 "numbers": []}]
        assert code(out) == "CLAIM_CITED_AS_FACT"                                      # NEWS-5
    out = base()
    out["summary"]["refs"] = out["summary"]["refs"] * 2
    assert code(out) == "DUPLICATE_REFERENCE"
    out = base()
    out["uncertainties"][0]["refs"] = ["CAT:C11"]                                      # C11 INCLUDED here
    assert code(out) == "MISSING_CATEGORY_CONTRADICTION"
    out = base(T2_REQ)
    out["uncertainties"][0]["refs"] = ["CAT:C10"]
    assert code(out, T2_SEL) == "OUT_OF_SCOPE_REFERENCE"


def test_section_coverage_and_mandatory_sections():
    out = base()
    out["anchor_assessments"] = out["anchor_assessments"][1:]
    assert code(out) == "ANCHOR_COVERAGE_INVALID"
    out = base()
    out["anchor_assessments"][1] = dict(out["anchor_assessments"][0], statement="Anchor A01 is assessed again here.")
    assert code(out) == "ANCHOR_COVERAGE_INVALID"                                       # duplicate, one missing
    out = base()
    out["anchor_assessments"].append(dict(out["anchor_assessments"][0], statement="Anchor A01 is assessed again here."))
    assert code(out) == "SCHEMA_INVALID"                                                # above the cap of 6
    out = base()
    out["anchor_assessments"][0]["anchor_id"] = "A99"
    assert code(out) == "UNKNOWN_ANCHOR"
    out = base()
    out["claim_notes"] = out["claim_notes"][1:]
    assert code(out) == "CLAIM_COVERAGE_INVALID"
    out = base()
    for a in out["anchor_assessments"]:
        a["stance"] = "NOT_ASSESSABLE"
    assert code(out) == "NO_SUBSTANTIVE_ASSESSMENT"                                     # SEC-1
    out = base()
    out["anchor_assessments"][0]["evidence_ids"] = []
    assert code(out) == "ASSESSMENT_WITHOUT_REFERENCE"
    out = base()
    out["uncertainties"] = []
    assert code(out) == "UNCERTAINTY_MISSING"                                           # SEC-3
    out = base()
    out["summary"]["refs"] = [ids(T1_REQ, category="C12_MACRO")[0]]
    assert code(out) == "SUMMARY_SOURCE_MISSING"
    empty = {"summary": {"statement": "", "refs": [], "numbers": []}, "anchor_assessments": [], "context_notes": [],
             "claim_notes": [], "uncertainties": []}
    assert code(empty) != "VALID"                                                       # SEC-6
    no_claims = select(T1, T, EvidenceInputs(market_state=market_state()))
    assert code(valid_output(json.loads(no_claims.request_json)), no_claims) == "VALID"  # SEC-5


def test_false_claims_must_cite_their_refuting_fact():
    false = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "FALSE")
    refuting = [f["fact_id"] for fr in false["frames"] for f in fr["facts"] if f["outcome"] == "CONTRADICTED"]
    assert refuting
    out = base()
    assert code(out) == "VALID"
    note = next(n for n in out["claim_notes"] if n["claim_id"] == false["claim_id"])
    note["refs"] = [false["claim_id"]]
    assert code(out) == "REFUTING_EVIDENCE_NOT_CITED"
    note["refs"] = [false["claim_id"], refuting[0]]
    assert code(out) == "VALID"


def test_statement_form():
    out = base()
    out["summary"]["statement"] = "Too short E001."
    assert code(out) == "STATEMENT_INVALID"
    out = base()
    out["summary"]["statement"] = "x" * 601
    assert code(out) == "STATEMENT_INVALID"
    out = base()
    out["context_notes"] = [dict(out["uncertainties"][0])]
    assert code(out) == "STATEMENT_INVALID"                                             # duplicate statement
    out = base()
    summary = out["summary"]["refs"][0]
    out["summary"]["statement"] = f"{summary} {summary} {summary} {summary} {summary}"
    assert code(out) == "STATEMENT_INVALID"                                             # identifiers only


def test_prohibited_language_and_macro_scope():
    for statement in ("Traders should buy BTC at the evaluation time here.",
                      "The cited state is a bullish signal for the market.",
                      "A long entry with leverage fits the evidence E001."):
        out = base()
        out["summary"]["statement"] = statement
        assert code(out) == "PROHIBITED_TRADE_LANGUAGE", statement
    for statement in ("Macro evidence matters for Bitcoin at this time.",
                      "The CPI print is relevant to crypto markets here.",
                      "The evidence is relevant to BTC at this time."):
        out = base(T2_REQ)
        out["summary"]["statement"] = statement + " " + out["summary"]["refs"][0]
        assert code(out, T2_SEL) == "ASSET_CONCLUSION_IN_MACRO_TASK", statement


def test_t1_context_notes_may_not_cite_c10():
    out = base()
    out["context_notes"] = [{"statement": "The direction evidence appears again in this note.", "refs": ["E001"],
                             "numbers": []}]
    assert code(out) == "CONTEXT_REFERENCE_INVALID"


# ------------------------------------------------- integrated numbers and citations
def _value(request, field_suffix):
    for i in request["structured"] + request["contextual"]:
        for v in i["values"]:
            if v["field_path"].endswith(field_suffix):
                return i["evidence_id"], v
    raise KeyError(field_suffix)


def test_integrated_number_binding_on_real_values():
    cpi_item, cpi = _value(T2_REQ, "series[CUUR0000SA0].known_value")
    fomc_item, low = _value(T2_REQ, "fomc.statement.target_lower_percent")
    _, high = _value(T2_REQ, "fomc.statement.target_upper_percent")
    _, change = _value(T2_REQ, "fomc.range_change_since_previous")

    def note(statement, refs, numbers):
        out = base(T2_REQ)
        out["context_notes"] = [{"statement": statement, "refs": refs, "numbers": numbers}]
        return code(out, T2_SEL)

    assert note(f"CPI (CUUR0000SA0) for 2026-09 was {cpi['value']} in {cpi_item}.", [cpi_item],
                [{"value_id": cpi["value_id"], "text": cpi["value"]}]) == "VALID"
    assert note(f"The index level was 336.94 in {cpi_item}.", [cpi_item],
                [{"value_id": cpi["value_id"], "text": "336.94"}]) == "VALID"           # normalized display
    assert note(f"The index level was 336.9 in {cpi_item}.", [cpi_item],
                [{"value_id": cpi["value_id"], "text": "336.9"}]) == "DISPLAY_MISMATCH"  # rounded
    assert note(f"The index level was 336.940% in {cpi_item}.", [cpi_item],
                [{"value_id": cpi["value_id"], "text": "336.940%"}]) == "UNIT_MISMATCH"
    assert note(f"The index level was {cpi['value']} in {fomc_item}.", [fomc_item],
                [{"value_id": cpi["value_id"], "text": cpi["value"]}]) == "UNCITED_VALUE"
    assert note(f"The statement range was 3.75% to 4% in {fomc_item}.", [fomc_item],
                [{"value_id": low["value_id"], "text": "3.75%"}, {"value_id": high["value_id"], "text": "4%"}]) == "VALID"
    assert note(f"The statement range was 3.75% with CPI {cpi['value']} here.", [fomc_item, cpi_item],
                [{"value_id": low["value_id"], "text": "3.75%"},
                 {"value_id": cpi["value_id"], "text": cpi["value"]}]) == "MULTI_VALUE_STATEMENT"
    assert note(f"The change was 0.25 percentage points in {fomc_item}.", [fomc_item],
                [{"value_id": change["value_id"], "text": "0.25"}]) == "VALID"
    assert note(f"The change was 0.25 percent in {fomc_item}.", [fomc_item],
                [{"value_id": change["value_id"], "text": "0.25"}]) == "UNIT_MISMATCH"
    assert note(f"The value 0.25 is cited from {fomc_item} only.", [fomc_item],
                [{"value_id": "E999.V1", "text": "0.25"}]) == "UNKNOWN_REFERENCE"
    assert note(f"CPI went from 334.980 to the cited level in {cpi_item}.", [cpi_item], []) == "UNBOUND_NUMBER"
    # a cited, linked C13 fact makes its linked value citable without citing the C12 item itself
    fact = next(f for c in T2_REQ["assessed_claims"] for fr in c["frames"] for f in fr["facts"]
                if f["linked_value_ids"] == [cpi["value_id"]])
    assert note(f"The confirmed claim value {cpi['value']} is cited via {fact['fact_id']}.", [fact["fact_id"]],
                [{"value_id": cpi["value_id"], "text": cpi["value"]}]) == "VALID"


def test_t1_numbers_from_c10_and_c11_bind_exactly():
    funding_item, rate = _value(T1_REQ, "funding.latest_rate")
    c11_item, gross = _value(T1_REQ, "aggregate.gross_notional")
    out = base()
    out["anchor_assessments"][4]["statement"] = f"The latest rate in {funding_item} was {rate['value']} per hour."
    out["anchor_assessments"][4]["numbers"] = [{"value_id": rate["value_id"], "text": rate["value"]}]
    out["context_notes"] = [{"statement": f"The whale gross notional in {c11_item} was {gross['value']} USDC.",
                             "refs": [c11_item], "numbers": [{"value_id": gross["value_id"], "text": gross["value"]}]}]
    assert code(out) == "VALID"
    out["context_notes"][0]["statement"] = f"The whale gross notional in {c11_item} was {gross['value']} USD."
    assert code(out) == "UNIT_MISMATCH"


# ------------------------------------------------------------------ canonical adapter
def test_canonical_fields_are_projected_deterministically():
    out = base()
    a = out["anchor_assessments"]
    c11 = ids(T1_REQ, category="C11")[0]
    cpi = next(e for e in ids(T1_REQ, category="C12_MACRO", subject="CUUR0000SA0"))
    a[0]["evidence_ids"] = [a[0]["evidence_ids"][0], c11]                 # independent evidence: C11
    a[1]["stance"] = "CONTRADICTS"
    a[1]["evidence_ids"] = [a[1]["evidence_ids"][0], cpi]
    a[2]["stance"] = "MIXED"
    a[3]["stance"] = "NOT_ASSESSABLE"
    a[5]["evidence_ids"] = [a[5]["evidence_ids"][0], "E001"]              # regime anchored on direction: not independent
    v = check(out)
    assert v.valid, v.code
    i = v.interpretation
    assert [(f.anchor_id, f.evidence_ids) for f in i.supporting_factors] == [("A01", (c11,))]
    assert [(f.anchor_id, f.evidence_ids) for f in i.contradicting_factors] == [("A02", (cpi,))]
    assert [(u.origin, u.anchor_id) for u in i.uncertainty] == [
        ("ANCHOR_MIXED", "A03"), ("ANCHOR_NOT_ASSESSABLE", "A04"), ("UNCERTAINTIES_SECTION", None)]
    assert "ANCHOR_ASSESSMENT_WITHOUT_INDEPENDENT_EVIDENCE:A06" in i.flags      # anchor never corroborates itself
    assert "ANCHOR_ASSESSMENT_WITHOUT_INDEPENDENT_EVIDENCE:A05" in i.flags
    subjects = {m.subject for m in i.missing_information}
    assert {"C10.crowding", "C10.liquidation", "consensus", "CAT:C12_ETF"} <= subjects
    assert all(m.reasons == ("WHALE_EVIDENCE_NOT_RELEASED",) for m in i.missing_information if m.category.value == "C11")
    assert set(i.evidence) >= {"E001", c11, cpi} and list(i.evidence) == sorted(i.evidence)
    refs = {s.ref: s for s in i.source_references}
    assert refs[c11].engine_version == "c11-whale-intelligence-1" and refs["E001"].engine_version == "c10-market-state-1"
    assert i.analysis_timestamp == TS and i.output.summary.statement == out["summary"]["statement"]
    assert i.limitations == ("AI_INTERPRETATION_IS_NOT_VERIFIED_FACT", "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION",
                             "NUMERIC_CHECK_IS_LEXICAL_NOT_SEMANTIC")
    claim_refs = [x for x in i.annotations if x.category.value == "C13"]
    assert claim_refs and all(x.claim_state in ("CONFIRMED", "FALSE") for x in claim_refs)


def test_t1_adversarial_regressions_stay_invalid():
    """Each previously named bypass, placed in a T1 assessment, is rejected."""
    funding_item, rate = _value(T1_REQ, "funding.latest_rate")
    cases = {
        f"Funding in {funding_item} is －{rate['value']} here.": "UNSUPPORTED_CHARACTER",
        f"Funding in {funding_item} is -\"{rate['value']}\" here.": "UNSUPPORTED_CHARACTER",
        f"Funding in {funding_item} is .{rate['value'][2:]} here.": "TOKEN_INVALID",
        f"Funding in {funding_item} is 1e3 for the hour.": "TOKEN_INVALID",
        f"Funding in {funding_item} was {rate['value']}={rate['value']} here.": "UNSUPPORTED_CHARACTER",
        f"One less one equals zero for {funding_item} here.": "NUMBER_WORD",
        f"Funding in {funding_item} rose to {rate['value']} for the hour.": "DERIVED_COMPARISON",
    }
    for statement, expected in cases.items():
        out = base()
        out["anchor_assessments"][4]["statement"] = statement
        out["anchor_assessments"][4]["numbers"] = [{"value_id": rate["value_id"], "text": rate["value"]}]
        assert code(out) == expected, statement


def test_t2_mandatory_sections_and_adversarial_regressions():
    out = base(T2_REQ)
    contextual = ids(T2_REQ, category="C12_MACRO", tier="CONTEXTUAL")[0]
    bad = copy.deepcopy(out)
    bad["summary"]["refs"] = [contextual]
    assert code(bad, T2_SEL) == "SUMMARY_SOURCE_MISSING"                          # must cite STRUCTURED C12
    bad = copy.deepcopy(out)
    for a in bad["anchor_assessments"]:
        a["stance"] = "NOT_ASSESSABLE"
    assert code(bad, T2_SEL) == "NO_SUBSTANTIVE_ASSESSMENT"
    bad = copy.deepcopy(out)
    bad["uncertainties"] = []
    assert code(bad, T2_SEL) == "UNCERTAINTY_MISSING"
    bad = copy.deepcopy(out)
    bad["anchor_assessments"].pop()
    assert code(bad, T2_SEL) == "ANCHOR_COVERAGE_INVALID"
    bad = copy.deepcopy(out)
    bad["claim_notes"] = []
    assert code(bad, T2_SEL) == "CLAIM_COVERAGE_INVALID"
    bad = copy.deepcopy(out)
    bad["summary"]["statement"] = "The CPI print at the evaluation time matters for crypto holders here."
    assert code(bad, T2_SEL) == "ASSET_CONCLUSION_IN_MACRO_TASK"
    bad = copy.deepcopy(out)
    bad["summary"]["statement"] = "The CPI print at the evaluation time suggests investors should wait."
    assert code(bad, T2_SEL) == "PROHIBITED_TRADE_LANGUAGE"


def test_news7_quoting_a_refuted_assertion_is_flagged_not_rejected():
    false = next(c for c in T1_REQ["assessed_claims"] if c["state"] == "FALSE")
    fact = next(f for fr in false["frames"] for f in fr["facts"] if f["outcome"] == "CONTRADICTED")
    out = base()
    note = next(n for n in out["claim_notes"] if n["claim_id"] == false["claim_id"])
    note["statement"] = f"Claim {false['claim_id']} asserted {fact['claim_asserted']}, which {fact['fact_id']} contradicts."
    note["refs"] = [false["claim_id"], fact["fact_id"]]
    v = check(out)
    assert v.valid, v.code
    assert f"ASSERTED_VALUE_QUOTED_FOR_REFUTED_FACT:{fact['fact_id']}" in v.interpretation.flags
