"""F6 whole-statement unit safety, through the complete C14 validator on requests built from real reports."""
from datetime import date, timedelta
import json

import pytest

from ai_support import (  # noqa: F401
    CPI_AT_T, MAPPING, T, T1, T2, etf, etf_obs, macro, market_state, offline, reply, valid_output, whales,
)
from test_macro_evidence import sched
from test_regime import derivatives, rates
from traid.ai import EvidenceInputs, select
from traid.ai.validation import validate_reply
from traid.macro import EtfMetric

TS = T + timedelta(seconds=40)
EMPLOYMENT = (sched("2026-09", date(2026, 10, 2), event="EMPLOYMENT_SITUATION"),
              sched("2026-10", date(2026, 11, 6), event="EMPLOYMENT_SITUATION"))
T2_SEL = select(T2, T, EvidenceInputs(macro=macro(schedules=(*CPI_AT_T, *EMPLOYMENT))))
T2_REQ = json.loads(T2_SEL.request_json)
T1_SEL = select(T1, T, EvidenceInputs(
    market_state=market_state(derivatives=derivatives(fs=rates(["-0.0001"] * 4))), whales=whales([("L", "100")] * 6),
    etf=etf([etf_obs("IBIT", "1000", metric=EtfMetric.TRADING_VOLUME_SHARES), etf_obs("IBIT", "500")]),
    etf_mapping=MAPPING))
T1_REQ = json.loads(T1_SEL.request_json)


def find(request, match):
    for i in request["structured"] + request["contextual"]:
        for v in i["values"]:
            if match in v["field_path"]:
                return i["evidence_id"], v
    raise KeyError(match)


def run(statement, values, request=T2_REQ, sel=T2_SEL):
    """values: [(match, text)]; {e} in the statement is the first value's item."""
    found = [(find(request, m), text) for m, text in values]
    refs = sorted({e for (e, _), _ in found})
    statement = statement.format(e=refs[0] if refs else "E001")
    note = {"statement": statement, "refs": refs or [], "numbers": [{"value_id": v["value_id"], "text": t}
                                                                    for (_, v), t in found]}
    out = valid_output(request)
    out["uncertainties"].append(note)
    res = validate_reply(reply(out), sel.context, TS)
    return "VALID" if res.valid else res.code


CPI = ("series[CUUR0000SA0].known_value", "336.940")


# ------------------------------------------------------------- exact Codex counterexamples
@pytest.mark.parametrize("statement", [
    "The CPI level is 336.940 payroll jobs in {e}.",
    "The CPI level is 336.940 in USD in {e}.",
    "The CPI level is 336.940 measured in USD in {e}.",
    "The CPI level is 336.940 in {e}, with its unit being payroll jobs.",
    "The CPI level is 336.940 in {e}, expressed in shares.",
    "The CPI level is 336.940 measured as the stated value in payroll jobs in {e}.",
])
def test_codex_counterexamples_are_rejected(statement):
    assert run(statement, [CPI]) == "UNIT_MISMATCH"


# ---------------------------------------------------------------- adversarial placements
@pytest.mark.parametrize("statement", [
    "In USD terms the CPI level for {e} is 336.940.",                                # before the number
    "The CPI level is 336.940 for {e} in USD.",                                      # after an identifier
    "The CPI level is 336.940 for {e} and 2026-09, in dollars.",                     # after a period literal
    "The CPI level is 336.940 as the value that is stated in terms of the shares in {e}.",   # long connectors
    "The CPI level is 336.940, in USD, in {e}.",                                     # punctuation
    "The CPI level is 336.940 in {e}; USD.",
    "The CPI level is 336.940 in {e} in basis points.",                              # multiword
    "The CPI level is 336.940 in {e} as a share of the total.",
    "The CPI level is 336.940 in units of index points for {e}.",                    # ambiguous: fails closed
])
def test_wrong_or_ambiguous_units_anywhere_are_rejected(statement):
    assert run(statement, [CPI]) == "UNIT_MISMATCH"


def test_bracketed_unit_is_not_a_token():
    assert run("The CPI level is 336.940 (USD) in {e}.", [CPI]) == "TOKEN_INVALID"


def test_multiple_numbers_with_different_units_cannot_share_a_statement():
    assert run("CPI was 336.940 and the rate 4.2 percent in {e}.",
               [CPI, ("series[LNS14000000].known_value", "4.2")]) == "MULTI_VALUE_STATEMENT"


def test_fomc_endpoint_group():
    low, high = ("fomc.statement.target_lower_percent", "3.75%"), ("fomc.statement.target_upper_percent", "4%")
    assert run("The range is 3.75% to 4% in {e}, as stated.", [low, high]) == "VALID"
    assert run("The range is 3.75% to 4% in percent terms in {e}.", [low, high]) == "VALID"
    assert run("The range is 3.75% to 4% in percentage points in {e}.", [low, high]) == "UNIT_MISMATCH"
    assert run("The range is 3.75% to 4% in {e}, in USD.", [low, high]) == "UNIT_MISMATCH"


# ------------------------------------------------- every unit family: valid and invalid
FAMILIES = [
    # (request, match, text, valid statement, invalid statement)
    ("T2", "series[CUUR0000SA0].known_value", "336.940", "The CPI level is 336.940 index points in {e}.",
     "The CPI level is 336.940 percent in {e}."),
    ("T2", "series[CES0000000001].known_value", "159044", "The payroll employment level was 159044 in {e}.",
     "The payroll level was 159044 jobs in {e}."),
    ("T2", "series[LNS14000000].known_value", "4.2", "The unemployment rate was 4.2 percent in {e}.",
     "The unemployment rate was 4.2 percentage points in {e}."),
    ("T2", "fomc.range_change_since_previous", "0.25", "The range moved by 0.25 percentage points in {e}.",
     "The range moved by 0.25 percent in {e}."),
    ("T1", "C07.book:spread_bps", None, "The displayed spread was {t} bps in {e}.",
     "The displayed spread was {t} percent in {e}."),
    ("T1", "C07.book:bands[0].bid_quote", "499.7", "The bid depth was 499.7 USD in {e}.",
     "The bid depth was 499.7 USDC in {e}."),
    ("T1", "aggregate.gross_notional", "600", "The whale gross notional was 600 USDC in {e}.",
     "The whale gross notional was 600 USD in {e}."),
    ("T1", "C08.flow:window_buy_volume", "3", "The window aggressor volume was 3 BTC in {e}.",
     "The window aggressor volume was 3 USD in {e}."),
    ("T1", "funds[IBIT]", None, "The fund volume was {t} shares in {e}.", "The fund volume was {t} USD in {e}."),
    ("T1", "funding.latest_rate", "-0.0001", "The latest funding rate was -0.0001 as a fraction in {e}.",
     "The latest funding rate was -0.0001 bps in {e}."),
]


@pytest.mark.parametrize("task,match,text,good,bad", FAMILIES)
def test_each_unit_family(task, match, text, good, bad):
    request, sel = (T2_REQ, T2_SEL) if task == "T2" else (T1_REQ, T1_SEL)
    if match == "funds[IBIT]":
        item = next(i for i in request["structured"] + request["contextual"] if i["subject"] == "TRADING_VOLUME_SHARES")
        match = f"metrics[TRADING_VOLUME_SHARES].funds[IBIT]"
        assert item["values"][0]["unit"] == "shares"
    if text is None:
        text = find(request, match)[1]["displays"][-1]
    assert run(good.replace("{t}", text), [(match, text)], request, sel) == "VALID", good
    assert run(bad.replace("{t}", text), [(match, text)], request, sel) == "UNIT_MISMATCH", bad


# ------------------------------------------------------------------- valid statements
@pytest.mark.parametrize("statement,values", [
    ("The CPI level is 336.940 in {e}.", [CPI]),                                     # no unit asserted
    ("The CPI level is 336.940 as stated in {e}.", [CPI]),
    ("CPI (CUUR0000SA0) for 2026-09 was 336.940, captured 2026-10-15T12:02:00Z.", [CPI]),
    ("The CPI level is 336.940 measured in index points in {e}.", [CPI]),
    ("The CPI level is 336.940 as an index in {e}.", [CPI]),
    ("The cited release is described in E001 without a unit claim.", []),
])
def test_valid_statements_still_pass(statement, values):
    assert run(statement, values) == "VALID"


def test_negative_t1_value_with_and_without_unit():
    m = ("funding.latest_rate", "-0.0001")
    assert run("The latest funding rate was -0.0001 per hour in {e}.", [m], T1_REQ, T1_SEL) == "VALID"
    assert run("The BTC funding rate was -0.0001 per hour in {e}.", [m], T1_REQ, T1_SEL) == "VALID"     # asset word, not unit
    assert run("The funding rate was -0.0001 BTC in {e}.", [m], T1_REQ, T1_SEL) == "UNIT_MISMATCH"


# ------------------------------------------------ asset word: descriptor versus unit assertion
FUNDING = ("funding.latest_rate", "-0.0001")
BTC_VOLUME = ("C08.flow:window_buy_volume", "3")


@pytest.mark.parametrize("statement", [
    "The funding rate was -0.0001 in {e}, measured in BTC.",                         # exact Codex bypasses
    "The funding rate was -0.0001 in {e}, denominated in BTC.",
    "The funding rate was -0.0001 in {e}, reported in bitcoin.",
    "The funding rate was -0.0001 BTC in {e}.",                                      # immediate, already rejected
    "The funding rate was -0.0001 in {e} btc.",                                      # after the identifier
    "The funding rate was -0.0001 in {e}, measured in Bitcoin.",                     # capitalization
    "The funding rate was -0.0001 in {e}, quoted in BITCOIN.",
    "In BTC terms the funding rate for {e} was -0.0001.",                            # before the number
    "Measured in bitcoin, the funding rate in {e} was -0.0001.",
    "The funding rate in BTC was -0.0001 in {e}.",
    "The funding rate was -0.0001 in {e} and 1h, stated as a value given in terms of BTC.",   # long connectors
    "The funding rate was -0.0001, in {e}; BTC.",                                    # punctuation
    "The funding rate was -0.0001 in {e}: bitcoin.",
    "The funding rate of BTC was -0.0001 in {e}.",                                   # ambiguous: fails closed
    "The BTC was -0.0001 in {e}.",
    "The funding rate was -0.0001 in {e}, measured in ETH.",                         # other asset labels
    "The funding rate was -0.0001 in {e}, denominated in USDT.",
    "The funding rate was -0.0001 in {e}, reported in ether.",
    "The funding rate was -0.0001 in {e}, measured in sats.",
    "The funding rate was -0.0001 in {e}, measured in USDC.",
])
def test_asset_word_as_unit_assertion_is_rejected(statement):
    assert run(statement, [FUNDING], T1_REQ, T1_SEL) == "UNIT_MISMATCH", statement


@pytest.mark.parametrize("statement,value", [
    ("The BTC funding rate was -0.0001 in {e}.", FUNDING),                          # asset descriptors
    ("The bitcoin funding rate was -0.0001 in {e}.", FUNDING),
    ("Bitcoin funding was -0.0001 in {e}.", FUNDING),
    ("The Bitcoin perpetual funding rate was -0.0001 per hour in {e}.", FUNDING),
    ("The latest funding rate was -0.0001 in {e}.", FUNDING),                        # fractional funding
    ("The latest funding rate was -0.0001 as a fraction in {e}.", FUNDING),
    ("The window aggressor volume was 3 BTC in {e}.", BTC_VOLUME),                   # real BTC quantities
    ("The window aggressor volume was 3 in {e}, measured in BTC.", BTC_VOLUME),
    ("The bitcoin aggressor volume was 3 btc in {e}.", BTC_VOLUME),
])
def test_asset_descriptor_and_supported_btc_units_stay_valid(statement, value):
    assert run(statement, [value], T1_REQ, T1_SEL) == "VALID", statement


@pytest.mark.parametrize("statement", [
    "The funding rate was -0.0001 in {e}, expressed using the BTC denomination.",    # exact Codex reproductions
    "The BTC denomination of the funding rate was -0.0001 in {e}.",
    "The funding rate was -0.0001 in {e}, measured using the bitcoin denomination.",
    "The funding rate was -0.0001 in {e}, in the BTC denomination.",                 # supplied variants
    "The BTC unit for this funding rate was -0.0001 in {e}.",
    "The funding rate was -0.0001 in {e}, quoted using bitcoin as its unit.",
    "The rate of -0.0001 in {e} was expressed as a BTC amount.",
    "Bitcoin-denominated funding was -0.0001 in {e}.",                               # found in self-audit
    "The BTC-quoted funding rate was -0.0001 in {e}.",
    "The BTC currency value of the funding rate was -0.0001 in {e}.",
    "A BTC quantity for the funding rate was -0.0001 in {e}.",
    "The BTC funding denomination was -0.0001 in {e}.",
    "The BTC figure for funding was -0.0001 in {e}.",
    "The bitcoin's denomination for funding was -0.0001 in {e}.",
    "The BTC funding rate was -0.0001 in {e}, in its native currency.",
    "The funding rate was -0.0001 in {e}, given in its native currency.",            # no asset word at all
    "As a BTC price the funding rate was -0.0001 in {e}.",                           # determiner, not opening
    "In {e} the BTC funding rate was -0.0001.",
    "The funding rate was -0.0001 in {e} for the BTC perpetual.",                    # after the number
    "The BTC funding rate was -0.0001 in {e}, as a BTC price.",                      # correct + incorrect
    "The BTC funding rate was -0.0001 in {e}, measured in bitcoin.",
    "The BTC funding rate, a bitcoin figure, was -0.0001 in {e}.",
    "The BTC funding rate was -0.0001 in {e}, which the source states in BTC.",
    "The funding rate was -0.0001 in {e} for the BTC.",                              # sentence-final
])
def test_asset_denomination_assertions_are_rejected(statement):
    assert run(statement, [FUNDING], T1_REQ, T1_SEL) == "UNIT_MISMATCH", statement


def test_denomination_candidate_failing_another_rule_first():
    assert run("This BTC sum for funding was -0.0001 in {e}.", [FUNDING], T1_REQ, T1_SEL) == "ARITHMETIC_WORD"


@pytest.mark.parametrize("statement", [
    "Bitcoin's funding rate was -0.0001 in {e}.",
    "THE BTC FUNDING rate was -0.0001 in {e}.",
])
def test_opening_asset_descriptor_variants_stay_valid(statement):
    assert run(statement, [FUNDING], T1_REQ, T1_SEL) == "VALID", statement


def test_btc_quantity_with_another_asset_unit_is_rejected():
    assert run("The window aggressor volume was 3 in {e}, measured in ETH.", [BTC_VOLUME], T1_REQ, T1_SEL) \
        == "UNIT_MISMATCH"
    assert run("The window aggressor volume was 3 in {e}, denominated in USD.", [BTC_VOLUME], T1_REQ, T1_SEL) \
        == "UNIT_MISMATCH"


# -------------------------------------------------------- earlier bypasses stay blocked
@pytest.mark.parametrize("statement,code", [
    ("The CPI level is －336.940 in {e}.", "UNSUPPORTED_CHARACTER"),
    ('The CPI level is -"336.940" in {e}.', "UNSUPPORTED_CHARACTER"),
    ("The CPI level is 336.940+0 in {e}.", "UNSUPPORTED_CHARACTER"),
    ("The CPI level is .940 in {e} only.", "TOKEN_INVALID"),
    ("The CPI level is 1e3 in {e} only.", "TOKEN_INVALID"),
    ("One less one equals zero for {e} here.", "NUMBER_WORD"),
])
def test_previous_bypasses_remain_rejected(statement, code):
    values = [] if "One less" in statement else [CPI]
    assert run(statement, values) == code
