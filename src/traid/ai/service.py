"""C14 interpretation service: one bounded, fail-closed model call per invocation.

Concurrency and deadline (final F1):

* One process-wide slot, taken without blocking; a busy slot returns
  ``AI_NOT_REQUESTED:PREVIOUS_CALL_UNRESOLVED`` with no thread and no record. The worker releases the
  slot in ``finally``, so a stuck worker keeps it (one outstanding request per process).
* The caller does only bounded in-memory work: it starts one worker and waits on its completion event
  until ``D = t0 + 65 s`` (monotonic, ``t0`` at entry). Every blocking phase (selection, SETUP, SEND,
  validation, the record write) runs in the worker. No cancellation is ever claimed.
* Every transition is stamped with ``monotonic()`` while holding the lock. An event counts as before
  the deadline only if ``t < D``; ``t == D`` is late. The first actor holding the lock at or after D
  seals an immutable snapshot of the state reached by transitions stamped before D, with
  ``deadline_outcome = decide(snapshot)``; nothing after D can change what the caller receives.
* After the seal a worker before COMMITTING sends nothing more, sets no outcome and writes exactly one
  deferred record with the deadline outcome (``LATE_WORKER_RESULT_DISCARDED``); a worker in COMMITTING
  finishes that one commit. Exactly one record attempt per invocation, at most two application attempts.
* An interpretation is released only when the commit was confirmed and the caller finalized strictly
  before D (row O1). A late or unconfirmed VALID is withheld; a deliberate skip stays AI_NOT_REQUESTED
  even when its record fails.

Fail-closed structured-output patterns are adapted as methods only from the Quant Flow reference
(SOURCE FILE NOT YET VERIFIED; no code copied, its invalid-output retry deliberately not adopted).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import threading
import time
import uuid

from traid.ai.models import (
    AIAnalysisRecord, AIResult, AIStatus, AttemptRecord, BoundedRaw, Measure, ModelMetadata, Persistence,
    PersistenceDetail, ValidatedInterpretation,
)
from traid.ai.prompts import SYSTEM_PROMPT, TOOL_DESCRIPTION, TOOL_NAME, TOOL_SCHEMA
from traid.ai.provider import AIProvider, ModelReply, ProviderFailure, ProviderRequest
from traid.ai.records import RecordStore
from traid.ai.selection import EvidenceInputs, Selection, select
from traid.ai.validation import validate_reply

UTC = timezone.utc
DEADLINE_S = 65.0
COMMIT_RESERVE_S = 5.0
ATTEMPT_MIN_S = 20.0
ATTEMPT_MAX_S = 30.0
CONNECT_MAX_S = 5.0
BACKOFF_S = 2.0
MAX_TOKENS = 2000
TEMPERATURE = 0.0
MAX_ATTEMPTS = 2
RAW_PREFIX_CHARS = 4096
RELEASE_RULE = "RELEASED_ONLY_IF_COMMIT_CONFIRMED_AND_CALLER_FINALIZED_STRICTLY_BEFORE_DEADLINE"
LATE = "LATE_WORKER_RESULT_DISCARDED"


class Phase(StrEnum):
    SELECTING = "SELECTING"
    SETUP = "SETUP"
    SENDING = "SENDING"
    BACKOFF = "BACKOFF"
    VALIDATING = "VALIDATING"
    COMMITTING = "COMMITTING"
    DONE = "DONE"


class Terminal(StrEnum):
    COMMITTED = "COMMITTED"
    FAILED_NOT_PUBLISHED = "FAILED_NOT_PUBLISHED"
    UNCONFIRMED = "UNCONFIRMED"


class InvariantDefect(RuntimeError):
    """An unreachable state: never handled silently."""


# ----------------------------------------------------------------------------- clock
class Clock:
    """Real time. Tests inject a clock that can return exactly the deadline."""
    def monotonic(self) -> float:
        return time.monotonic()

    def wall(self) -> datetime:
        return datetime.now(UTC)

    def wait_until(self, event: threading.Event, deadline: float) -> None:
        event.wait(max(0.0, deadline - self.monotonic()))

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class ProcessSlot:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        self._lock.release()

    def busy(self) -> bool:
        return self._lock.locked()


PROCESS_SLOT = ProcessSlot()


# -------------------------------------------------------------------------- decide()
@dataclass(frozen=True)
class PreOutcome:
    status: AIStatus
    reasons: tuple[str, ...]
    interpretation: ValidatedInterpretation | None = None


@dataclass(frozen=True)
class Snapshot:
    phase: Phase | None
    pre: PreOutcome | None
    terminal: Terminal | None


@dataclass(frozen=True)
class Decision:
    row: str
    status: AIStatus
    reasons: tuple[str, ...]
    release: bool
    persistence: Persistence
    detail: PersistenceDetail
    persistence_reason: str | None
    pre_persistence_status: AIStatus | None
    limitations: tuple[str, ...] = ()


_PERSISTENCE = {Terminal.COMMITTED: Persistence.COMMITTED, Terminal.FAILED_NOT_PUBLISHED: Persistence.FAILED,
                Terminal.UNCONFIRMED: Persistence.UNCONFIRMED}
_ROW = {Terminal.COMMITTED: "", Terminal.FAILED_NOT_PUBLISHED: "F", Terminal.UNCONFIRMED: "C"}


def _combine(pre: PreOutcome, terminal: Terminal, *, late: bool, unresolved: bool) -> Decision:
    detail = PersistenceDetail.UNRESOLVED_AT_DEADLINE if unresolved else PersistenceDetail.TERMINAL
    persistence = _PERSISTENCE[terminal]
    path = "U" if unresolved else ("L" if late else "O")
    if terminal is Terminal.COMMITTED:
        if pre.status is AIStatus.VALID:
            if late:
                return Decision("L1", AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_BEFORE_RELEASE",), False,
                                persistence, detail, None, AIStatus.VALID)
            return Decision("O1", AIStatus.VALID, pre.reasons, True, persistence, detail, None, None)
        row = f"{path}{2 if pre.status is AIStatus.AI_NOT_REQUESTED else 3}"
        return Decision(row, pre.status, pre.reasons, False, persistence, detail, None, None)
    sub = {AIStatus.AI_NOT_REQUESTED: "a", AIStatus.VALID: "b", AIStatus.AI_INVALID: "b", AIStatus.AI_UNAVAILABLE: "c"}
    row = f"{path}{'' if unresolved else _ROW[terminal]}{sub[pre.status]}"
    if pre.status is AIStatus.AI_NOT_REQUESTED:
        return Decision(row, pre.status, pre.reasons, False, persistence, detail, "RECORD_WRITE_FAILED", None)
    if pre.status in (AIStatus.VALID, AIStatus.AI_INVALID):
        return Decision(row, AIStatus.AI_UNAVAILABLE, ("RECORD_WRITE_FAILED",), False, persistence, detail,
                        "RECORD_WRITE_FAILED", pre.status)
    return Decision(row, pre.status, pre.reasons, False, persistence, detail, "RECORD_WRITE_FAILED", None)


def decide(s: Snapshot, *, on_time: bool) -> Decision:
    """The complete, mutually exclusive decision table (final F1, 24 rows)."""
    if on_time:
        if s.phase is not Phase.DONE or s.pre is None or s.terminal is None:
            raise InvariantDefect("on-time finalization requires DONE with an outcome and a terminal commit")
        return _combine(s.pre, s.terminal, late=False, unresolved=False)
    if s.phase is Phase.DONE:
        if s.pre is None or s.terminal is None:
            raise InvariantDefect("DONE requires an outcome and a terminal commit")
        return _combine(s.pre, s.terminal, late=True, unresolved=False)
    if s.phase is Phase.COMMITTING:
        if s.pre is None or s.terminal is not None:
            raise InvariantDefect("COMMITTING requires an outcome and no terminal before the deadline")
        return _combine(s.pre, Terminal.UNCONFIRMED, late=True, unresolved=True)
    if s.pre is not None or s.terminal is not None:
        raise InvariantDefect("an outcome is set only together with COMMITTING")
    deferred = PersistenceDetail.DEFERRED_AFTER_FINALIZATION
    if s.phase in (None, Phase.SELECTING, Phase.SETUP):
        return Decision("N1", AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_BEFORE_REQUEST",), False,
                        Persistence.NOT_ATTEMPTED, deferred, None, None)
    if s.phase in (Phase.SENDING, Phase.BACKOFF):
        return Decision("N2", AIStatus.AI_UNAVAILABLE, ("CALL_UNRESOLVED_AT_DEADLINE",), False,
                        Persistence.NOT_ATTEMPTED, deferred, None, None,
                        ("REMOTE_OUTCOME_UNKNOWN", "LOCAL_WORKER_MAY_STILL_RUN"))
    if s.phase is Phase.VALIDATING:
        return Decision("N3", AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_DURING_VALIDATION",), False,
                        Persistence.NOT_ATTEMPTED, deferred, None, None)
    raise InvariantDefect(f"unknown phase {s.phase}")


# ------------------------------------------------------------------------ invocation
@dataclass
class _Invocation:
    clock: Clock
    deadline: float
    run_id: str
    file_name: str
    invoked_at: datetime
    lock: threading.Lock = field(default_factory=threading.Lock)
    done: threading.Event = field(default_factory=threading.Event)
    phase: Phase | None = None
    log: list = field(default_factory=list)
    pre: PreOutcome | None = None
    terminal: Terminal | None = None
    sealed: Snapshot | None = None
    deadline_decision: Decision | None = None
    sealed_by: str | None = None
    caller_outcome: AIResult | None = None
    late_results: int = 0
    record_attempts: int = 0

    def _seal(self, actor: str) -> None:
        if self.sealed is None:
            self.sealed = Snapshot(self.phase, self.pre, self.terminal)
            self.deadline_decision = decide(self.sealed, on_time=False)
            self.sealed_by = actor

    def _late(self, actor: str, now: float) -> bool:
        """Under the lock, with the one timestamp of this transition: True (and sealed) once a seal
        exists or ``now`` is at or after D. Exactly D is late."""
        if self.sealed is not None:
            return True
        if now >= self.deadline:
            self._seal(actor)
            return True
        return False

    def enter(self, phase: Phase) -> bool:
        with self.lock:
            now = self.clock.monotonic()          # the single clock read of this transition
            if self._late("worker", now):
                return False
            self.phase = phase
            self.log.append((phase, now))
            return True

    def alive(self) -> bool:
        with self.lock:
            return not self._late("worker", self.clock.monotonic())

    def room(self, needed: float) -> bool | None:
        """None when late (sealed); otherwise whether ``needed`` seconds fit before D - R."""
        with self.lock:
            now = self.clock.monotonic()
            if self._late("worker", now):
                return None
            return now + needed <= self.deadline - COMMIT_RESERVE_S

    def commit_step(self, pre: PreOutcome) -> PreOutcome | None:
        """Atomic step A: the pre-persistence outcome, the VALID downgrade and COMMITTING together."""
        with self.lock:
            now = self.clock.monotonic()
            if self._late("worker", now):
                return None
            if pre.status is AIStatus.VALID and now > self.deadline - COMMIT_RESERVE_S:
                pre = PreOutcome(AIStatus.AI_UNAVAILABLE, ("INSUFFICIENT_TIME_TO_PERSIST",))
            self.pre = pre
            self.phase = Phase.COMMITTING
            self.log.append((Phase.COMMITTING, now))
            self.record_attempts += 1
            return pre

    def try_finalize(self, build=None) -> Decision | AIResult | None:
        """The caller's finalization: one clock read, the decision and the assignment of the caller's
        outcome in the same locked step. None when woken early (before D and not DONE). With ``build``
        the caller outcome is built and assigned here and returned; it is never reassigned."""
        with self.lock:
            if self.caller_outcome is not None:
                return self.caller_outcome
            now = self.clock.monotonic()
            if now < self.deadline:
                if self.phase is not Phase.DONE:
                    return None
                decision = decide(Snapshot(self.phase, self.pre, self.terminal), on_time=True)
            else:
                self._seal("caller")
                decision = self.deadline_decision
            if build is None:
                return decision
            interpretation = self.pre.interpretation if decision.release else None
            self.caller_outcome = build(decision, interpretation)
            return self.caller_outcome

    def finish_commit(self, terminal: Terminal) -> None:
        with self.lock:
            now = self.clock.monotonic()
            self._late("worker", now)             # seals first if this stamp is at or after D
            self.terminal = terminal
            self.phase = Phase.DONE
            self.log.append((Phase.DONE, now))
            self.done.set()


# ---------------------------------------------------------------------------- service
@dataclass
class _Work:
    selection: Selection | None = None
    attempts: list = field(default_factory=list)
    reply: ModelReply | None = None
    tool_input_sha256: str | None = None


class AIService:
    def __init__(self, provider: AIProvider | None, store: RecordStore, *, clock: Clock | None = None,
                 slot: ProcessSlot | None = None, price_table_version: str | None = None) -> None:
        self.provider = provider
        self.store = store
        self.clock = clock or Clock()
        self.slot = slot or PROCESS_SLOT
        self.price_table_version = price_table_version
        self.late_results = 0
        self.last_invocation: _Invocation | None = None

    # ------------------------------------------------------------------ caller side
    def interpret(self, task, evaluation_time, inputs: EvidenceInputs) -> AIResult:
        """Never raises. Returns by the deadline whatever the worker does."""
        t0 = self.clock.monotonic()
        if not self.slot.try_acquire():
            return AIResult(run_id=None, status=AIStatus.AI_NOT_REQUESTED, reasons=("PREVIOUS_CALL_UNRESOLVED",),
                            interpretation=None, persistence=Persistence.NOT_ATTEMPTED,
                            persistence_detail=PersistenceDetail.NO_RECORD, persistence_reason=None,
                            pre_persistence_status=None, record_path=None, limitations=())
        run_id = uuid.uuid4().hex
        invoked_at = self.clock.wall()
        name = f"{invoked_at.astimezone(UTC):%Y%m%dT%H%M%S%f}Z-{run_id}.json"
        inv = _Invocation(clock=self.clock, deadline=t0 + DEADLINE_S, run_id=run_id, file_name=name,
                          invoked_at=invoked_at)
        self.last_invocation = inv
        try:
            worker = threading.Thread(target=self._worker, args=(inv, task, evaluation_time, inputs),
                                      name="traid-c14-invocation", daemon=True)
            worker.start()
        except Exception:
            self.slot.release()
            return AIResult(run_id=run_id, status=AIStatus.AI_UNAVAILABLE, reasons=("WORKER_START_FAILED",),
                            interpretation=None, persistence=Persistence.NOT_ATTEMPTED,
                            persistence_detail=PersistenceDetail.NO_RECORD, persistence_reason=None,
                            pre_persistence_status=None, record_path=None, limitations=())
        return self._finalize(inv)

    def _finalize(self, inv: _Invocation) -> AIResult:
        while True:
            self.clock.wait_until(inv.done, inv.deadline)
            outcome = inv.try_finalize(lambda d, interpretation: self._result(inv, d, interpretation))
            if outcome is not None:
                return outcome
            # woken early: wait again

    def _result(self, inv: _Invocation, d: Decision, interpretation) -> AIResult:
        record_path = self.store.path_for(inv.file_name) if d.persistence in (
            Persistence.COMMITTED, Persistence.UNCONFIRMED) or d.detail is PersistenceDetail.DEFERRED_AFTER_FINALIZATION \
            else None
        return AIResult(run_id=inv.run_id, status=d.status, reasons=d.reasons, interpretation=interpretation,
                        persistence=d.persistence, persistence_detail=d.detail, persistence_reason=d.persistence_reason,
                        pre_persistence_status=d.pre_persistence_status, record_path=record_path,
                        limitations=d.limitations + (interpretation.limitations if interpretation else ()))

    # ------------------------------------------------------------------ worker side
    def _worker(self, inv: _Invocation, task, evaluation_time, inputs: EvidenceInputs) -> None:
        work = _Work()
        try:
            pre = self._run(inv, work, task, evaluation_time, inputs)
            if pre is None:
                self._deferred(inv, work)
                return
            final = inv.commit_step(pre)
            if final is None:
                self._deferred(inv, work)
                return
            terminal = self._commit(inv, work, final, status=final.status, reasons=final.reasons,
                                    interpretation=final.interpretation, limitations=())
            inv.finish_commit(terminal)
            with inv.lock:
                if inv.sealed is not None:
                    inv.late_results += 1
                    self.late_results += 1
        except Exception:
            # Fail closed: never let a defect escape the worker, and never start a second record attempt.
            try:
                with inv.lock:
                    phase, attempts = inv.phase, inv.record_attempts
                if attempts:
                    if phase is Phase.COMMITTING:
                        inv.finish_commit(Terminal.UNCONFIRMED)
                    return
                final = inv.commit_step(PreOutcome(AIStatus.AI_UNAVAILABLE, ("INTERNAL_ERROR",)))
                if final is None:
                    self._deferred(inv, work)
                else:
                    inv.finish_commit(self._commit(inv, work, final, status=final.status, reasons=final.reasons,
                                                   interpretation=None, limitations=()))
            except Exception:
                pass
        finally:
            self.slot.release()

    def _run(self, inv: _Invocation, work: _Work, task, evaluation_time, inputs) -> PreOutcome | None:
        """Selection, SETUP, attempts and validation. None means the deadline seal intervened."""
        if not inv.enter(Phase.SELECTING):
            return None
        if self.provider is None:
            work.selection = select(task, evaluation_time, inputs)
            return PreOutcome(AIStatus.AI_NOT_REQUESTED, ("AI_DISABLED",))
        sel = work.selection = select(task, evaluation_time, inputs)
        if sel.skip:
            return PreOutcome(AIStatus.AI_NOT_REQUESTED, sel.skip)
        room = inv.room(ATTEMPT_MIN_S)
        if room is None:
            return None
        if not room:
            return PreOutcome(AIStatus.AI_UNAVAILABLE, ("DEADLINE_EXCEEDED_BEFORE_REQUEST",))
        if not inv.enter(Phase.SETUP):
            return None
        session = self.provider.setup()
        if isinstance(session, ProviderFailure):
            if not inv.alive():
                return None
            return PreOutcome(AIStatus.AI_UNAVAILABLE, (session.code,))
        request = ProviderRequest(system_prompt=SYSTEM_PROMPT, user_text=sel.request_json, tool_name=TOOL_NAME,
                                  tool_description=TOOL_DESCRIPTION, tool_schema=TOOL_SCHEMA, max_tokens=MAX_TOKENS,
                                  temperature=TEMPERATURE)
        attempt = 1
        while True:
            if not inv.enter(Phase.SENDING):
                return None
            budget = min(ATTEMPT_MAX_S, inv.deadline - COMMIT_RESERVE_S - self.clock.monotonic())
            connect = min(CONNECT_MAX_S, budget)
            read = max(1.0, budget - connect)
            started = self.clock.monotonic()
            reply = self.provider.send(session, request, attempt, connect, read)
            duration = int((self.clock.monotonic() - started) * 1000)
            offset = int((started - (inv.deadline - DEADLINE_S)) * 1000)
            if not inv.alive():
                work.attempts.append(AttemptRecord(number=attempt, outcome="DISCARDED_AFTER_DEADLINE", error_code=None,
                                                   retry_safe=False, http_sends=min(reply.http_sends, 2),
                                                   started_offset_ms=max(0, offset), duration_ms=duration))
                return None
            if isinstance(reply, ProviderFailure):
                work.attempts.append(AttemptRecord(number=attempt, outcome="FAILURE", error_code=reply.code,
                                                   retry_safe=reply.retry_safe, http_sends=min(reply.http_sends, 2),
                                                   started_offset_ms=max(0, offset), duration_ms=duration,
                                                   request_id=reply.request_id))
                if reply.retry_safe and attempt < MAX_ATTEMPTS:
                    room = inv.room(BACKOFF_S + ATTEMPT_MIN_S)
                    if room is None:
                        return None
                    if room:
                        if not inv.enter(Phase.BACKOFF):
                            return None
                        self.clock.sleep(BACKOFF_S)
                        attempt += 1
                        continue
                return PreOutcome(AIStatus.AI_UNAVAILABLE, (reply.code,))
            work.reply = reply
            work.attempts.append(AttemptRecord(
                number=attempt, outcome="RESPONSE", error_code=None, retry_safe=False,
                http_sends=min(reply.http_sends, 2), started_offset_ms=max(0, offset), duration_ms=duration,
                stop_reason=reply.stop_reason, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
                total_tokens=reply.total_tokens, provider_latency_ms=reply.provider_latency_ms,
                request_id=reply.request_id))
            if not inv.enter(Phase.VALIDATING):
                return None
            result = validate_reply(reply, sel.context, self.clock.wall())
            work.tool_input_sha256 = result.tool_input_sha256
            if not result.valid:
                return PreOutcome(AIStatus.AI_INVALID, (result.code,))
            return PreOutcome(AIStatus.VALID, (), result.interpretation)

    def _deferred(self, inv: _Invocation, work: _Work) -> None:
        """P4(a): the one record of an invocation sealed before COMMITTING, written after the caller's
        outcome was fixed. It carries the deadline outcome, never a late provider result."""
        with inv.lock:
            d = inv.deadline_decision
            inv.record_attempts += 1
        if d is None:
            raise InvariantDefect("a deferred record requires a seal")
        work.reply = None
        work.tool_input_sha256 = None
        self._commit(inv, work, None, status=d.status, reasons=d.reasons, interpretation=None,
                     limitations=d.limitations + (LATE,))
        with inv.lock:
            inv.late_results += 1
            self.late_results += 1

    def _commit(self, inv: _Invocation, work: _Work, final: PreOutcome | None, *, status, reasons, interpretation,
                limitations) -> Terminal:
        try:
            record = self._record(inv, work, status, reasons, interpretation, limitations)
        except Exception:
            return Terminal.FAILED_NOT_PUBLISHED
        try:
            outcome = self.store.publish(record, inv.file_name)
        except Exception:
            return Terminal.UNCONFIRMED
        return Terminal(outcome.kind)

    def _record(self, inv: _Invocation, work: _Work, status, reasons, interpretation, limitations) -> AIAnalysisRecord:
        sel = work.selection
        model = None
        if self.provider is not None:
            p = self.provider.describe()
            model = ModelMetadata(
                provider=p.provider, api=p.api, model_id_sent=p.model_id, source_region=p.source_region,
                approved_destination_regions=p.approved_destination_regions,
                destinations_verified_on=p.destinations_verified_on, temperature=Decimal(str(TEMPERATURE)),
                max_tokens=MAX_TOKENS, cost=Measure(value=None, unit="USD", reason="PRICE_TABLE_NOT_CONFIGURED"),
                price_table_version=self.price_table_version)
        raw = None
        if work.reply is not None:
            text = work.reply.raw_text
            cut = len(text.encode()) > 64 * 1024
            raw = BoundedRaw(content=text[:RAW_PREFIX_CHARS] if cut else text,
                             sha256=hashlib.sha256(text.encode()).hexdigest(), size_bytes=work.reply.raw_size,
                             truncated=cut, omitted_reason="RESPONSE_LIMIT_EXCEEDED_PREFIX_ONLY" if cut else None)
        extra = ("SMALL_SAMPLE_AGGREGATES_MAY_REVEAL_INDIVIDUAL_ACTIVITY",) if sel and sel.released_whale_aggregate else ()
        return AIAnalysisRecord(
            run_id=inv.run_id, invoked_at=inv.invoked_at, decided_at=self.clock.wall(),
            deadline_at=inv.invoked_at + timedelta(seconds=DEADLINE_S), release_rule=RELEASE_RULE, status=status,
            reasons=tuple(reasons), task_id=sel.task_id if sel else "UNKNOWN",
            evaluation_time=sel.evaluation_time if sel else None, request=sel.request if sel else None,
            request_sha256=sel.request_sha256 if sel else None, excluded_items=sel.excluded if sel else (),
            attempts=tuple(work.attempts), model=model, interpretation=interpretation,
            tool_input_sha256=work.tool_input_sha256, raw_response=raw,
            private_bindings=sel.bindings if sel else None,
            limitations=tuple(dict.fromkeys((*limitations, *extra))))


def interpret(task, evaluation_time, inputs: EvidenceInputs, *, provider: AIProvider | None, store: RecordStore,
              clock: Clock | None = None) -> AIResult:
    """Convenience entry point using the process-wide slot."""
    return AIService(provider, store, clock=clock).interpret(task, evaluation_time, inputs)
