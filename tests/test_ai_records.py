"""F7: local immutable records and how a persistence outcome combines with the status."""
import errno
import json
import os
from pathlib import Path
import stat
import threading

import pytest

from ai_support import (  # noqa: F401
    T, T1, FakeClock, FakeProvider, FaultyOps, failure, market_state, offline, oserror, record_root, reply, valid_output,
)
from traid.ai import AIService, AIStatus, EvidenceInputs, Persistence, ProcessSlot, RecordStore, load_record
from traid.ai.records import MAX_RECORD_BYTES, REPO_ROOT, RecordStoreError, serialize

INPUTS = EvidenceInputs(market_state=market_state())


def svc(root, provider=None, ops=None):
    p = provider if provider is not None else FakeProvider([lambda r: valid_output(json.loads(r.user_text))])
    return AIService(p, RecordStore(root, ops), clock=FakeClock(), slot=ProcessSlot())


def files(root):
    return sorted(os.listdir(root))


# ---------------------------------------------------------------- one record per status
def test_every_status_writes_exactly_one_committed_record(record_root):
    cases = {
        AIStatus.VALID: (FakeProvider([lambda r: valid_output(json.loads(r.user_text))]), INPUTS),
        AIStatus.AI_INVALID: (FakeProvider([{"summary": "x"}]), INPUTS),
        AIStatus.AI_UNAVAILABLE: (FakeProvider([failure("PROVIDER_ERROR")]), INPUTS),
        AIStatus.AI_NOT_REQUESTED: (FakeProvider(), EvidenceInputs()),
    }
    for status, (provider, inputs) in cases.items():
        before = set(files(record_root))
        result = svc(record_root, provider).interpret(T1, T, inputs)
        new = set(files(record_root)) - before
        assert result.status is status and result.persistence is Persistence.COMMITTED and len(new) == 1
        path = record_root / new.pop()
        assert str(path) == result.record_path
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        rec = load_record(path)
        assert rec.status is status and rec.deadline_at == rec.invoked_at + __import__("datetime").timedelta(seconds=65)
        assert rec.release_rule == "RELEASED_ONLY_IF_COMMIT_CONFIRMED_AND_CALLER_FINALIZED_STRICTLY_BEFORE_DEADLINE"
        assert (rec.interpretation is not None) == (status is AIStatus.VALID)
        if provider.describe() and status is not AIStatus.AI_NOT_REQUESTED:
            assert rec.model.cost.reason == "PRICE_TABLE_NOT_CONFIGURED" and rec.model.model_version == "NOT_REPORTED_BY_API"
    assert not any(f.startswith(".stage-") for f in files(record_root))


def test_record_holds_private_bindings_that_the_request_never_contains(record_root):
    from ai_support import whales
    inputs = EvidenceInputs(market_state=market_state(), whales=whales([("L", "100")] * 6))
    result = svc(record_root).interpret(T1, T, inputs)
    rec = load_record(result.record_path)
    assert rec.private_bindings.whale_contributors and rec.private_bindings.watchlist_digest
    assert "private_bindings" not in rec.request.model_dump_json()
    assert all(a not in rec.request.model_dump_json() for a in rec.private_bindings.whale_contributors)
    assert rec.request_sha256 and "SMALL_SAMPLE_AGGREGATES_MAY_REVEAL_INDIVIDUAL_ACTIVITY" in rec.limitations


# ------------------------------------------------------------- persistence combinations
def test_pers1_skip_with_failed_stage_stays_not_requested(record_root, monkeypatch):
    import traid.ai.selection as selection
    monkeypatch.setattr(selection, "MAX_REQUEST_BYTES", 1024)
    ops = FaultyOps(fail={"write": oserror()})
    result = svc(record_root, FakeProvider(), ops).interpret(T1, T, INPUTS)
    assert (result.status, result.reasons, result.persistence, result.persistence_reason) == (
        AIStatus.AI_NOT_REQUESTED, ("INPUT_LIMIT_EXCEEDED",), Persistence.FAILED, "RECORD_WRITE_FAILED")
    assert result.record_path is None and files(record_root) == []


def test_pers2_skip_with_failed_directory_flush_keeps_the_file(record_root):
    ops = FaultyOps(fail={"fsync_dir": oserror()})
    result = svc(record_root, FakeProvider(), ops).interpret(T1, T, EvidenceInputs())
    assert (result.status, result.persistence, result.persistence_reason) == (
        AIStatus.AI_NOT_REQUESTED, Persistence.UNCONFIRMED, "RECORD_WRITE_FAILED")
    assert os.path.exists(result.record_path) and "unlink" not in ops.calls


def test_pers3_existing_name_is_never_overwritten(record_root, monkeypatch):
    import traid.ai.service as service_module
    fixed = "abcdef0123456789abcdef0123456789"
    monkeypatch.setattr(service_module.uuid, "uuid4", lambda: type("U", (), {"hex": fixed})())
    s = svc(record_root)
    name = f"{s.clock.wall():%Y%m%dT%H%M%S%f}Z-{fixed}.json"
    (record_root / name).write_bytes(b"someone else's bytes")
    result = s.interpret(T1, T, INPUTS)
    assert (result.status, result.reasons, result.pre_persistence_status) == (
        AIStatus.AI_UNAVAILABLE, ("RECORD_WRITE_FAILED",), AIStatus.VALID)
    assert result.interpretation is None and result.persistence is Persistence.FAILED
    assert (record_root / name).read_bytes() == b"someone else's bytes"
    assert not any(f.startswith(".stage-") for f in files(record_root))


def test_pers4_pers5_failed_write_after_a_call(record_root):
    ops = FaultyOps(fail={"link": oserror(errno.EIO)})
    invalid = svc(record_root, FakeProvider([{"summary": "x"}]), ops).interpret(T1, T, INPUTS)
    assert (invalid.status, invalid.reasons, invalid.pre_persistence_status, invalid.persistence) == (
        AIStatus.AI_UNAVAILABLE, ("RECORD_WRITE_FAILED",), AIStatus.AI_INVALID, Persistence.UNCONFIRMED)
    ops = FaultyOps(fail={"fsync_stage": oserror()})
    unavailable = svc(record_root, FakeProvider([failure("PROVIDER_ERROR")]), ops).interpret(T1, T, INPUTS)
    assert (unavailable.status, unavailable.reasons, unavailable.persistence_reason, unavailable.persistence) == (
        AIStatus.AI_UNAVAILABLE, ("PROVIDER_ERROR",), "RECORD_WRITE_FAILED", Persistence.FAILED)


def test_pers6_cleanup_failure_after_commit_changes_nothing(record_root):
    ops = FaultyOps(fail={"unlink": oserror()})
    result = svc(record_root, ops=ops).interpret(T1, T, INPUTS)
    assert result.status is AIStatus.VALID and result.persistence is Persistence.COMMITTED
    assert any(f.startswith(".stage-") for f in files(record_root))          # leftover, never read as a record


def test_commit_point_sequence(record_root):
    ops = FaultyOps()
    svc(record_root, ops=ops).interpret(T1, T, INPUTS)
    assert ops.calls == ["open_root", "open_stage", "write", "fsync_stage", "link", "fsync_dir", "unlink"]
    ops = FaultyOps(fail={"fsync_stage": oserror()})
    result = svc(record_root, ops=ops).interpret(T1, T, INPUTS)
    assert "link" not in ops.calls and result.persistence is Persistence.FAILED


# --------------------------------------------------------------------------- root rules
def test_root_rules(tmp_path, record_root):
    store = RecordStore(REPO_ROOT / "tests")
    rec = load_record(svc(record_root).interpret(T1, T, INPUTS).record_path)
    name = "20261015T120530000000Z-" + rec.run_id + ".json"
    assert store.publish(rec, name).reason == "ROOT_REJECTED"                         # inside the repository
    link = tmp_path / "link"
    link.symlink_to(record_root)
    assert RecordStore(link).publish(rec, name).reason == "ROOT_REJECTED"            # through a symlink
    assert RecordStore("relative/dir").publish(rec, name).reason == "ROOT_REJECTED"
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o770)
    assert RecordStore(shared.resolve()).publish(rec, name).reason == "ROOT_PERMISSIONS"
    assert RecordStore(record_root).publish(rec, "../escape.json").reason == "INVALID_FILE_NAME"


def test_root_swap_after_opening_has_no_effect(tmp_path):
    root = (tmp_path / "root").resolve()
    root.mkdir(mode=0o700)
    entered, release = threading.Event(), threading.Event()
    ops = FaultyOps(block={"open_stage": (entered, release)})
    s = svc(root, ops=ops)
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("r", s.interpret(T1, T, INPUTS)))
    t.start()
    assert entered.wait(10)
    moved = tmp_path / "moved"
    root.rename(moved)
    root.mkdir(mode=0o700)                                    # a different directory now sits at the path
    release.set()
    t.join(10)
    assert out["r"].status is AIStatus.VALID
    assert os.listdir(root) == [] and len([f for f in os.listdir(moved) if f.endswith(".json")]) == 1


def test_concurrent_writers_never_collide(record_root):
    results = []
    threads = [threading.Thread(target=lambda: results.append(
        AIService(FakeProvider([lambda r: valid_output(json.loads(r.user_text))]), RecordStore(record_root),
                  slot=ProcessSlot()).interpret(T1, T, INPUTS))) for _ in range(2)]
    [t.start() for t in threads]
    [t.join(30) for t in threads]
    assert [r.status for r in results] == [AIStatus.VALID] * 2 and len(set(r.record_path for r in results)) == 2


# -------------------------------------------------------------------- size and scans
def test_credential_pattern_is_never_written(record_root):
    rec = load_record(svc(record_root).interpret(T1, T, INPUTS).record_path)
    key = "AKIA" + "Q" * 16                                    # built at run time: the repository scan stays clean
    for planted in (key, "aws_secret_access_key", "AWS_SESSION_TOKEN"):
        bad = rec.model_copy(update={"reasons": (planted,), "run_id": "f" * 32})
        out = RecordStore(record_root).publish(bad, "20261015T120530000000Z-" + "f" * 32 + ".json")
        assert (out.kind, out.reason) == ("FAILED_NOT_PUBLISHED", "CREDENTIAL_PATTERN")
    assert not any("f" * 32 in f for f in files(record_root))


def test_oversized_raw_response_is_bounded_and_oversized_records_drop_it_once(record_root):
    big = valid_output(json.loads(__import__("traid.ai", fromlist=["select"]).select(T1, T, INPUTS).request_json))
    huge = reply(big, raw_size=70 * 1024)
    huge = huge.__class__(**{**huge.__dict__, "raw_text": "x" * (70 * 1024)})
    result = svc(record_root, FakeProvider([huge])).interpret(T1, T, INPUTS)
    assert (result.status, result.reasons) == (AIStatus.AI_INVALID, ("RESPONSE_LIMIT_EXCEEDED",))
    raw = load_record(result.record_path).raw_response
    assert raw.truncated and raw.size_bytes == 70 * 1024 and len(raw.content) == 4096 and raw.omitted_reason
    rec = load_record(result.record_path)
    giant = rec.model_copy(update={"raw_response": raw.model_copy(update={"content": "y" * (MAX_RECORD_BYTES + 10),
                                                                          "truncated": False}),
                                   "run_id": "e" * 32})
    out = RecordStore(record_root).publish(giant, "20261015T120530000000Z-" + "e" * 32 + ".json")
    assert out.kind == "COMMITTED"
    kept = load_record(out.path).raw_response
    assert kept.content is None and kept.omitted_reason == "RECORD_LIMIT" and kept.sha256 == raw.sha256
    still = giant.model_copy(update={"reasons": ("z" * (MAX_RECORD_BYTES + 10),), "run_id": "d" * 32})
    assert RecordStore(record_root).publish(still, "20261015T120530000000Z-" + "d" * 32 + ".json").reason == "RECORD_LIMIT"


def test_load_record_is_bounded_and_schema_checked(record_root, tmp_path):
    path = Path(svc(record_root).interpret(T1, T, INPUTS).record_path)
    assert load_record(path).status is AIStatus.VALID
    bad = tmp_path / "bad.json"
    bad.write_text('{"record_schema": "c14-record-1"}')
    with pytest.raises(Exception):
        load_record(bad)
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (MAX_RECORD_BYTES + 1))
    with pytest.raises(RecordStoreError):
        load_record(big)
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(OSError):
        load_record(link)
    assert serialize(load_record(path)) == path.read_bytes()       # canonical, byte-stable
