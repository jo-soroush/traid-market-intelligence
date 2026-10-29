"""Regressions for the first independent C14 implementation audit (Codex FAIL): atomic deadline
finalization, future evidence admission, unit phrases, claim capacity and optional T2 ETF context.
Reports are built by the real upstream engines and then made time-inconsistent by schema-valid edits."""
from datetime import date, timedelta
from decimal import Decimal
import json
import threading

import pytest

from ai_support import (  # noqa: F401
    MAPPING, T, T1, T2, FakeClock, FakeProvider, bls, cpi_claim, etf, etf_obs, macro, market_state, news,
    offline, record_root, reply, valid_output, whales,
)
from test_macro_evidence import sched
from traid.ai import AIService, AIStatus, EvidenceInputs, ProcessSlot, RecordStore, select
from traid.ai.service import Phase, PreOutcome, Terminal, _Invocation, decide
from traid.ai.validation import validate_reply

D = 1065.0
MS = 0.001
TS = T + timedelta(seconds=40)


def tamper(model, path, value):
    data = model.model_dump()
    node = data
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    return type(model).model_validate(data)


def req(s):
    assert s.skip is None, s.skip
    return json.loads(s.request_json)


def items(r):
    return {i["evidence_id"]: i for i in r["structured"] + r["contextual"]}


def by_kind(r, kind):
    return [i for i in items(r).values() if i["kind"] == kind]


# ======================================================================= Fix 1
class ScriptedClock(FakeClock):
    """Each monotonic() read returns the next scripted value (then keeps the last); counts reads."""
    def __init__(self, reads):
        super().__init__()
        self.reads = list(reads)
        self.count = 0

    def monotonic(self):
        self.count += 1
        if len(self.reads) > 1:
            return self.reads.pop(0)
        return self.reads[0]


def inv_with(clock):
    return _Invocation(clock=clock, deadline=D, run_id="0" * 32, file_name="x", invoked_at=T)


def committing(clock):
    inv = inv_with(clock)
    with inv.lock:                      # state reached before D (set directly to isolate one transition)
        inv.phase, inv.pre = Phase.COMMITTING, PreOutcome(AIStatus.VALID, ())
        inv.log.append((Phase.COMMITTING, D - 10))
    return inv


def test_defect_b_one_clock_read_per_transition_before_the_deadline():
    clock = ScriptedClock([D - MS, D + MS])         # a second read would cross the deadline
    inv = committing(clock)
    inv.finish_commit(Terminal.COMMITTED)
    assert clock.count == 1 and inv.sealed is None and inv.log[-1] == (Phase.DONE, D - MS)
    clock.reads = [D + MS]
    assert inv.try_finalize().row == "L1"           # late caller, DONE before D: L1, never U


def test_defect_b_exact_d_read_takes_the_late_path_and_seals_before_applying():
    clock = ScriptedClock([D, D - MS])              # a second read would look on time
    inv = committing(clock)
    inv.finish_commit(Terminal.COMMITTED)
    assert clock.count == 1 and inv.sealed is not None and inv.sealed.phase is Phase.COMMITTING
    assert inv.deadline_decision.row == "Ub" and inv.log[-1] == (Phase.DONE, D)
    clock.reads = [D + MS]
    assert inv.try_finalize().row == "Ub"


@pytest.mark.parametrize("method", ["enter", "commit_step", "room", "alive"])
def test_defect_b_every_locked_transition_reads_the_clock_once(method):
    clock = ScriptedClock([D - MS, D + MS])
    inv = inv_with(clock)
    call = {"enter": lambda: inv.enter(Phase.SELECTING), "commit_step": lambda: inv.commit_step(
        PreOutcome(AIStatus.AI_NOT_REQUESTED, ("X",))), "room": lambda: inv.room(0.0), "alive": inv.alive}[method]
    result = call()
    assert result is not None and (result is not False or method == "room")     # room: no time to spare at D - 1 ms
    assert clock.count == 1 and inv.sealed is None
    if method in ("enter", "commit_step"):
        assert inv.log[-1][1] == D - MS             # the stamp is the read that passed the deadline check


def test_defect_a_decision_and_assignment_are_one_locked_step():
    """The caller decides O1 at D - 1 ms; time then passes D and a worker-side actor tries to take the
    lock to seal. It can only run after the caller's outcome is assigned, and nothing changes it."""
    clock = ScriptedClock([D - MS])
    inv = committing(clock)
    inv.finish_commit(Terminal.COMMITTED)
    inv.pre = PreOutcome(AIStatus.VALID, (), None)
    seen, built = [], []
    contender = threading.Thread(target=lambda: (inv.alive(), seen.append(inv.caller_outcome)))

    def build(decision, interpretation):
        clock.reads = [D + MS]                       # time crosses D inside the caller's step
        contender.start()                            # a contender for the lock ...
        assert not inv.lock.acquire(blocking=False)  # ... cannot get it while the caller decides
        built.append(decision.row)
        return f"outcome:{decision.row}"
    out = inv.try_finalize(build)
    contender.join(10)
    assert out == "outcome:O1" and built == ["O1"]
    assert seen == ["outcome:O1"]                    # the contender saw the assigned outcome
    assert inv.try_finalize(build) == "outcome:O1"   # never reassigned


def test_defect_a_late_caller_after_worker_seal_never_publishes_valid(record_root):
    """End to end: the worker commits at D - 1 ms; the caller's read happens after D."""
    clock = FakeClock()
    entered, release = threading.Event(), threading.Event()
    from ai_support import FaultyOps
    ops = FaultyOps(block={"fsync_dir": (entered, release)})
    svc = AIService(FakeProvider([lambda r: valid_output(json.loads(r.user_text))]), RecordStore(record_root, ops),
                    clock=clock, slot=ProcessSlot())
    clock.caller_gate.clear()
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("r", svc.interpret(T1, T, EvidenceInputs(market_state=market_state()))))
    t.start()
    assert entered.wait(10)
    clock.set(D - MS)
    release.set()
    assert svc.last_invocation.done.wait(10)
    clock.set(D + MS)
    clock.caller_gate.set()
    t.join(10)
    r = out["r"]
    assert r.status is AIStatus.AI_UNAVAILABLE and r.reasons == ("DEADLINE_EXCEEDED_BEFORE_RELEASE",)
    assert r.interpretation is None and svc.last_invocation.caller_outcome is r


# ======================================================================= Fix 2
REP = macro()


def test_fomc_latest_statement_received_after_t_is_not_admitted():
    late = tamper(REP, ["fomc", "statement", "provenance", "received_timestamp"], T + timedelta(days=1))
    assert late.fomc.freshness.value == "CURRENT"             # the label alone would have admitted it
    r = req(select(T2, T, EvidenceInputs(macro=late)))
    (fomc,) = by_kind(r, "C12_FOMC")
    paths = [v["field_path"] for v in fomc["values"]]
    assert paths == ["fomc.previous_statement.target_lower_percent", "fomc.previous_statement.target_upper_percent"]
    assert fomc["state"] == "LATEST_STATEMENT_NOT_AVAILABLE_AT_EVALUATION" and fomc["tier"] == "CONTEXTUAL"
    assert {a["name"]: a["value"] for a in fomc["attributes"]}["scope"] == "HISTORICAL_STATEMENT"
    assert "statement:NOT_AVAILABLE_AT_EVALUATION" in fomc["values_withheld"]
    assert "range_change_since_previous:CONTRIBUTING_STATEMENT_NOT_AVAILABLE_AT_EVALUATION" in fomc["values_withheld"]
    assert all(a["evidence_id"] != fomc["evidence_id"] for a in r["anchors"])
    assert "fomc.statement." not in json.dumps(r) and "range_change_since_previous\"" not in json.dumps(r)


def test_fomc_publication_and_receipt_after_t_withhold_the_derived_change_and_anchor():
    st = REP.fomc.statement
    data = REP.model_dump()
    data["fomc"]["statement"]["published_at"] = T + timedelta(days=1)
    data["fomc"]["statement"]["provenance"]["received_timestamp"] = T + timedelta(days=1, minutes=1)
    late = type(REP).model_validate(data)
    r = req(select(T2, T, EvidenceInputs(macro=late)))
    (fomc,) = by_kind(r, "C12_FOMC")
    assert not any(v["field_path"] == "fomc.range_change_since_previous" for v in fomc["values"])
    assert [a["statement"] for a in r["anchors"] if "FOMC" in a["statement"]] == []
    assert st.statement_date.isoformat() not in json.dumps([a["statement"] for a in r["anchors"]])
    both = tamper(late, ["fomc", "previous_statement", "provenance", "received_timestamp"], T + timedelta(days=2))
    r = req(select(T2, T, EvidenceInputs(macro=both)))
    assert by_kind(r, "C12_FOMC") == [] and any(u["subject"] == "fomc.statement" for u in r["unavailable"])


def test_etf_observation_received_after_t_is_not_admitted():
    tickers = [f.ticker for f in MAPPING.applicable()]
    report = etf([etf_obs(t, "500") for t in tickers])
    metric = next(i for i, m in enumerate(report.metrics) if m.metric.value == "NET_FLOW_USD")
    late = tamper(report, ["metrics", metric, "funds", 0, "observation", "provenance", "received_timestamp"],
                  T + timedelta(days=1))
    assert late.metrics[metric].funds[0].status.value == "OBSERVED"     # the label alone would admit it
    r = req(select(T1, T, EvidenceInputs(market_state=market_state(), etf=late, etf_mapping=MAPPING)))
    (flow,) = [i for i in items(r).values() if i["subject"] == "NET_FLOW_USD"]
    funds = [v["field_path"] for v in flow["values"]]
    assert f"metrics[NET_FLOW_USD].funds[{late.metrics[metric].funds[0].ticker}]" not in funds
    assert "metrics[NET_FLOW_USD].aggregate" not in funds and flow["tier"] == "CONTEXTUAL"
    single = tamper(etf([etf_obs("IBIT", "500")]), ["metrics", metric, "funds",
                    [f.ticker for f in etf([etf_obs("IBIT", "500")]).metrics[metric].funds].index("IBIT"),
                    "observation", "provenance", "received_timestamp"], T + timedelta(days=1))
    r = req(select(T1, T, EvidenceInputs(market_state=market_state(), etf=single, etf_mapping=MAPPING)))
    assert '"500"' not in json.dumps(r) and not [i for i in items(r).values() if i["category"] == "C12_ETF"]


def test_other_receipts_after_t_are_not_admitted():
    ms = market_state()
    late_c10 = tamper(ms, ["direction", "sources", 0, "newest_provenance", "received_timestamp"], T + timedelta(hours=1))
    r = req(select(T1, T, EvidenceInputs(market_state=late_c10)))
    assert all(a["statement"].split(" ")[1] not in ("direction", "composite") for a in r["anchors"])
    assert {"C10.direction", "C10.regime"} <= {u["subject"] for u in r["unavailable"]}
    index = next(i for i, s in enumerate(REP.series) if s.series_id == "CUUR0000SA0")
    late_series = tamper(REP, ["series", index, "provenance", "received_timestamp"], T + timedelta(hours=1))
    r = req(select(T2, T, EvidenceInputs(macro=late_series)))
    assert not [i for i in items(r).values() if i["subject"] == "CUUR0000SA0"]
    wh = whales([("L", "100")] * 6)
    late_whale = tamper(wh, ["wallets", 0, "snapshot", "provenance", "received_timestamp"], T + timedelta(minutes=1))
    s = select(T1, T, EvidenceInputs(market_state=ms, whales=late_whale))
    assert s.bindings.whale_gate == "INCONSISTENT:SNAPSHOT_AFTER_EVALUATION"
    assert s.request_json == select(T1, T, EvidenceInputs(market_state=ms)).request_json     # constant absence


# ======================================================================= Fix 3
EMPLOYMENT = (sched("2026-09", date(2026, 10, 2), event="EMPLOYMENT_SITUATION"),
              sched("2026-10", date(2026, 11, 6), event="EMPLOYMENT_SITUATION"))
REP_ALL = macro(schedules=(*__import__("ai_support").CPI_AT_T, *EMPLOYMENT))
T2_SEL = select(T2, T, EvidenceInputs(macro=REP_ALL))
T2_REQ = json.loads(T2_SEL.request_json)
T1_SEL = select(T1, T, EvidenceInputs(market_state=market_state(), whales=whales([("L", "100")] * 6)))
T1_REQ = json.loads(T1_SEL.request_json)


def value(request, suffix):
    for i in request["structured"] + request["contextual"]:
        for v in i["values"]:
            if v["field_path"].endswith(suffix):
                return i["evidence_id"], v
    raise KeyError(suffix)


def note_code(request, sel, suffix, text, phrase):
    item, v = value(request, suffix)
    out = valid_output(request)
    out["context_notes" if request is T2_REQ else "uncertainties"].append(
        {"statement": f"The cited value is {text} {phrase} in {item}.", "refs": [item],
         "numbers": [{"value_id": v["value_id"], "text": text}]})
    if request is T1_REQ:
        out["uncertainties"][-1]["refs"] = [item]
    res = validate_reply(reply(out), sel.context, TS)
    return "VALID" if res.valid else res.code


def test_exact_cpi_payroll_counterexample_is_rejected():
    item, cpi = value(T2_REQ, "series[CUUR0000SA0].known_value")
    out = valid_output(T2_REQ)
    out["context_notes"] = [{"statement": f"The CPI level is 336.940 payroll jobs in {item}.", "refs": [item],
                             "numbers": [{"value_id": cpi["value_id"], "text": "336.940"}]}]
    res = validate_reply(reply(out), T2_SEL.context, TS)
    assert (res.valid, res.code) == (False, "UNIT_MISMATCH")


@pytest.mark.parametrize("suffix,text,ok,bad", [
    ("series[CUUR0000SA0].known_value", "336.940", ["index points", "index"], ["payroll jobs", "percent", "USD", "points", "jobs"]),
    ("series[CES0000000001].known_value", "159044", [], ["payroll jobs", "jobs", "index", "employees"]),
    ("series[LNS14000000].known_value", "4.2", ["percent"], ["percentage points", "bps", "basis points", "index"]),
    ("fomc.statement.target_lower_percent", "3.75", ["percent"], ["percentage points", "bps", "USD"]),
    ("fomc.range_change_since_previous", "0.25", ["percentage points"], ["percent", "points", "basis points", "bps"]),
])
def test_macro_unit_phrases(suffix, text, ok, bad):
    for phrase in ok:
        assert note_code(T2_REQ, T2_SEL, suffix, text, phrase) == "VALID", phrase
    for phrase in bad:
        assert note_code(T2_REQ, T2_SEL, suffix, text, phrase) == "UNIT_MISMATCH", phrase
    assert note_code(T2_REQ, T2_SEL, suffix, text, "as stated") == "VALID"        # no unit asserted


def _first(request, prefix):
    for i in request["structured"] + request["contextual"]:
        for v in i["values"]:
            if v["field_path"].startswith(prefix):
                return v
    raise KeyError(prefix)


@pytest.mark.parametrize("prefix,ok,bad", [
    ("aggregate.gross_notional", ["USDC"], ["USD", "dollars", "BTC"]),
    ("C10.liquidity.C07.book:spread_bps", ["bps", "basis points"], ["percent", "USD"]),
    ("C10.liquidity.C07.book:bands[0].bid_quote", ["USD"], ["USDC", "BTC"]),
    ("C10.flow.C08.flow:window_buy_volume", ["BTC"], ["USD", "shares", "contracts"]),
    ("C10.funding.C09.funding:funding.latest_rate", ["fraction"], ["percent", "bps"]),
])
def test_t1_unit_phrases(prefix, ok, bad):
    v = _first(T1_REQ, prefix)
    text = v["displays"][-1]
    for phrase in ok:
        assert note_code(T1_REQ, T1_SEL, v["field_path"], text, phrase) == "VALID", phrase
    for phrase in bad:
        assert note_code(T1_REQ, T1_SEL, v["field_path"], text, phrase) == "UNIT_MISMATCH", phrase


# ======================================================================= Fix 4
def nine_claims(n):
    return news([cpi_claim(source_id=f"cpi-{i}") for i in range(n)], REP)


def test_nine_claims_are_refused_not_truncated(record_root):
    inputs = EvidenceInputs(market_state=market_state(), macro=REP, news=nine_claims(9))
    s = select(T1, T, inputs)
    assert s.skip == ("INPUT_LIMIT_EXCEEDED",) and s.request is None
    assert [e.reason for e in s.excluded if e.locator == "results"] == ["ASSESSED_CLAIM_CAPACITY_EXCEEDED:9>8"]
    provider = FakeProvider([lambda r: valid_output(json.loads(r.user_text))])
    result = AIService(provider, RecordStore(record_root), clock=FakeClock(), slot=ProcessSlot()).interpret(T1, T, inputs)
    assert (result.status, result.reasons) == (AIStatus.AI_NOT_REQUESTED, ("INPUT_LIMIT_EXCEEDED",))
    assert provider.calls == []


def test_eight_claims_fit_and_all_are_covered(record_root):
    inputs = EvidenceInputs(market_state=market_state(), macro=REP, news=nine_claims(8))
    r = req(select(T1, T, inputs))
    assert len(r["assessed_claims"]) == 8 and len(r["required"]["claim_ids"]) == 8
    provider = FakeProvider([lambda x: valid_output(json.loads(x.user_text))])
    result = AIService(provider, RecordStore(record_root), clock=FakeClock(), slot=ProcessSlot()).interpret(T1, T, inputs)
    assert result.status is AIStatus.VALID and len(result.interpretation.output.claim_notes) == 8


# ======================================================================= T2 ETF context
def complete_etf():
    return etf([etf_obs(t, str(1000 + i)) for i, t in enumerate(f.ticker for f in MAPPING.applicable())])


def test_t2_keeps_eligible_etf_as_optional_context_only(record_root):
    s = select(T2, T, EvidenceInputs(macro=REP, etf=complete_etf(), etf_mapping=MAPPING))
    r = req(s)
    etf_items = [i for i in items(r).values() if i["category"] == "C12_ETF"]
    assert etf_items and all(i["tier"] == "CONTEXTUAL" for i in etf_items)
    assert all(a["evidence_id"] not in {i["evidence_id"] for i in etf_items} for a in r["anchors"])
    assert {c["category"]: c["state"] for c in r["categories"]}["C12_ETF"] == "PARTIAL"    # other metrics: no data
    flow = next(i for i in etf_items if i["subject"] == "NET_FLOW_USD")
    agg = flow["values"][0]
    out = valid_output(r)
    out["context_notes"] = [{"statement": f"Mapped fund net flow totals {agg['value']} USD in {flow['evidence_id']}.",
                             "refs": [flow["evidence_id"]], "numbers": [{"value_id": agg["value_id"], "text": agg["value"]}]}]
    assert validate_reply(reply(out), s.context, TS).valid
    for bad in ({"summary": dict(out["summary"], refs=out["summary"]["refs"] + [flow["evidence_id"]])},
                {"anchor_assessments": [dict(out["anchor_assessments"][0],
                                             evidence_ids=out["anchor_assessments"][0]["evidence_ids"] + [flow["evidence_id"]])]
                 + out["anchor_assessments"][1:]}):
        v = validate_reply(reply({**out, **bad}), s.context, TS)
        assert (v.valid, v.code) == (False, "OUT_OF_SCOPE_REFERENCE")
    out["context_notes"][0]["statement"] = f"The BTC fund flow is listed in {flow['evidence_id']} here."
    out["context_notes"][0]["numbers"] = []
    assert validate_reply(reply(out), s.context, TS).code == "ASSET_CONCLUSION_IN_MACRO_TASK"


def test_t2_continues_without_admissible_etf(record_root):
    for inputs in (EvidenceInputs(macro=REP, etf=etf(approved=False), etf_mapping=MAPPING),
                   EvidenceInputs(macro=REP, etf=complete_etf()),                       # mapping not supplied
                   EvidenceInputs(macro=REP)):
        s = select(T2, T, inputs)
        r = req(s)
        assert not [i for i in items(r).values() if i["category"] == "C12_ETF"]
        assert validate_reply(reply(valid_output(r)), s.context, TS).valid
