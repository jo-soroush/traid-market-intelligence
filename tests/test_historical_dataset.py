"""C06 deterministic dataset and temporal-integrity obligations."""

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import permutations

import pytest

from traid.domain import Candle, FundingSnapshot, OpenInterestSnapshot, SourceProvenance
from traid.historical.dataset import DatasetError, build_dataset, manifest_core_bytes, records_bytes, validate_dataset
from traid.historical.models import Category


BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)
FETCHED = BASE + timedelta(days=2)


def candle(hour: int, *, received: datetime = FETCHED, close: str = "2.00") -> Candle:
    start = BASE + timedelta(hours=hour)
    return Candle(
        symbol="BTC", start_timestamp=start, end_timestamp=start + timedelta(hours=1, milliseconds=-1),
        open=Decimal("1.00"), high=Decimal("2.00"), low=Decimal("1.00"), close=Decimal(close), volume=Decimal("3.000"),
        provenance=SourceProvenance(source="hyperliquid", source_type="public_info", source_id=str(int(start.timestamp() * 1000)), source_timestamp=start, received_timestamp=received),
    )


def funding(hour: int, *, rate: str = "-0.000125", received: datetime = FETCHED) -> FundingSnapshot:
    event = BASE + timedelta(hours=hour, milliseconds=51)
    return FundingSnapshot(
        symbol="BTC", funding_rate=Decimal(rate), timestamp=event,
        provenance=SourceProvenance(source="hyperliquid", source_type="public_info", source_id="fundingHistory", source_timestamp=event, received_timestamp=received),
    )


def dataset(candles=None, funds=None, hours=3):
    return build_dataset(candles if candles is not None else [candle(i) for i in range(hours)], funds if funds is not None else [funding(0)], window_start=BASE, window_end=BASE + timedelta(hours=hours), fetched_at=FETCHED)


def test_canonical_values_and_provenance_round_trip_exactly():
    result = dataset()
    first = next(item for item in result.records if item.category is Category.CANDLE)
    assert first.value == candle(0)
    assert str(first.value.volume) == "3.000"
    assert first.value.provenance.received_timestamp == FETCHED
    assert result.manifest.domain_schema_version == first.value.schema_version
    assert result.manifest.availability_method == "INFERRED_POLICY"
    assert result.manifest.publication_latency_status == "NOT_VERIFIED"


def test_input_permutations_have_identical_bytes_and_identity():
    values = [candle(2), candle(0), candle(1)]
    funds = [funding(2), funding(0)]
    baseline = dataset(values, funds)
    for permuted in permutations(values):
        for permuted_funds in permutations(funds):
            current = dataset(permuted, permuted_funds)
            assert current.manifest.dataset_id == baseline.manifest.dataset_id
            assert records_bytes(current.records) == records_bytes(baseline.records)


def test_identical_boundary_duplicates_collapse_to_earliest_receipt():
    late = FETCHED + timedelta(seconds=2)
    first = candle(0, received=late)
    second = candle(0, received=FETCHED)
    a = dataset([first, second, candle(1), candle(2)], [funding(0, received=late), funding(0)])
    b = dataset([second, first, candle(2), candle(1)], [funding(0), funding(0, received=late)])
    assert a.manifest.dataset_id == b.manifest.dataset_id
    assert a.manifest.candle_duplicate_count == 1
    assert a.manifest.funding_duplicate_count == 1
    assert a.records[0].value.provenance.received_timestamp == FETCHED


def test_conflicting_duplicates_fail_closed():
    with pytest.raises(DatasetError, match="conflicting duplicate"):
        dataset([candle(0), candle(0, close="1.50")])
    with pytest.raises(DatasetError, match="conflicting duplicate"):
        dataset([candle(0)], [funding(0), funding(0, rate="0.01")])


def test_missing_candle_gap_and_unknown_funding_continuity_are_explicit():
    result = dataset([candle(0), candle(2)], [])
    assert result.manifest.candle_gap_starts == (BASE + timedelta(hours=1),)
    assert result.manifest.candle_coverage.status == "PARTIAL"
    assert result.manifest.funding_coverage.count == 0
    assert result.manifest.funding_coverage.status == "UNKNOWN"
    assert result.manifest.funding_interval_status == "UNVERIFIED"
    assert result.manifest.funding_continuity == "UNKNOWN"
    assert len(result.records) == 2  # No synthetic bar or funding event.


def test_incomplete_bar_is_excluded_and_counted():
    end = BASE + timedelta(hours=2)
    first = candle(0, received=end)
    second = candle(1, received=end)
    boundary = candle(2, received=end)
    result = build_dataset([first, second, boundary], [], window_start=BASE, window_end=end, fetched_at=end)
    assert result.manifest.record_count == 2
    assert result.manifest.incomplete_bar_count == 1
    assert all(event.event_time < end for event in result.records)
    with pytest.raises(DatasetError, match="fully closed"):
        build_dataset([first, second], [], window_start=BASE, window_end=end, fetched_at=end - timedelta(seconds=1))


def test_early_received_candle_cannot_become_completed_history():
    early = candle(0, received=BASE + timedelta(minutes=30))
    result = build_dataset([early], [], window_start=BASE, window_end=BASE + timedelta(hours=1), fetched_at=FETCHED)
    assert result.manifest.record_count == 0
    assert result.manifest.incomplete_bar_count == 1
    assert result.manifest.candle_gap_starts == (BASE,)
    assert result.manifest.candle_coverage.status == "PARTIAL"


def test_hashed_dataset_cannot_bypass_record_level_candle_completion():
    original = dataset([candle(0)], [], hours=1)
    event = original.records[0]
    early = candle(0, received=BASE + timedelta(minutes=30))
    forged = replace(event, value=early)
    records = (forged,)
    changed = original.manifest.model_copy(update={"data_sha256": hashlib.sha256(records_bytes(records)).hexdigest()})
    changed = changed.model_copy(update={"dataset_id": hashlib.sha256(manifest_core_bytes(changed)).hexdigest()})
    with pytest.raises(DatasetError, match="incomplete candle"):
        validate_dataset(replace(original, manifest=changed, records=records))


def test_funding_value_is_not_reinterpreted_or_costed():
    result = dataset([candle(0)], [funding(0, rate="-0.00012500")], hours=1)
    event = next(item for item in result.records if item.category is Category.FUNDING_SNAPSHOT)
    assert str(event.value.funding_rate) == "-0.00012500"
    assert event.availability_time == event.event_time + timedelta(seconds=60)
    assert result.manifest.funding_offset_seconds == 60


def test_candle_availability_is_close_plus_policy_offset():
    event = next(item for item in dataset([candle(0)], [], hours=1).records)
    assert event.event_time == BASE
    assert event.availability_time == BASE + timedelta(hours=1, seconds=60)
    assert event.value.provenance.received_timestamp == FETCHED


def test_replay_envelope_rejects_non_utc_offset_even_for_same_instant():
    event = dataset([candle(0)], [], hours=1).records[0]
    with pytest.raises(ValueError, match="must be UTC"):
        replace(event, event_time=event.event_time.astimezone(timezone(timedelta(hours=1))))


def test_rejects_oi_and_wrong_instrument_without_conversion():
    provenance = funding(0).provenance
    oi = OpenInterestSnapshot(symbol="BTC", open_interest=Decimal("1"), timestamp=BASE, provenance=provenance)
    with pytest.raises(DatasetError, match="canonical BTC candles"):
        dataset([oi], [])
    with pytest.raises(DatasetError, match="canonical BTC funding"):
        dataset([candle(0)], [oi])


@pytest.mark.parametrize("hours", [0, 169])
def test_window_must_be_bounded(hours):
    with pytest.raises(DatasetError, match="1 to 168"):
        dataset([], [], hours=hours)


def test_tampered_in_memory_record_cannot_replay_or_publish():
    baseline = dataset()
    changed = replace(baseline, records=baseline.records[:-1])
    with pytest.raises(DatasetError, match="record hash mismatch"):
        validate_dataset(changed)


def test_unsupported_version_and_offset_fail_closed():
    baseline = dataset()
    for field, value in (("dataset_format_version", "2.0"), ("availability_policy_version", "2.0"), ("candle_offset_seconds", 0)):
        changed = replace(baseline, manifest=baseline.manifest.model_copy(update={field: value}))
        with pytest.raises(DatasetError, match="unsupported|offsets"):
            validate_dataset(changed)
