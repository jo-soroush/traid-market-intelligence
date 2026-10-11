"""C06 metadata and replay envelopes; C02 remains the canonical value owner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from traid.domain import Candle, FundingSnapshot


UTC = timezone.utc
HOUR = timedelta(hours=1)
DATASET_FORMAT_VERSION = "1.0"
NORMALIZATION_POLICY_VERSION = "1.0"
AVAILABILITY_POLICY_VERSION = "1.0"
CANDLE_OFFSET_SECONDS = 60
FUNDING_OFFSET_SECONDS = 60


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def timestamp_text(value: datetime) -> str:
    return utc(value).isoformat().replace("+00:00", "Z")


class Category(StrEnum):
    CANDLE = "CANDLE"
    FUNDING_SNAPSHOT = "FUNDING_SNAPSHOT"


class Coverage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["COMPLETE", "PARTIAL", "UNKNOWN"]
    count: int = Field(ge=0)
    first_event_time: datetime | None = None
    last_event_time: datetime | None = None

    @field_validator("first_event_time", "last_event_time")
    @classmethod
    def validate_time(cls, value: datetime | None) -> datetime | None:
        return None if value is None else utc(value)


class DatasetManifest(BaseModel):
    """Identity excludes only dataset_id; all other metadata is content-bound."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_format_version: str
    domain_schema_version: str
    normalization_policy_version: str
    availability_policy_version: str
    source: str
    source_type: str
    source_endpoint: str
    symbol: Literal["BTC"]
    interval: Literal["1h"]
    window_start: datetime
    window_end: datetime
    fetched_at: datetime
    availability_method: Literal["INFERRED_POLICY"]
    publication_latency_status: Literal["NOT_VERIFIED"]
    candle_offset_seconds: int
    funding_offset_seconds: int
    funding_interval_status: Literal["UNVERIFIED"]
    funding_continuity: Literal["UNKNOWN"]
    candle_coverage: Coverage
    funding_coverage: Coverage
    candle_gap_starts: tuple[datetime, ...]
    candle_duplicate_count: int = Field(ge=0)
    funding_duplicate_count: int = Field(ge=0)
    incomplete_bar_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    limitations: tuple[str, ...]
    data_sha256: str
    dataset_id: str

    @field_validator("window_start", "window_end", "fetched_at")
    @classmethod
    def validate_time(cls, value: datetime) -> datetime:
        return utc(value)

    @field_validator("candle_gap_starts")
    @classmethod
    def validate_gaps(cls, value: tuple[datetime, ...]) -> tuple[datetime, ...]:
        return tuple(utc(item) for item in value)


@dataclass(frozen=True, slots=True)
class HistoricalEvent:
    category: Category
    value: Candle | FundingSnapshot
    event_time: datetime
    availability_time: datetime

    def __post_init__(self) -> None:
        if self.category is Category.CANDLE and not isinstance(self.value, Candle):
            raise TypeError("CANDLE requires the C02 Candle model")
        if self.category is Category.FUNDING_SNAPSHOT and not isinstance(self.value, FundingSnapshot):
            raise TypeError("FUNDING_SNAPSHOT requires the C02 FundingSnapshot model")
        if self.value.symbol != "BTC":
            raise ValueError("C06 supports BTC perpetual only")
        if self.event_time.utcoffset() != timedelta(0) or self.availability_time.utcoffset() != timedelta(0):
            raise ValueError("event timestamps must be UTC")
        if self.availability_time < self.event_time:
            raise ValueError("availability cannot precede event time")


@dataclass(frozen=True, slots=True)
class HistoricalDataset:
    manifest: DatasetManifest
    records: tuple[HistoricalEvent, ...]
