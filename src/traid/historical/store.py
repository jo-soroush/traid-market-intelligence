"""Content-addressed C06 JSONL publication and verify-before-load."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from traid.domain import Candle, FundingSnapshot
from traid.historical.dataset import (
    DatasetError,
    canonical_json,
    event_object,
    manifest_bytes,
    records_bytes,
    validate_dataset,
    validate_manifest_header,
)
from traid.historical.models import Category, DatasetManifest, HistoricalDataset, HistoricalEvent, timestamp_text


SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_DATA_BYTES = 8_000_000
MAX_MANIFEST_BYTES = 40_000
REPO_ROOT = Path(__file__).resolve().parents[3]


def _root(path: Path | str) -> Path:
    root = Path(path).absolute()
    if not root.is_dir():
        raise DatasetError("caller-supplied storage root must already exist")
    if root.resolve() != root or root == REPO_ROOT or REPO_ROOT in root.parents:
        raise DatasetError("storage root must be an ordinary directory outside Git")
    if any(parent.is_symlink() for parent in (root, *root.parents)):
        raise DatasetError("storage root may not traverse a symlink")
    return root


def _write_file(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def _read_file(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise DatasetError(f"dataset file unavailable: {path.name}") from error
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise DatasetError("dataset file type or size is invalid")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise DatasetError("dataset file exceeds limit")
        return data
    finally:
        os.close(fd)


def publish_dataset(root: Path | str, dataset: HistoricalDataset) -> Path:
    """Publish one complete directory by same-filesystem rename; never overwrite."""
    base = _root(root)
    validate_dataset(dataset)
    identity = dataset.manifest.dataset_id
    if not SHA256.fullmatch(identity):
        raise DatasetError("invalid dataset identity")
    final = base / identity
    if final.exists() or final.is_symlink():
        raise DatasetError("published dataset already exists")
    payload = records_bytes(dataset.records)
    manifest = manifest_bytes(dataset.manifest)
    if len(payload) > MAX_DATA_BYTES or len(manifest) > MAX_MANIFEST_BYTES:
        raise DatasetError("dataset exceeds bounded storage size")
    stage = Path(tempfile.mkdtemp(prefix=".traid-c06-stage-", dir=base))
    try:
        _write_file(stage / "records.jsonl", payload)
        _write_file(stage / "manifest.json", manifest)
        directory_fd = os.open(stage, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if final.exists() or final.is_symlink():
            raise DatasetError("published dataset already exists")
        os.rename(stage, final)
        parent_fd = os.open(base, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        return final
    except BaseException:
        if stage.exists():
            for child in stage.iterdir():
                child.unlink()
            stage.rmdir()
        raise


def _strict_json(raw: bytes) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in items:
            if key in output:
                raise DatasetError("duplicate JSON key")
            output[key] = value
        return output

    def invalid_constant(value: str) -> None:
        raise DatasetError(f"invalid JSON numeric constant: {value}")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DatasetError("malformed or truncated JSON") from error


def _strict_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DatasetError("timestamp must be canonical UTC text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DatasetError("invalid timestamp representation") from error
    if parsed.tzinfo != timezone.utc or timestamp_text(parsed) != value:
        raise DatasetError("non-canonical UTC timestamp")
    return parsed


def _decode_records(payload: bytes) -> tuple[HistoricalEvent, ...]:
    if payload and not payload.endswith(b"\n"):
        raise DatasetError("truncated JSONL final record")
    records: list[HistoricalEvent] = []
    for line in payload.splitlines():
        raw = _strict_json(line)
        if not isinstance(raw, dict) or set(raw) != {"category", "event_time", "availability_time", "value"}:
            raise DatasetError("record envelope is invalid")
        value = raw["value"]
        if not isinstance(value, dict) or not isinstance(value.get("provenance"), dict):
            raise DatasetError("canonical value or provenance is missing")
        try:
            category = Category(raw["category"])
        except (ValueError, TypeError) as error:
            raise DatasetError("unsupported record category") from error
        decimals = ("open", "high", "low", "close", "volume") if category is Category.CANDLE else ("funding_rate",)
        if any(not isinstance(value.get(field), str) for field in decimals):
            raise DatasetError("canonical decimal must be encoded as text")
        for field in ("start_timestamp", "end_timestamp") if category is Category.CANDLE else ("timestamp",):
            _strict_timestamp(value.get(field))
        for field in ("source_timestamp", "received_timestamp"):
            if value["provenance"].get(field) is not None:
                _strict_timestamp(value["provenance"][field])
        try:
            canonical = (Candle if category is Category.CANDLE else FundingSnapshot).model_validate(value)
            event = HistoricalEvent(category, canonical, _strict_timestamp(raw["event_time"]), _strict_timestamp(raw["availability_time"]))
        except DatasetError:
            raise
        except (ValueError, TypeError) as error:
            raise DatasetError("invalid canonical record") from error
        if canonical_json(event_object(event)) != line:
            raise DatasetError("record bytes are not canonical")
        records.append(event)
    return tuple(records)


def load_dataset(root: Path | str, dataset_id: str) -> HistoricalDataset:
    """Verify exact stored bytes and metadata before parsing or returning any event."""
    base = _root(root)
    if not SHA256.fullmatch(dataset_id):
        raise DatasetError("invalid dataset path identity")
    folder = base / dataset_id
    if folder.is_symlink() or not folder.is_dir() or folder.resolve() != folder:
        raise DatasetError("dataset directory is absent or unsafe")
    manifest_raw = _read_file(folder / "manifest.json", MAX_MANIFEST_BYTES)
    manifest_data = _strict_json(manifest_raw)
    if not isinstance(manifest_data, dict) or canonical_json(manifest_data) + b"\n" != manifest_raw:
        raise DatasetError("manifest bytes are not canonical")
    try:
        manifest = DatasetManifest.model_validate(manifest_data)
    except ValueError as error:
        raise DatasetError("invalid dataset manifest") from error
    if manifest.dataset_id != dataset_id:
        raise DatasetError("manifest path identity mismatch")
    validate_manifest_header(manifest)
    payload = _read_file(folder / "records.jsonl", MAX_DATA_BYTES)
    if hashlib.sha256(payload).hexdigest() != manifest.data_sha256:
        raise DatasetError("stored record bytes failed SHA-256 verification")
    dataset = HistoricalDataset(manifest, _decode_records(payload))
    validate_dataset(dataset)
    return dataset
