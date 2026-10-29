"""Regressions for the second independent C14 re-audit (Codex FAIL): future-dependent FOMC metadata, and
unit assertions linked to a number by connector words. FOMC cases are schema-valid edits of real C12
builder reports; unit cases run the complete C14 validator."""
from datetime import date, timedelta
from decimal import Decimal
import json

import pytest

from ai_support import (  # noqa: F401
    CPI_AT_T, T, T1, T2, macro, market_state, offline, reply, valid_output, whales,
)
from test_macro_evidence import REAL, sched
from traid.ai import EvidenceInputs, select
from traid.ai.validation import validate_reply

TS = T + timedelta(seconds=40)
REP = macro()


def tamper(model, edits):
    data = model.model_dump()
    for path, value in edits:
        node = data
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
    return type(model).model_validate(data)


def request(rep):
    s = select(T2, T, EvidenceInputs(macro=rep))
    assert s.skip is None, s.skip
    return s, json.loads(s.request_json)


def fomc_item(r):
    (item,) = [i for i in r["structured"] + r["contextual"] if i["kind"] == "C12_FOMC"]
    return item


def attrs(item):
    return {a["name"]: a["value"] for a in item["attributes"]}


# ================================================================ Fix 1: FOMC metadata
def test_future_received_calendar_sends_no_schedule_and_no_current_state():
    late = tamper(REP, [(["fomc", "calendar_provenance", "received_timestamp"], T + timedelta(days=1))])
    assert late.fomc.freshness.value == "CURRENT" and late.fomc.next_meeting is not None      # labels alone would admit
    s, r = request(late)
    item = fomc_item(r)
    names = {t["name"] for t in item["times"]}
    assert "next_meeting.start_date" not in names and "next_meeting.end_date" not in names
    assert item["state"] == "CALENDAR_NOT_AVAILABLE_AT_EVALUATION" and attrs(item)["scope"] == "HISTORICAL_STATEMENT"
    assert "in_calendar" not in attrs(item) and "consistency" not in attrs(item) and item["tier"] == "CONTEXTUAL"
    assert "SCHEDULE:CALENDAR_NOT_AVAILABLE_AT_EVALUATION" in item["values_withheld"]
    assert not any(v["field_path"] == "fomc.range_change_since_previous" for v in item["values"])
    text = json.dumps(r)
    assert late.fomc.next_meeting.end_date.isoformat() not in text and "SCHEDULED_MEETING" not in text
    assert all("FOMC" not in a["statement"] for a in r["anchors"])                           # no FOMC anchor
    # the statements' own facts remain, labelled historical
    assert [v["field_path"] for v in item["values"]][:2] == ["fomc.statement.target_lower_percent",
                                                             "fomc.statement.target_upper_percent"]


def test_future_meeting_with_a_calendar_received_before_t_is_kept():
    s, r = request(REP)
    item = fomc_item(r)
    times = {t["name"]: t for t in item["times"]}
    assert REP.fomc.calendar_provenance.received_timestamp < T and REP.fomc.next_meeting.end_date > T.date()
    assert times["next_meeting.end_date"]["kind"] == "SCHEDULED"
    assert times["next_meeting.end_date"]["value"] == REP.fomc.next_meeting.end_date.isoformat()
    assert item["state"] == "CURRENT" and attrs(item)["in_calendar"] == "SCHEDULED_MEETING"
    assert attrs(item)["consistency"] == "CONSISTENT"
    assert any("FOMC" in a["statement"] for a in r["anchors"])


@pytest.mark.parametrize("consistency_source", ["consistent", "contradictory"])
def test_unavailable_latest_statement_leaks_no_comparison_state(consistency_source):
    base = REP
    if consistency_source == "contradictory":
        bad = REAL[3].model_copy(update={"target_upper_percent": Decimal("4.25"), "target_lower_percent": Decimal("4")})
        base = macro(statements=[*REAL[:3], bad])
    assert base.fomc.consistency == consistency_source.upper()
    late = tamper(base, [(["fomc", "statement", "provenance", "received_timestamp"], T + timedelta(days=1))])
    s, r = request(late)
    item = fomc_item(r)
    text = json.dumps(r)
    assert "consistency" not in attrs(item) and "CONSISTENT" not in text and "CONTRADICTORY" not in text
    assert "consistency:CONTRIBUTING_EVIDENCE_NOT_AVAILABLE_AT_EVALUATION" in item["values_withheld"]
    assert item["reasons"] == ["LATEST_STATEMENT_NOT_AVAILABLE_AT_EVALUATION"]          # no upstream derived reasons
    # the admissible previous statement stays, historical
    assert [v["field_path"] for v in item["values"]] == ["fomc.previous_statement.target_lower_percent",
                                                         "fomc.previous_statement.target_upper_percent"]
    assert attrs(item)["scope"] == "HISTORICAL_STATEMENT" and item["state"] == "LATEST_STATEMENT_NOT_AVAILABLE_AT_EVALUATION"
    assert attrs(item)["previous_statement.action"] == REAL[2].action.value
    assert all("FOMC" not in a["statement"] for a in r["anchors"])


def test_unavailable_previous_statement_withholds_comparison_but_keeps_latest_facts():
    late = tamper(REP, [(["fomc", "previous_statement", "provenance", "received_timestamp"], T + timedelta(days=1))])
    s, r = request(late)
    item = fomc_item(r)
    assert "consistency" not in attrs(item) and not any(v["field_path"].startswith("fomc.previous_statement")
                                                       for v in item["values"])
    assert not any("stated_change" in v["field_path"] or "range_change" in v["field_path"] for v in item["values"])
    assert attrs(item)["scope"] == "CURRENT_STATEMENT" and item["state"] == "CURRENT"     # latest facts are admissible
    assert any("FOMC" in a["statement"] for a in r["anchors"])


def test_expected_announcement_time_without_verifiable_receipt_is_withheld():
    """The report carries no receipt for the curated schedule behind expected_announcement_at (SYN edit:
    set to a scheduled instant), so its availability at T cannot be shown and it is never sent."""
    from datetime import datetime, timezone
    when = datetime(2026, 10, 28, 18, tzinfo=timezone.utc)
    rep = tamper(REP, [(["fomc", "expected_announcement_at"], when)])
    s, r = request(rep)
    item = fomc_item(r)
    assert "expected_announcement_at" not in {t["name"] for t in item["times"]}
    assert "expected_announcement_at:SCHEDULE_RECEIPT_NOT_IN_REPORT" in item["values_withheld"]
    assert "2026-10-28T18:00:00Z" not in json.dumps(r)


# ============================================================ Fix 2: connected units
EMPLOYMENT = (sched("2026-09", date(2026, 10, 2), event="EMPLOYMENT_SITUATION"),
              sched("2026-10", date(2026, 11, 6), event="EMPLOYMENT_SITUATION"))
REP_ALL = macro(schedules=(*CPI_AT_T, *EMPLOYMENT))
T2_SEL = select(T2, T, EvidenceInputs(macro=REP_ALL))
T2_REQ = json.loads(T2_SEL.request_json)
T1_SEL = select(T1, T, EvidenceInputs(market_state=market_state(), whales=whales([("L", "100")] * 6)))
T1_REQ = json.loads(T1_SEL.request_json)


def bound(request, suffix):
    for i in request["structured"] + request["contextual"]:
        for v in i["values"]:
            if v["field_path"].endswith(suffix):
                return i["evidence_id"], v
    raise KeyError(suffix)


def verdict(statement, refs_numbers, request=T2_REQ, sel=T2_SEL):
    out = valid_output(request)
    refs = sorted({item for item, _, _ in refs_numbers})
    note = {"statement": statement, "refs": refs,
            "numbers": [{"value_id": v["value_id"], "text": text} for _, v, text in refs_numbers]}
    out["context_notes" if request is T2_REQ else "uncertainties"].append(note)
    res = validate_reply(reply(out), sel.context, TS)
    return "VALID" if res.valid else res.code


CPI = bound(T2_REQ, "series[CUUR0000SA0].known_value")


@pytest.mark.parametrize("statement", ["The CPI level is 336.940 in USD in {e}.",               # Codex
                                       "The CPI level is 336.940 measured in USD in {e}.",      # Codex
                                       "The CPI level is 336.940 expressed in dollars in {e}.",
                                       "The CPI level is 336.940 in {e} in USD terms.",
                                       "The CPI level is 336.940 as a percent in {e}.",
                                       "The CPI level is 336.940 measured in payroll jobs in {e}.",
                                       "The CPI level is 336.940 in terms of the bps in {e}."])
def test_cpi_with_a_connected_wrong_unit_is_rejected(statement):
    e, v = CPI
    assert verdict(statement.format(e=e), [(e, v, "336.940")]) == "UNIT_MISMATCH"


@pytest.mark.parametrize("statement", ["The CPI level is 336.940 index points in {e}.",
                                       "The CPI level is 336.940 measured in index points in {e}.",
                                       "The CPI level is 336.940 as an index in {e}.",
                                       "The CPI level is 336.940 in {e}.",
                                       "The CPI level in {e} is 336.940 for the reference period.",
                                       "The CPI level is 336.940 as stated in {e}."])
def test_cpi_with_its_index_unit_or_no_unit_is_valid(statement):
    e, v = CPI
    assert verdict(statement.format(e=e), [(e, v, "336.940")]) == "VALID"


@pytest.mark.parametrize("suffix,text,good,bad", [
    ("series[LNS14000000].known_value", "4.2", ["measured in percent", "percent"],
     ["measured in percentage points", "in bps", "in USD"]),
    ("fomc.range_change_since_previous", "0.25", ["measured in percentage points", "percentage points"],
     ["measured in percent", "in basis points", "expressed in bps"]),
    ("fomc.statement.target_lower_percent", "3.75", ["in percent", "percent"], ["in percentage points", "in USD"]),
    ("series[CES0000000001].known_value", "159044", ["as stated"], ["in payroll jobs", "measured in jobs", "in USD"]),
])
def test_macro_units_through_connectors(suffix, text, good, bad):
    e, v = bound(T2_REQ, suffix)
    for phrase in good:
        assert verdict(f"The cited value is {text} {phrase} in {e}.", [(e, v, text)]) == "VALID", phrase
    for phrase in bad:
        assert verdict(f"The cited value is {text} {phrase} in {e}.", [(e, v, text)]) == "UNIT_MISMATCH", phrase


def _t1(prefix):
    for i in T1_REQ["structured"] + T1_REQ["contextual"]:
        for v in i["values"]:
            if v["field_path"].startswith(prefix):
                return i["evidence_id"], v
    raise KeyError(prefix)


@pytest.mark.parametrize("prefix,good,bad", [
    ("aggregate.gross_notional", ["USDC", "measured in USDC"], ["in USD", "measured in dollars", "USD"]),
    ("C10.liquidity.C07.book:spread_bps", ["bps", "expressed in basis points"], ["in percent", "in USD"]),
    ("C10.liquidity.C07.book:bands[0].bid_quote", ["USD", "in USD"], ["in USDC", "measured in percent"]),
    ("C10.flow.C08.flow:window_buy_volume", ["BTC", "in BTC"], ["in USD", "measured in shares"]),
    ("C10.funding.C09.funding:funding.latest_rate", ["fraction", "as a fraction"], ["in percent", "measured in bps"]),
])
def test_t1_units_through_connectors(prefix, good, bad):
    e, v = _t1(prefix)
    text = v["displays"][-1]
    for phrase in good:
        assert verdict(f"The cited value is {text} {phrase} for {e}.", [(e, v, text)], T1_REQ, T1_SEL) == "VALID", phrase
    for phrase in bad:
        assert verdict(f"The cited value is {text} {phrase} for {e}.", [(e, v, text)], T1_REQ, T1_SEL) == \
            "UNIT_MISMATCH", phrase


def test_ordinary_prose_negatives_and_fomc_groups_still_pass():
    e, low = bound(T2_REQ, "fomc.statement.target_lower_percent")
    _, high = bound(T2_REQ, "fomc.statement.target_upper_percent")
    assert verdict(f"The range is 3.75% to 4% in {e}, as stated in the statement.",
                   [(e, low, "3.75%"), (e, high, "4%")]) == "VALID"
    assert verdict(f"The range is 3.75% to 4% in {e}, in USD.", [(e, low, "3.75%"), (e, high, "4%")]) == "UNIT_MISMATCH"
    from ai_support import market_state as ms
    from test_regime import derivatives, rates
    sel = select(T1, T, EvidenceInputs(market_state=ms(derivatives=derivatives(fs=rates(["-0.0001"] * 4)))))
    req = json.loads(sel.request_json)
    item = next(i for i in req["structured"] if i["subject"] == "funding")
    v = next(x for x in item["values"] if x["field_path"].endswith("funding.latest_rate"))
    out = valid_output(req)
    out["uncertainties"].append({"statement": f"The latest rate in {item['evidence_id']} was -0.0001 per hour.",
                                 "refs": [item["evidence_id"]], "numbers": [{"value_id": v["value_id"], "text": "-0.0001"}]})
    assert validate_reply(reply(out), sel.context, TS).valid
    # prose without a number may mention currencies freely: no numeric unit is asserted
    out = valid_output(T2_REQ)
    out["context_notes"].append({"statement": "Macro releases are reported by agencies, not in USD terms here.",
                                 "refs": [CPI[0]], "numbers": []})
    assert validate_reply(reply(out), T2_SEL.context, TS).valid
