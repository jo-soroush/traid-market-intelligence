"""F6: strict whole-token grammar (G1-G5), exercised on the grammar functions and on real request
contexts built from real C10/C12/C13 reports."""
from decimal import Decimal
import json

import pytest

from ai_support import T, T1, T2, cpi_claim, fomc_claim, macro, market_state, news, offline  # noqa: F401
from test_regime import derivatives, rates
from traid.ai import EvidenceInputs, select
from traid.ai.grammar import (
    Bound, GrammarError, check_statement, classify, is_literal_candidate, tokenize,
)
from traid.ai.selection import displays

LITS = frozenset({"E004", "CUUR0000SA0", "2026-09", "LOWER", "SR-NASDAQ-2023-016", "1h", "2026-10-15T12:30:00Z"})
PCT = Bound("E009.V1", ("5", "5%"), "percent", None, "E009")
NEG = Bound("E009.V2", ("-0.0012", "-0.0012%"), "percent", None, "E009")
LOW = Bound("E005.V1", ("4.25", "4.25%"), "percent", "E005.G1", "E005")
HIGH = Bound("E005.V2", ("4.5", "4.5%"), "percent", "E005.G1", "E005")
CPI = Bound("E003.V1", ("337.1004",), "index, 1982-84=100", None, "E003")
PP = Bound("E005.V6", ("-0.25",), "percentage points", None, "E005")
INDEX = {b.value_id: b for b in (PCT, NEG, LOW, HIGH, CPI, PP)}
ALL = frozenset(INDEX)


def code(statement, numbers=(), literals=LITS, citable=ALL):
    try:
        check_statement(statement, literals, list(numbers), INDEX, citable)
    except GrammarError as e:
        return e.code
    return "OK"


# ------------------------------------------------------------------ Codex counterexamples
@pytest.mark.parametrize("statement", [
    'The source rate is -"5%" for the period.',            # Codex audit 6
    'The range is "4.25%"+"4.5%" for this decision.',      # Codex audit 6
    "Funding is －5% for the period.",                 # Codex audit 5: FULLWIDTH HYPHEN-MINUS
    "Funding is ﹣5% for the period.",                 # Codex audit 5: SMALL HYPHEN-MINUS
])
def test_codex_sign_and_quote_counterexamples_are_rejected(statement):
    assert code(statement, [("E009.V1", "5%")]) == "UNSUPPORTED_CHARACTER"


UNICODE_SIGNS = ["−", "－", "﹣", "‐", "‑", "‒", "–", "—", "―", "­",
                 "˗", "⁻", "₋", "➖", "＋", "﹢", "±", "∓", "ー", "​",
                 "⁠", "﻿", " ", " "]


@pytest.mark.parametrize("sign", UNICODE_SIGNS)
def test_every_unicode_sign_variant_is_rejected_before_any_number_or_literal(sign):
    assert code(f"Funding is {sign}5% for the period.", [("E009.V1", "5%")]) == "UNSUPPORTED_CHARACTER"
    assert code(f"Funding is {sign}E004 for the period.") == "UNSUPPORTED_CHARACTER"       # next to a literal
    assert code(f"Funding is E0{sign}04 for the period.") == "UNSUPPORTED_CHARACTER"       # inside one


def test_unsupported_character_reports_the_code_point():
    with pytest.raises(GrammarError) as e:
        tokenize("Funding is −5% here.", LITS)
    assert e.value.detail == "U+2212"


@pytest.mark.parametrize("statement,expected", [
    ('Funding is "5%" for the period.', "UNSUPPORTED_CHARACTER"),
    ("Funding=999% for the period here.", "UNSUPPORTED_CHARACTER"),
    ("The change was 3.4-3.2=0.2. here.", "UNSUPPORTED_CHARACTER"),
    ("Funding is 5%! for the period.", "UNSUPPORTED_CHARACTER"),
    ("The range is 4.25%+4.5% for now.", "UNSUPPORTED_CHARACTER"),
    ("Funding is $5 for the period here.", "UNSUPPORTED_CHARACTER"),
    ("Funding is 5_% for the period here.", "UNSUPPORTED_CHARACTER"),
    ("Funding is '5%' for the period.", "TOKEN_INVALID"),
    ("Funding is (5%) for the period.", "TOKEN_INVALID"),
    ("Funding is -(5%) for the period.", "TOKEN_INVALID"),
    ("Funding is -'5% for the period.", "TOKEN_INVALID"),
    ("Funding is - 5% for the period.", "TOKEN_INVALID"),
    ("Funding is --5% for the period.", "TOKEN_INVALID"),
    ("Funding is 5%- for the period.", "TOKEN_INVALID"),
    ("Funding is .5% for the period.", "TOKEN_INVALID"),        # never re-read as 5%
    ("Funding is 5.% for the period.", "TOKEN_INVALID"),
    ("The notional is 1e3 in total here.", "TOKEN_INVALID"),    # never split into 1 and 3
    ("The notional is 1E3 in total here.", "TOKEN_INVALID"),
    ("The notional is 1,000 in total here.", "TOKEN_INVALID"),
    ("The value is (999). for this.", "TOKEN_INVALID"),
    ("Filing SR-NASDAQ-2023-016x remains cited.", "TOKEN_INVALID"),
    ("The period -2026-09 is cited here.", "TOKEN_INVALID"),
    ("Q3 looked different in this window.", "TOKEN_INVALID"),
    ("Funding is 5% (as stated) here.", "TOKEN_INVALID"),       # over-rejection: fails closed
    ("Funding  is 5% for the period.", "TOKEN_INVALID"),        # double space
    (" Funding is 5% for the period.", "TOKEN_INVALID"),        # leading space
])
def test_invalid_numeric_and_character_forms(statement, expected):
    assert code(statement, [("E009.V1", "5%")]) == expected


def test_word_arithmetic_number_words_and_comparisons():
    assert code("One less one equals zero in this comparison.") == "NUMBER_WORD"         # Codex audit 4
    assert code("The value is nine percent of the base.") == "NUMBER_WORD"
    assert code("The twenty-five cases are listed in E004.") == "NUMBER_WORD"
    assert code("The difference is shown in E004 for now.") == "ARITHMETIC_WORD"
    assert code("The computed change is shown in E004.") == "ARITHMETIC_WORD"
    assert code("The value is equal to the earlier one.") == "NUMBER_WORD"
    assert code("The value is equal to the earlier figure.") == "ARITHMETIC_WORD"
    assert code("CUUR0000SA0 rose to 337.1004 in the latest capture.", [("E003.V1", "337.1004")]) == "DERIVED_COMPARISON"
    assert code("Funding is lower at 5% for the period.", [("E009.V1", "5%")]) == "DERIVED_COMPARISON"
    assert code("Activity rose during the cited window in E004.") == "OK"          # no number: no comparison claim


def test_count_order_groups_and_bindings():
    assert code("The undeclared value 5 appears here.") == "UNBOUND_NUMBER"
    assert code("CPI moved from 337.1004 to 5 in this window.",
                [("E003.V1", "337.1004"), ("E009.V1", "5")]) == "MULTI_VALUE_STATEMENT"
    assert code("The range is 4.25% to 4.5%, as stated.", [("E005.V1", "4.25%"), ("E005.V2", "4.5%")]) == "OK"
    assert code("The range is 4.25% to 4.5%, as stated.", [("E005.V2", "4.5%"), ("E005.V1", "4.25%")]) == "DECLARATION_MISMATCH"
    assert code("The value 4.250% is the first endpoint here.", [("E005.V1", "4.250%")]) == "DISPLAY_MISMATCH"
    assert code("The value 4.3% is the first endpoint here.", [("E005.V1", "4.3%")]) == "DISPLAY_MISMATCH"
    assert code("The value 4.25% is the first endpoint here.", [("E005.V1", "4.3%")]) == "DECLARATION_MISMATCH"
    assert code("The index value was 337.1004% at receipt.", [("E003.V1", "337.1004%")]) == "UNIT_MISMATCH"
    assert code("The index value was 337.1004 percent at receipt.", [("E003.V1", "337.1004")]) == "UNIT_MISMATCH"
    assert code("The change was -0.25 percentage points here.", [("E005.V6", "-0.25")]) == "OK"
    assert code("The change was -0.25 bps in this decision.", [("E005.V6", "-0.25")]) == "UNIT_MISMATCH"
    assert code("CPI (CUUR0000SA0) for 2026-09 was 337.1004.", [("E003.V1", "337.1004")],
                citable=frozenset({"E005.V1"})) == "UNCITED_VALUE"


@pytest.mark.parametrize("statement,numbers", [
    ("Funding over 1h was -0.0012%, captured 2026-10-15T12:30:00Z.", [("E009.V2", "-0.0012%")]),
    ("The change was -0.25 percentage points.", [("E005.V6", "-0.25")]),
    ("CPI (CUUR0000SA0) for 2026-09 was 337.1004.", [("E003.V1", "337.1004")]),
    ("The committee chose LOWER, setting 4.25% to 4.5% as the range.", [("E005.V1", "4.25%"), ("E005.V2", "4.5%")]),
    ("The range is 4.25% to 4.5%, as stated.", [("E005.V1", "4.25%"), ("E005.V2", "4.5%")]),
    ("Filing SR-NASDAQ-2023-016 remains cited in E004.", []),
    ("Funding is 5%.", [("E009.V1", "5%")]),
])
def test_legitimate_sourced_statements_pass(statement, numbers):
    assert code(statement, numbers) == "OK"


def test_literals_are_exact_whole_tokens_and_never_bare_numbers():
    assert classify("LOWER,", LITS).kind == "LITERAL"
    assert classify("lower", LITS).kind == "WORD"                  # not the code literal: G3 applies
    assert classify("(CUUR0000SA0)", LITS).kind == "LITERAL"
    with pytest.raises(GrammarError):
        classify("(CUUR0000SA0", LITS)                              # parentheses both or neither
    assert not is_literal_candidate("5") and not is_literal_candidate("-0.25%") and not is_literal_candidate("4.5")
    assert is_literal_candidate("2026-09") and is_literal_candidate("SR-NASDAQ-2023-016")
    # NUM-33: a literal only counts when it comes from the cited items
    assert code("CPI (CUUR0000SA0) for 2026-09 is cited.", literals=frozenset({"E004"})) == "TOKEN_INVALID"


@pytest.mark.parametrize("value,unit", [(Decimal("1E+3"), "USD"), (Decimal("0.50"), "percent"),
                                         (Decimal("-0.000012"), "fraction"), (Decimal("336.940"), "index"),
                                         (Decimal("4"), "percent"), (Decimal("-0E-7"), "USD"),
                                         (Decimal("0.0097087378640776699029126213592233009708737864077670"), "fraction")])
def test_num31_generated_displays_are_fixed_point(value, unit):
    import re
    out = displays(value, unit)
    assert out and all(re.fullmatch(r"-?\d+(\.\d+)?%?", d) and "E" not in d for d in out)
    assert all(Decimal(d.rstrip("%")) == value for d in out)
    assert any(d.endswith("%") for d in out) == (unit == "percent")


# ------------------------------------------------------------------ on real request contexts
def _ctx(task=T2, **inputs):
    sel = select(task, T, EvidenceInputs(**inputs))
    assert sel.skip is None
    return sel


def test_real_context_literals_never_contain_claim_text_or_bare_numbers():
    rep = macro()
    sel = _ctx(macro=rep, news=news([cpi_claim(), fomc_claim()], rep))
    every = set().union(*sel.context.literals.values()) | sel.context.global_literals
    assert not any(is_literal_candidate(x) is False for x in every)
    assert "336.94" not in every and "3.75-4" not in every and "RAISE" in every     # claim_asserted never a literal
    req = json.loads(sel.request_json)
    assert all(f["claim_asserted"] not in every or f["claim_asserted"] in ("RAISE",)
               for c in req["assessed_claims"] for fr in c["frames"] for f in fr["facts"])


def test_real_negative_funding_value_is_bindable_as_ascii_negative():
    ms = market_state(derivatives=derivatives(fs=rates(["-0.0001"] * 4)))
    sel = _ctx(T1, market_state=ms)
    funding = next(i for i in sel.request.structured if i.subject == "funding")
    v = next(v for v in funding.values if v.field_path.endswith("funding.latest_rate"))
    assert v.displays == ("-0.0001",)
    tokens_ok = check_statement(f"The latest funding rate in {funding.evidence_id} was -0.0001 per hour.",
                                sel.context.global_literals | sel.context.literals[funding.evidence_id],
                                [(v.value_id, "-0.0001")], sel.context.values, frozenset({v.value_id}))
    assert [t.kind for t in tokens_ok].count("NUMBER") == 1
