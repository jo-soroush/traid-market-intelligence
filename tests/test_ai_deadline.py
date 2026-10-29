"""F1: deadline seal, decision table and races, with an injected clock that can return exactly D,
real worker threads and explicit barriers. No timing assumption: exact-D stamps are tested directly."""
from datetime import timedelta
import itertools
import json
import os
import threading

import pytest

from ai_support import (  # noqa: F401
    T, T1, FakeClock, FakeProvider, FaultyOps, failure, market_state, offline, oserror, record_root, valid_output,
)
import traid.ai.service as service_module
from traid.ai import AIService, AIStatus, EvidenceInputs, Persistence, PersistenceDetail, ProcessSlot, RecordStore, \
    load_record
from traid.ai.service import (
    InvariantDefect, Phase, PreOutcome, Snapshot, Terminal, _Invocation, decide,
)

D = 1065.0
MS = 0.001
INPUTS = EvidenceInputs(market_state=market_state())
SKIP_INPUTS = EvidenceInputs()                       # no C10: AI_NOT_REQUESTED without a call
ROWS = {"O1", "O2", "O3", "OFa", "OFb", "OFc", "OCa", "OCb", "OCc", "L1", "L2", "L3", "LFa", "LFb", "LFc",
        "LCa", "LCb", "LCc", "Ua", "Ub", "Uc", "N1", "N2", "N3"}
PRE = {"sk": PreOutcome(AIStatus.AI_NOT_REQUESTED, ("INSUFFICIENT_EVIDENCE", "NO_ANCHOR")),
       "va": PreOutcome(AIStatus.VALID, ()), "in": PreOutcome(AIStatus.AI_INVALID, ("SCHEMA_INVALID",)),
       "un": PreOutcome(AIStatus.AI_UNAVAILABLE, ("PROVIDER_ERROR",))}


def gate():
    return threading.Event(), threading.Event()


def valid_script():
    return [lambda r: valid_output(json.loads(r.user_text))]


class Harness:
    def __init__(self, root, provider=None, ops=None, clock=None):
        self.clock = clock or FakeClock()
        self.slot = ProcessSlot()
        self.ops = ops or FaultyOps()
        self.provider = provider if provider is not None else FakeProvider(valid_script())
        self.store = RecordStore(root, self.ops)
        self.svc = AIService(self.provider, self.store, clock=self.clock, slot=self.slot)
        self.result = None
        self.caller_thread = None

    def start(self, inputs=INPUTS, *, hold_caller=False):
        if hold_caller:
            self.clock.caller_gate.clear()

        def run():
            self.caller_thread = threading.get_ident()
            self.result = self.svc.interpret(T1, T, inputs)
        self.thread = threading.Thread(target=run)
        self.thread.start()
        return self

    def release_caller(self):
        self.clock.caller_gate.set()
        self.thread.join(10)
        assert not self.thread.is_alive()
        return self.result

    def worker_done(self):
        inv = self.svc.last_invocation
        assert inv.done.wait(10)
        for _ in range(1000):
            if not self.slot.busy():
                break
            threading.Event().wait(0.002)
        return inv

    def records(self, root):
        return sorted(p for p in os.listdir(root))


def wait_for(predicate):
    for _ in range(5000):
        if predicate():
            return
        threading.Event().wait(0.001)
    raise AssertionError("condition not reached")


# --------------------------------------------------------------------- the table
def test_decide_is_complete_and_mutually_exclusive():
    seen = {}
    for phase in (None, *Phase):
        for pre_key in (None, *PRE):
            for terminal in (None, *Terminal):
                for on_time in (True, False):
                    s = Snapshot(phase, PRE.get(pre_key), terminal)
                    try:
                        d = decide(s, on_time=on_time)
                    except InvariantDefect:
                        continue
                    assert d.row in ROWS
                    seen.setdefault(d.row, set()).add((phase, pre_key, terminal, on_time))
                    if d.release:
                        assert d.row == "O1" and on_time and terminal is Terminal.COMMITTED and pre_key == "va"
    assert set(seen) == ROWS
    # every reachable key maps to one row by construction; spot-check the policy of each family
    assert decide(Snapshot(Phase.DONE, PRE["sk"], Terminal.FAILED_NOT_PUBLISHED), on_time=True).status is AIStatus.AI_NOT_REQUESTED
    d = decide(Snapshot(Phase.DONE, PRE["va"], Terminal.FAILED_NOT_PUBLISHED), on_time=True)
    assert (d.status, d.reasons, d.pre_persistence_status) == (AIStatus.AI_UNAVAILABLE, ("RECORD_WRITE_FAILED",), AIStatus.VALID)
    d = decide(Snapshot(Phase.COMMITTING, PRE["va"], None), on_time=False)
    assert (d.row, d.persistence, d.detail) == ("Ub", Persistence.UNCONFIRMED, PersistenceDetail.UNRESOLVED_AT_DEADLINE)
    d = decide(Snapshot(Phase.SENDING, None, None), on_time=False)
    assert d.limitations == ("REMOTE_OUTCOME_UNKNOWN", "LOCAL_WORKER_MAY_STILL_RUN")
    with pytest.raises(InvariantDefect):
        decide(Snapshot(Phase.SENDING, None, None), on_time=True)                    # I1
    with pytest.raises(InvariantDefect):
        decide(Snapshot(Phase.SELECTING, PRE["sk"], None), on_time=False)            # I2


def test_race10_exhaustive_stamps_including_exact_d_and_either_actor_first():
    """Every interleaving of worker transitions and the caller on the grid {D-10 s, D-3..D+2 ms} (exact D included),
    with both orders at equal stamps, using the real locked methods. Each reaches exactly one row."""
    grid = [D - 10.0] + [D + k * MS for k in (-3, -2, -1, 0, 1, 2)]     # D - 10 s: before the commit reserve
    paths = {"sk": ["SEL", "COMMIT"], "un": ["SEL", "SETUP", "SEND", "COMMIT"],
             "va": ["SEL", "SETUP", "SEND", "VALID", "COMMIT"], "in": ["SEL", "SETUP", "SEND", "VALID", "COMMIT"]}
    reached, cases = set(), 0
    for pre_key, steps in paths.items():
        steps = steps + ["FINISH"]
        for stamps in itertools.combinations_with_replacement(grid, len(steps)):
            for terminal in Terminal:
                for t_fin in grid:
                    for caller_first in (True, False):
                        clock = FakeClock()
                        inv = _Invocation(clock=clock, deadline=D, run_id="0" * 32, file_name="x", invoked_at=T)
                        pending = list(enumerate(stamps))
                        caller_at, caller_before = t_fin, caller_first
                        decision, worker_alive = None, True
                        while decision is None or pending:
                            nxt = pending[0][1] if pending else None
                            caller_turn = decision is None and (
                                nxt is None or caller_at < nxt or (caller_at == nxt and caller_before))
                            if caller_turn:
                                clock.set(caller_at)
                                decision = inv.try_finalize()
                                if decision is None:      # woken early: waits for DONE or for D
                                    finish = stamps[-1]
                                    caller_at = finish if finish < D and pending and \
                                        pending[-1][0] == len(steps) - 1 and worker_alive else D
                                    caller_at = max(caller_at, clock.monotonic())
                                    caller_before = False
                                continue
                            i, t = pending.pop(0)
                            clock.set(t)
                            if not worker_alive:
                                continue
                            step = steps[i]
                            if step == "SEL":
                                worker_alive = inv.enter(Phase.SELECTING)
                            elif step == "SETUP":
                                worker_alive = inv.enter(Phase.SETUP)
                            elif step == "SEND":
                                worker_alive = inv.enter(Phase.SENDING)
                            elif step == "VALID":
                                worker_alive = inv.enter(Phase.VALIDATING)
                            elif step == "COMMIT":
                                worker_alive = inv.commit_step(PRE[pre_key]) is not None
                            elif step == "FINISH":
                                inv.finish_commit(terminal)
                        cases += 1
                        assert decision is not None and decision.row in ROWS
                        reached.add(decision.row)
                        if decision.release:
                            assert t_fin < D and inv.terminal is Terminal.COMMITTED and inv.pre.status is AIStatus.VALID
                            assert next(t for p, t in inv.log if p is Phase.DONE) < D
                        if inv.sealed is not None:
                            assert decision == inv.deadline_decision or t_fin < D
    assert reached == ROWS and cases > 10000


# -------------------------------------------------------------------- thread races
def _block(ops, step):
    entered, release = gate()
    ops.block[step] = (entered, release)
    return entered, release


@pytest.mark.parametrize("worker_first", [True, False])
def test_race1_race2_race5_commit_stamped_after_d_is_never_released(record_root, worker_first):
    h = Harness(record_root)
    entered, release = _block(h.ops, "fsync_dir")
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D + MS)
    if worker_first:
        release.set()
        h.worker_done()
        result = h.release_caller()
    else:
        result = h.release_caller()
        release.set()
        h.worker_done()
    assert (result.status, result.reasons) == (AIStatus.AI_UNAVAILABLE, ("RECORD_WRITE_FAILED",))
    assert result.interpretation is None and result.persistence is Persistence.UNCONFIRMED
    assert result.persistence_detail is PersistenceDetail.UNRESOLVED_AT_DEADLINE and result.pre_persistence_status is AIStatus.VALID
    rec = load_record(result.record_path)                       # the file exists and shows VALID, not released
    assert rec.status is AIStatus.VALID and rec.release_rule.startswith("RELEASED_ONLY_IF")
    assert h.svc.last_invocation.caller_outcome is result


def test_race3_commit_before_d_caller_after_d_withholds(record_root):
    h = Harness(record_root)
    entered, release = _block(h.ops, "fsync_dir")
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D - MS)
    release.set()
    h.worker_done()
    h.clock.set(D + MS)
    result = h.release_caller()
    assert (result.status, result.reasons, result.persistence) == (
        AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_BEFORE_RELEASE",), Persistence.COMMITTED)
    assert result.interpretation is None and result.pre_persistence_status is AIStatus.VALID


def test_race4_commit_and_caller_before_d_release(record_root):
    h = Harness(record_root)
    entered, release = _block(h.ops, "fsync_dir")
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D - MS)
    release.set()
    h.worker_done()
    h.clock.set(D - MS / 2)
    result = h.release_caller()
    assert result.status is AIStatus.VALID and result.interpretation is not None
    assert result.persistence is Persistence.COMMITTED and load_record(result.record_path).status is AIStatus.VALID


@pytest.mark.parametrize("kind,expected", [("skip", "LFa"), ("valid", "LFb"), ("unavailable", "LFc")])
def test_race6_stage_write_fails_before_d_caller_after_d(record_root, kind, expected):
    provider = {"skip": FakeProvider(), "valid": FakeProvider(valid_script()),
                "unavailable": FakeProvider([failure("PROVIDER_ERROR")])}[kind]
    h = Harness(record_root, provider)
    entered, release = _block(h.ops, "write")
    h.ops.fail["write"] = oserror()
    h.start(SKIP_INPUTS if kind == "skip" else INPUTS, hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D - MS)
    release.set()
    h.worker_done()
    h.clock.set(D + MS)
    r = h.release_caller()
    assert r.persistence is Persistence.FAILED and r.persistence_detail is PersistenceDetail.TERMINAL
    if kind == "skip":
        assert (r.status, r.reasons, r.persistence_reason) == (
            AIStatus.AI_NOT_REQUESTED, ("INSUFFICIENT_EVIDENCE", "NO_ANCHOR"), "RECORD_WRITE_FAILED")
    elif kind == "valid":
        assert (r.status, r.reasons, r.pre_persistence_status) == (AIStatus.AI_UNAVAILABLE, ("RECORD_WRITE_FAILED",), AIStatus.VALID)
    else:
        assert (r.status, r.reasons, r.persistence_reason) == (AIStatus.AI_UNAVAILABLE, ("PROVIDER_ERROR",), "RECORD_WRITE_FAILED")
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == expected


def test_race7_stage_write_fails_after_d_is_unresolved(record_root):
    h = Harness(record_root)
    entered, release = _block(h.ops, "write")
    h.ops.fail["write"] = oserror()
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D + MS)
    release.set()
    h.worker_done()
    r = h.release_caller()
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == "Ub"
    assert (r.status, r.persistence, r.persistence_detail) == (
        AIStatus.AI_UNAVAILABLE, Persistence.UNCONFIRMED, PersistenceDetail.UNRESOLVED_AT_DEADLINE)


def test_race8_directory_flush_fails_before_d_file_stays(record_root):
    h = Harness(record_root)
    entered, release = _block(h.ops, "fsync_dir")
    h.ops.fail["fsync_dir"] = oserror()
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D - MS)
    release.set()
    h.worker_done()
    h.clock.set(D + MS)
    r = h.release_caller()
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == "LCb"
    assert r.persistence is Persistence.UNCONFIRMED and r.persistence_detail is PersistenceDetail.TERMINAL
    assert os.path.exists(r.record_path)                         # never removed after an unconfirmed flush


def test_race9_commit_at_exactly_d_is_late(record_root):
    h = Harness(record_root)
    entered, release = _block(h.ops, "fsync_dir")
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D)
    release.set()
    h.worker_done()
    r = h.release_caller()
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == "Ub" and r.interpretation is None
    # commit at D - 1 us, caller exactly at D: L1
    h = Harness(record_root)
    entered, release = _block(h.ops, "fsync_dir")
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D - 1e-6)
    release.set()
    h.worker_done()
    h.clock.set(D)
    r = h.release_caller()
    assert r.reasons == ("DEADLINE_EXCEEDED_BEFORE_RELEASE",) and r.interpretation is None


@pytest.mark.parametrize("kind,expected", [("skip", "Ua"), ("valid", "Ub"), ("unavailable", "Uc")])
def test_race12_caller_exactly_at_d_with_unresolved_commit(record_root, kind, expected):
    provider = {"skip": FakeProvider(), "valid": FakeProvider(valid_script()),
                "unavailable": FakeProvider([failure("PROVIDER_ERROR")])}[kind]
    h = Harness(record_root, provider)
    entered, release = _block(h.ops, "fsync_dir")
    h.start(SKIP_INPUTS if kind == "skip" else INPUTS)
    assert entered.wait(10)
    h.clock.set(D)                                            # the caller wakes at exactly D and seals
    h.thread.join(10)
    r = h.result
    release.set()
    h.worker_done()
    assert h.svc.last_invocation.sealed_by == "caller"
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == expected
    assert r.persistence is Persistence.UNCONFIRMED and r.persistence_detail is PersistenceDetail.UNRESOLVED_AT_DEADLINE
    assert r.interpretation is None and h.svc.last_invocation.caller_outcome is r


@pytest.mark.parametrize("worker_seals", [True, False])
def test_race13_skip_step_after_d_never_enters_committing(record_root, monkeypatch, worker_seals):
    entered, release = gate()
    real_select = service_module.select

    def blocking_select(*args):
        entered.set()
        release.wait(10)
        return real_select(*args)
    monkeypatch.setattr(service_module, "select", blocking_select)
    h = Harness(record_root, FakeProvider())
    h.start(SKIP_INPUTS, hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D - 0.1)
    if worker_seals:
        h.clock.set(D + MS)
        release.set()
        wait_for(lambda: not h.slot.busy())
        h.clock.set(D + 3 * MS)
        r = h.release_caller()
    else:
        h.clock.set(D + 3 * MS)
        r = h.release_caller()
        release.set()
        wait_for(lambda: not h.slot.busy())
    inv = h.svc.last_invocation
    assert inv.sealed_by == ("worker" if worker_seals else "caller")
    assert decide(inv.sealed, on_time=False).row == "N1" and inv.pre is None
    assert (r.status, r.reasons, r.persistence, r.persistence_detail) == (
        AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_BEFORE_REQUEST",), Persistence.NOT_ATTEMPTED,
        PersistenceDetail.DEFERRED_AFTER_FINALIZATION)
    assert inv.record_attempts == 1 and Phase.COMMITTING not in [p for p, _ in inv.log]
    wait_for(lambda: os.path.exists(r.record_path))
    rec = load_record(r.record_path)
    assert (rec.status, rec.reasons) == (r.status, r.reasons) and "LATE_WORKER_RESULT_DISCARDED" in rec.limitations
    assert len(h.records(record_root)) == 1


def test_race14_seal_during_backoff_prevents_a_second_send(record_root):
    provider = FakeProvider([failure("PROVIDER_THROTTLED", retry_safe=True), valid_script()[0]])
    h = Harness(record_root, provider)
    entered, release = gate()
    h.clock.sleep_gate = (entered, release)
    h.start()
    assert entered.wait(10)
    h.clock.set(D + MS)
    h.thread.join(10)
    r = h.result
    release.set()
    wait_for(lambda: not h.slot.busy())
    assert r.reasons == ("CALL_UNRESOLVED_AT_DEADLINE",) and len(provider.calls) == 1
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == "N2"


def test_race15_io_done_before_d_but_lock_taken_after_d_is_late(record_root):
    h = Harness(record_root)
    entered, release = _block(h.ops, "unlink")               # after the directory flush, before the stamp
    h.start(hold_caller=True)
    assert entered.wait(10)
    h.clock.set(D + MS)
    release.set()
    h.worker_done()
    r = h.release_caller()
    assert decide(h.svc.last_invocation.sealed, on_time=False).row == "Ub" and r.interpretation is None


def test_race11_race16_late_result_never_changes_the_caller_and_one_record(record_root):
    entered, release = gate()
    provider = FakeProvider(valid_script(), gates={1: (entered, release)})
    h = Harness(record_root, provider)
    h.start()
    assert entered.wait(10)
    assert h.slot.busy()
    h.clock.set(D + MS)
    h.thread.join(10)
    r = h.result
    snapshot = r.model_dump_json()
    assert r.reasons == ("CALL_UNRESOLVED_AT_DEADLINE",) and r.limitations == ("REMOTE_OUTCOME_UNKNOWN", "LOCAL_WORKER_MAY_STILL_RUN")
    assert h.slot.busy()                                          # the stuck worker keeps the slot
    busy = h.svc.interpret(T1, T, INPUTS)
    assert (busy.status, busy.reasons, busy.persistence, busy.record_path) == (
        AIStatus.AI_NOT_REQUESTED, ("PREVIOUS_CALL_UNRESOLVED",), Persistence.NOT_ATTEMPTED, None)
    release.set()                                                 # the late VALID payload arrives
    wait_for(lambda: not h.slot.busy())
    inv = h.svc.last_invocation
    assert inv.caller_outcome is r and r.model_dump_json() == snapshot and len(provider.calls) == 1
    rec = load_record(r.record_path)
    assert rec.status is AIStatus.AI_UNAVAILABLE and rec.interpretation is None and rec.raw_response is None
    assert rec.attempts[0].outcome == "DISCARDED_AFTER_DEADLINE" and "LATE_WORKER_RESULT_DISCARDED" in rec.limitations
    assert len(h.records(record_root)) == 1 and inv.record_attempts == 1
    assert "cancel" not in open(r.record_path).read().lower()                # no cancellation is claimed


# ---------------------------------------------------------------------- DL cases
def test_dl1_t4_no_attempt_without_enough_time(record_root, monkeypatch):
    real_select = service_module.select

    def late_select(*args):
        h.clock.set(D - 24.9)                     # now + 20 s > D - R
        return real_select(*args)
    monkeypatch.setattr(service_module, "select", late_select)
    h = Harness(record_root)
    r = h.start().release_caller()
    assert (r.status, r.reasons) == (AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_BEFORE_REQUEST",))
    assert h.provider.calls == [] and r.persistence is Persistence.COMMITTED


def test_dl3_valid_too_late_to_persist(record_root):
    entered, release = gate()
    h = Harness(record_root, FakeProvider(valid_script(), gates={1: (entered, release)}))
    h.start()
    assert entered.wait(10)
    h.clock.set(D - 5.0 + MS)
    release.set()
    r = h.release_caller()
    assert (r.status, r.reasons, r.persistence) == (
        AIStatus.AI_UNAVAILABLE, ("INSUFFICIENT_TIME_TO_PERSIST",), Persistence.COMMITTED)
    assert load_record(r.record_path).interpretation is None


def test_dl5_caller_thread_does_no_io_and_attempt_budget(record_root, monkeypatch):
    threads = []
    real_select = service_module.select

    def spy(*args):
        threads.append(threading.get_ident())
        return real_select(*args)
    monkeypatch.setattr(service_module, "select", spy)
    h = Harness(record_root)
    r = h.start().release_caller()
    assert r.status is AIStatus.VALID
    caller = h.caller_thread
    assert caller not in threads + h.ops.threads + h.provider.threads
    (attempt, connect, read) = h.provider.calls[0]
    assert attempt == 1 and connect == 5.0 and read == 25.0          # B = min(30, D - R - now)


def test_worker_start_failure_and_no_cancellation_claim(record_root, monkeypatch):
    h = Harness(record_root)
    with monkeypatch.context() as m:
        m.setattr(threading.Thread, "start", lambda self: (_ for _ in ()).throw(RuntimeError("no thread")))
        r = h.svc.interpret(T1, T, INPUTS)
    assert (r.status, r.reasons, r.persistence_detail) == (
        AIStatus.AI_UNAVAILABLE, ("WORKER_START_FAILED",), PersistenceDetail.NO_RECORD)
    assert not h.slot.busy() and os.listdir(record_root) == []
    src = open(service_module.__file__).read().lower()
    assert "cancelled" not in src and "canceled" not in src
