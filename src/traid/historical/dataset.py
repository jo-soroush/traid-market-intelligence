"""Deterministic C06 construction, byte identity, coverage, and integrity rules."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Iterable

from traid.domain import Candle, FundingSnapshot
from traid.domain.models import DOMAIN_SCHEMA_VERSION
from traid.historical.models import (
    AVAILABILITY_POLICY_VERSION,
    CANDLE_OFFSET_SECONDS,
    DATASET_FORMAT_VERSION,
    FUNDING_OFFSET_SECONDS,
    HOUR,
    NORMALIZATION_POLICY_VERSION,
    Category,
    Coverage,
    DatasetManifest,
    HistoricalDataset,
    HistoricalEvent,
    timestamp_text,
    utc,
)


class DatasetError(ValueError):
    """Historical data cannot be published or trusted."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def event_object(event: HistoricalEvent) -> dict[str, object]:
    return {
        "category": event.category.value,
        "event_time": timestamp_text(event.event_time),
        "availability_time": timestamp_text(event.availability_time),
        "value": event.value.model_dump(mode="json"),
    }


def records_bytes(records: tuple[HistoricalEvent, ...]) -> bytes:
    return b"".join(canonical_json(event_object(event)) + b"\n" for event in records)


def manifest_core_bytes(manifest: DatasetManifest) -> bytes:
    return canonical_json(manifest.model_dump(mode="json", exclude={"dataset_id"}))


def manifest_bytes(manifest: DatasetManifest) -> bytes:
    return canonical_json(manifest.model_dump(mode="json")) + b"\n"


def _source_identity(value: Candle | FundingSnapshot) -> bytes:
    payload = value.model_dump(mode="json")
    payload["provenance"].pop("received_timestamp")
    return canonical_json(payload)


def _unique(values: Iterable[Candle | FundingSnapshot], *, candle: bool) -> tuple[tuple[Candle | FundingSnapshot, ...], int]:
    seen: dict[datetime, Candle | FundingSnapshot] = {}
    duplicates = 0
    for value in values:
        key = value.start_timestamp if candle else value.timestamp
        old = seen.get(key)
        if old is None:
            seen[key] = value
            continue
        if _source_identity(old) != _source_identity(value):
            raise DatasetError(f"conflicting duplicate at {timestamp_text(key)}")
        duplicates += 1
        if value.provenance.received_timestamp < old.provenance.received_timestamp:
            seen[key] = value
    return tuple(seen[key] for key in sorted(seen)), duplicates


def _coverage(times: tuple[datetime, ...], status: str) -> Coverage:
    return Coverage(status=status, count=len(times), first_event_time=times[0] if times else None, last_event_time=times[-1] if times else None)


def _sort_key(event: HistoricalEvent) -> tuple[datetime, datetime, str, bytes]:
    return event.availability_time, event.event_time, event.category.value, canonical_json(event_object(event))


def build_dataset(
    candles: Iterable[Candle],
    funding: Iterable[FundingSnapshot],
    *,
    window_start: datetime,
    window_end: datetime,
    fetched_at: datetime,
    source: str = "hyperliquid",
    source_type: str = "public_info",
    source_endpoint: str = "https://api.hyperliquid.xyz/info",
) -> HistoricalDataset:
    """Build one bounded, half-open BTC 1h window without filling missing data."""
    start, end, fetched = utc(window_start), utc(window_end), utc(fetched_at)
    if start.minute or start.second or start.microsecond or end.minute or end.second or end.microsecond:
        raise DatasetError("C06 window boundaries must be aligned to UTC hours")
    hours = (end - start) / HOUR
    if not 0 < hours <= 168 or not hours.is_integer():
        raise DatasetError("C06 window must contain 1 to 168 whole hours")
    if fetched < end:
        raise DatasetError("the requested history window is not fully closed at fetch time")
    if not source.strip() or not source_type.strip() or not source_endpoint.strip():
        raise DatasetError("source metadata is required")
    complete: list[Candle] = []
    incomplete_count = 0
    for candle in candles:
        if not isinstance(candle, Candle) or candle.symbol != "BTC":
            raise DatasetError("only canonical BTC candles are supported")
        bar_end = candle.start_timestamp + HOUR
        if candle.end_timestamp != bar_end - timedelta(milliseconds=1):
            raise DatasetError("1h candle end must be the provider's inclusive final millisecond")
        if candle.start_timestamp.minute or candle.start_timestamp.second or candle.start_timestamp.microsecond:
            raise DatasetError("1h candle start must align to an hour")
        if candle.start_timestamp == end and (candle.provenance.received_timestamp < bar_end or bar_end > fetched):
            incomplete_count += 1
            continue  # A provider may include the still-open exclusive boundary bar.
        if not start <= candle.start_timestamp < end:
            continue  # The API may include the exclusive end-boundary candle.
        if candle.provenance.received_timestamp < bar_end or bar_end > fetched:
            incomplete_count += 1
            continue
        complete.append(candle)
    unique_candles, candle_duplicates = _unique(complete, candle=True)
    eligible_funding: list[FundingSnapshot] = []
    for item in funding:
        if not isinstance(item, FundingSnapshot) or item.symbol != "BTC":
            raise DatasetError("only canonical BTC funding snapshots are supported")
        if start <= item.timestamp < end:
            eligible_funding.append(item)
    unique_funding, funding_duplicates = _unique(eligible_funding, candle=False)
    candle_starts = tuple(item.start_timestamp for item in unique_candles)
    funding_times = tuple(item.timestamp for item in unique_funding)
    present = set(candle_starts)
    gap_starts = tuple(start + index * HOUR for index in range(int(hours)) if start + index * HOUR not in present)
    records = tuple(sorted((
        *(HistoricalEvent(Category.CANDLE, item, item.start_timestamp, item.start_timestamp + HOUR + timedelta(seconds=CANDLE_OFFSET_SECONDS)) for item in unique_candles),
        *(HistoricalEvent(Category.FUNDING_SNAPSHOT, item, item.timestamp, item.timestamp + timedelta(seconds=FUNDING_OFFSET_SECONDS)) for item in unique_funding),
    ), key=_sort_key))
    data_hash = hashlib.sha256(records_bytes(records)).hexdigest()
    core = {
        "dataset_format_version": DATASET_FORMAT_VERSION,
        "domain_schema_version": DOMAIN_SCHEMA_VERSION,
        "normalization_policy_version": NORMALIZATION_POLICY_VERSION,
        "availability_policy_version": AVAILABILITY_POLICY_VERSION,
        "source": source.strip(), "source_type": source_type.strip(), "source_endpoint": source_endpoint.strip(),
        "symbol": "BTC", "interval": "1h", "window_start": start, "window_end": end, "fetched_at": fetched,
        "availability_method": "INFERRED_POLICY", "publication_latency_status": "NOT_VERIFIED",
        "candle_offset_seconds": CANDLE_OFFSET_SECONDS, "funding_offset_seconds": FUNDING_OFFSET_SECONDS,
        "funding_interval_status": "UNVERIFIED", "funding_continuity": "UNKNOWN",
        "candle_coverage": _coverage(candle_starts, "COMPLETE" if not gap_starts and not incomplete_count else "PARTIAL"),
        "funding_coverage": _coverage(funding_times, "UNKNOWN"),
        "candle_gap_starts": gap_starts,
        "candle_duplicate_count": candle_duplicates, "funding_duplicate_count": funding_duplicates,
        "incomplete_bar_count": incomplete_count, "record_count": len(records),
        "limitations": (
            "Provider publication timestamps are not verified; replay availability is inferred policy, not observed exchange availability.",
            "Historical backfills and revisions may change a later fetch of the same window.",
            "Funding cadence and continuity are unknown; no funding gaps or costs are inferred.",
            "The public candle API has rolling retention; unavailable older history is not filled.",
        ),
        "data_sha256": data_hash,
    }
    temporary = DatasetManifest(**core, dataset_id="0" * 64)
    manifest = temporary.model_copy(update={"dataset_id": hashlib.sha256(manifest_core_bytes(temporary)).hexdigest()})
    result = HistoricalDataset(manifest, records)
    validate_dataset(result)
    return result


def validate_manifest_header(manifest: DatasetManifest) -> None:
    """Reject unsupported or unsafe metadata before decoding record payloads."""
    if (manifest.dataset_format_version, manifest.domain_schema_version, manifest.normalization_policy_version, manifest.availability_policy_version) != (
        DATASET_FORMAT_VERSION, DOMAIN_SCHEMA_VERSION, NORMALIZATION_POLICY_VERSION, AVAILABILITY_POLICY_VERSION,
    ):
        raise DatasetError("unsupported dataset or policy version")
    if manifest.candle_offset_seconds != CANDLE_OFFSET_SECONDS or manifest.funding_offset_seconds != FUNDING_OFFSET_SECONDS:
        raise DatasetError("availability offsets disagree with the versioned policy")
    if not re.fullmatch(r"[0-9a-f]{64}", manifest.data_sha256) or not re.fullmatch(r"[0-9a-f]{64}", manifest.dataset_id):
        raise DatasetError("dataset SHA-256 format is invalid")
    start, end = manifest.window_start, manifest.window_end
    hours = (end - start) / HOUR
    if (start.minute, start.second, start.microsecond, end.minute, end.second, end.microsecond) != (0, 0, 0, 0, 0, 0) or not 0 < hours <= 168 or not hours.is_integer():
        raise DatasetError("manifest window is not a bounded 1h-aligned interval")
    if manifest.fetched_at < end or not manifest.source.strip() or not manifest.source_type.strip() or not manifest.source_endpoint.strip():
        raise DatasetError("manifest source or closed-window proof is missing")


def validate_dataset(dataset: HistoricalDataset) -> None:
    """Fail before publication or replay if any content or version is inconsistent."""
    manifest = dataset.manifest
    validate_manifest_header(manifest)
    if hashlib.sha256(manifest_core_bytes(manifest)).hexdigest() != manifest.dataset_id:
        raise DatasetError("manifest identity mismatch")
    if hashlib.sha256(records_bytes(dataset.records)).hexdigest() != manifest.data_sha256:
        raise DatasetError("record hash mismatch")
    if manifest.record_count != len(dataset.records) or tuple(sorted(dataset.records, key=_sort_key)) != dataset.records:
        raise DatasetError("record count or total ordering mismatch")
    candles: list[datetime] = []
    funding: list[datetime] = []
    seen: set[tuple[Category, datetime]] = set()
    for event in dataset.records:
        expected_time = event.value.start_timestamp if event.category is Category.CANDLE else event.value.timestamp
        expected_availability = (expected_time + HOUR + timedelta(seconds=CANDLE_OFFSET_SECONDS)) if event.category is Category.CANDLE else (expected_time + timedelta(seconds=FUNDING_OFFSET_SECONDS))
        provenance = event.value.provenance
        if (provenance.source != manifest.source or provenance.source_type != manifest.source_type
                or not provenance.source_id or provenance.source_timestamp != expected_time
                or provenance.received_timestamp > manifest.fetched_at):
            raise DatasetError("record source or receipt provenance is inconsistent")
        if event.category is Category.CANDLE:
            if event.value.end_timestamp != expected_time + HOUR - timedelta(milliseconds=1):
                raise DatasetError("published candle interval is invalid")
            if provenance.received_timestamp < expected_time + HOUR:
                raise DatasetError("incomplete candle received before interval close")
        if event.event_time != expected_time or event.availability_time != expected_availability:
            raise DatasetError("replay timestamp disagrees with availability policy")
        if not manifest.window_start <= expected_time < manifest.window_end:
            raise DatasetError("record is outside the half-open dataset window")
        key = (event.category, expected_time)
        if key in seen:
            raise DatasetError("published dataset contains a duplicate")
        seen.add(key)
        (candles if event.category is Category.CANDLE else funding).append(expected_time)
    candle_times = tuple(sorted(candles))
    funding_times = tuple(sorted(funding))
    expected_gaps = tuple(manifest.window_start + i * HOUR for i in range(int((manifest.window_end - manifest.window_start) / HOUR)) if manifest.window_start + i * HOUR not in set(candle_times))
    if tuple(manifest.candle_gap_starts) != expected_gaps:
        raise DatasetError("candle gap manifest does not match records")
    if manifest.candle_coverage != _coverage(candle_times, "COMPLETE" if not expected_gaps and not manifest.incomplete_bar_count else "PARTIAL"):
        raise DatasetError("candle coverage manifest does not match records")
    if manifest.funding_coverage != _coverage(funding_times, "UNKNOWN"):
        raise DatasetError("funding coverage manifest does not match records")
