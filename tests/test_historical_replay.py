"""C06 replay determinism and modeled lookahead boundaries."""

from dataclasses import replace
from datetime import timedelta

import pytest

from traid.historical import replay
from traid.historical.dataset import DatasetError
from traid.historical.models import Category

from test_historical_dataset import BASE, candle, dataset, funding


def mixed():
    return dataset([candle(1), candle(0), candle(2)], [funding(0), funding(1)])


def test_repeated_replay_is_identical_and_does_not_mutate_records():
    value = mixed()
    before = value.records
    first = tuple(replay(value))
    second = tuple(replay(value))
    assert first == second == before
    assert value.records is before


def test_total_order_uses_modeled_availability_then_event_time():
    value = mixed()
    keys = [(item.availability_time, item.event_time, item.category.value) for item in replay(value)]
    assert keys == sorted(keys)


def test_as_of_never_releases_future_modeled_availability():
    value = mixed()
    before_first_candle = BASE + timedelta(hours=1, seconds=59)
    assert all(event.category is Category.FUNDING_SNAPSHOT for event in replay(value, as_of=before_first_candle))
    assert all(event.availability_time <= before_first_candle for event in replay(value, as_of=before_first_candle))
    at_first_candle = tuple(replay(value, as_of=BASE + timedelta(hours=1, seconds=60)))
    assert any(event.category is Category.CANDLE and event.event_time == BASE for event in at_first_candle)


def test_half_open_range_category_filter_and_empty_range():
    value = mixed()
    start = BASE + timedelta(hours=1, seconds=60)
    end = BASE + timedelta(hours=2, seconds=60)
    selected = tuple(replay(value, start=start, end=end, categories=(Category.CANDLE,)))
    assert len(selected) == 1 and selected[0].event_time == BASE
    assert tuple(replay(value, start=start, end=start)) == ()
    assert tuple(replay(value, categories=())) == ()


def test_invalid_range_or_category_fails_closed():
    value = mixed()
    with pytest.raises(DatasetError, match="start cannot exceed"):
        replay(value, start=BASE + timedelta(hours=3), end=BASE)
    with pytest.raises(DatasetError, match="category"):
        replay(value, categories=("OPEN_INTEREST",))


def test_tampered_record_cannot_yield_any_event():
    value = mixed()
    corrupt = replace(value, records=value.records[1:])
    with pytest.raises(DatasetError, match="record hash mismatch"):
        tuple(replay(corrupt))


def test_receipt_time_never_grants_earlier_replay_availability():
    value = mixed()
    event = next(item for item in value.records if item.category is Category.CANDLE)
    assert event.value.provenance.received_timestamp > event.availability_time
    assert event.availability_time == event.event_time + timedelta(hours=1, seconds=60)


def test_future_record_injection_fails_manifest_integrity():
    value = mixed()
    future = dataset([candle(0)], [funding(0)], hours=1).records[-1]
    injected = replace(value, records=value.records + (future,))
    with pytest.raises(DatasetError):
        tuple(replay(injected, as_of=BASE + timedelta(days=5)))
