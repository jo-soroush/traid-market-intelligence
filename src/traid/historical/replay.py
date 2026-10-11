"""Pull-based C06 replay using modeled availability time, never receipt time."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Iterator

from traid.historical.dataset import DatasetError, validate_dataset
from traid.historical.models import Category, HistoricalDataset, HistoricalEvent, utc


def replay(
    dataset: HistoricalDataset,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    as_of: datetime | None = None,
    categories: Iterable[Category] | None = None,
) -> Iterator[HistoricalEvent]:
    """Filter a validated sequence by half-open availability range and inclusive as-of."""
    validate_dataset(dataset)
    lower = utc(start) if start is not None else None
    upper = utc(end) if end is not None else None
    cutoff = utc(as_of) if as_of is not None else None
    if lower is not None and upper is not None and lower > upper:
        raise DatasetError("replay start cannot exceed end")
    selected = None if categories is None else frozenset(categories)
    if selected is not None and any(not isinstance(item, Category) for item in selected):
        raise DatasetError("invalid replay category")
    return iter(tuple(event for event in dataset.records if
        (lower is None or event.availability_time >= lower)
        and (upper is None or event.availability_time < upper)
        and (cutoff is None or event.availability_time <= cutoff)
        and (selected is None or event.category in selected)
    ))
