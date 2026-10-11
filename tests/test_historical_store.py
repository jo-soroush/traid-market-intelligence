"""C06 atomic publication and verify-before-load failure matrix."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from traid.historical import load_dataset, publish_dataset
from traid.historical.dataset import DatasetError, build_dataset, manifest_bytes, manifest_core_bytes, records_bytes, validate_dataset
from traid.historical.models import Category
from traid.historical.store import _decode_records

from test_historical_dataset import BASE, FETCHED, candle, funding


def sample():
    return build_dataset([candle(0), candle(1)], [funding(0)], window_start=BASE, window_end=BASE + timedelta(hours=2), fetched_at=FETCHED)


@pytest.fixture
def outside_root(tmp_path: Path) -> Path:
    return tmp_path


def test_build_store_load_replay_preserves_exact_canonical_values(outside_root):
    expected = sample()
    path = publish_dataset(outside_root, expected)
    assert path.name == expected.manifest.dataset_id
    assert (path / "records.jsonl").read_bytes() == records_bytes(expected.records)
    assert (path / "manifest.json").read_bytes() == manifest_bytes(expected.manifest)
    assert load_dataset(outside_root, path.name) == expected
    loaded_candle = next(item for item in load_dataset(outside_root, path.name).records if item.category is Category.CANDLE)
    assert str(loaded_candle.value.volume) == "3.000"


def test_existing_published_dataset_cannot_be_overwritten(outside_root):
    value = sample()
    publish_dataset(outside_root, value)
    with pytest.raises(DatasetError, match="already exists"):
        publish_dataset(outside_root, value)


def test_tampered_or_truncated_bytes_fail_before_parse(outside_root):
    value = sample()
    path = publish_dataset(outside_root, value)
    records = path / "records.jsonl"
    records.write_bytes(records.read_bytes().replace(b"3.000", b"9.000"))
    with pytest.raises(DatasetError, match="SHA-256"):
        load_dataset(outside_root, value.manifest.dataset_id)
    records.write_bytes(records.read_bytes()[:-4])
    with pytest.raises(DatasetError, match="SHA-256"):
        load_dataset(outside_root, value.manifest.dataset_id)


def test_absent_manifest_or_partial_directory_fails_closed(outside_root):
    value = sample()
    path = publish_dataset(outside_root, value)
    (path / "manifest.json").unlink()
    with pytest.raises(DatasetError, match="unavailable"):
        load_dataset(outside_root, value.manifest.dataset_id)
    assert list(outside_root.glob(".traid-c06-stage-*")) == []


def test_symlink_escape_and_path_traversal_are_rejected(outside_root):
    value = sample()
    path = publish_dataset(outside_root, value)
    (path / "records.jsonl").unlink()
    (path / "records.jsonl").symlink_to("/etc/hosts")
    with pytest.raises(DatasetError, match="unavailable"):
        load_dataset(outside_root, value.manifest.dataset_id)
    with pytest.raises(DatasetError, match="path identity"):
        load_dataset(outside_root, "../outside")
    other = outside_root.parent / (outside_root.name + "-link")
    try:
        other.symlink_to(outside_root, target_is_directory=True)
        with pytest.raises(DatasetError, match="outside Git|symlink"):
            load_dataset(other, value.manifest.dataset_id)
    finally:
        other.unlink(missing_ok=True)


def test_storage_root_inside_git_or_unavailable_is_rejected(outside_root):
    value = sample()
    with pytest.raises(DatasetError, match="outside Git"):
        publish_dataset(Path(__file__).resolve().parents[1], value)
    with pytest.raises(DatasetError, match="already exist"):
        publish_dataset(outside_root / "missing", value)


def test_json_numeric_decimal_missing_provenance_and_unknown_category_rejected():
    value = sample()
    raw = next(json.loads(line) for line in records_bytes(value.records).splitlines() if b'"category":"CANDLE"' in line)
    raw["value"]["volume"] = 3.0
    with pytest.raises(DatasetError, match="decimal"):
        _decode_records(json.dumps(raw).encode() + b"\n")
    raw["value"]["volume"] = "3.000"
    raw["value"].pop("provenance")
    with pytest.raises(DatasetError, match="provenance"):
        _decode_records(json.dumps(raw).encode() + b"\n")
    raw["value"]["provenance"] = value.records[0].value.provenance.model_dump(mode="json")
    raw["category"] = "OPEN_INTEREST"
    with pytest.raises(DatasetError, match="category"):
        _decode_records(json.dumps(raw).encode() + b"\n")


def test_malformed_timestamp_and_truncated_jsonl_rejected():
    value = sample()
    raw = json.loads(records_bytes(value.records).splitlines()[0])
    raw["event_time"] = "2026-10-01T00:00:00+02:00"
    with pytest.raises(DatasetError, match="timestamp"):
        _decode_records(json.dumps(raw).encode() + b"\n")
    with pytest.raises(DatasetError, match="truncated"):
        _decode_records(records_bytes(value.records)[:-1])


def test_manifest_identity_and_schema_version_are_checked(outside_root):
    value = sample()
    path = publish_dataset(outside_root, value)
    manifest_path = path / "manifest.json"
    modified = json.loads(manifest_path.read_bytes())
    modified["domain_schema_version"] = "99"
    manifest_path.write_text(json.dumps(modified, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(DatasetError, match="unsupported|identity"):
        load_dataset(outside_root, value.manifest.dataset_id)


def test_manifest_count_and_gap_claims_must_match_records():
    value = sample()
    for change, reason in (({"record_count": 99}, "record count"), ({"candle_gap_starts": (BASE,)}, "candle gap")):
        changed = replace(value, manifest=value.manifest.model_copy(update=change))
        changed_manifest = changed.manifest.model_copy(update={"dataset_id": hashlib.sha256(manifest_core_bytes(changed.manifest)).hexdigest()})
        changed = replace(changed, manifest=changed_manifest)
        with pytest.raises(DatasetError, match=reason):
            validate_dataset(changed)


def test_valid_hashes_cannot_publish_or_load_an_early_received_candle(outside_root):
    value = sample()
    original = next(event for event in value.records if event.category is Category.CANDLE)
    early = replace(original, value=candle(0, received=BASE + timedelta(minutes=30)))
    records = tuple(early if event == original else event for event in value.records)
    changed_manifest = value.manifest.model_copy(update={"data_sha256": hashlib.sha256(records_bytes(records)).hexdigest()})
    changed_manifest = changed_manifest.model_copy(update={"dataset_id": hashlib.sha256(manifest_core_bytes(changed_manifest)).hexdigest()})
    forged = replace(value, manifest=changed_manifest, records=records)
    with pytest.raises(DatasetError, match="incomplete candle"):
        publish_dataset(outside_root, forged)
    folder = outside_root / changed_manifest.dataset_id
    folder.mkdir()
    (folder / "records.jsonl").write_bytes(records_bytes(records))
    (folder / "manifest.json").write_bytes(manifest_bytes(changed_manifest))
    with pytest.raises(DatasetError, match="incomplete candle"):
        load_dataset(outside_root, changed_manifest.dataset_id)
