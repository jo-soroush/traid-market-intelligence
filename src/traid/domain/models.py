"""Canonical, provider-neutral domain models for V1-C02."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DOMAIN_SCHEMA_VERSION = "1.0"
UTC = timezone.utc


def _aware_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise TypeError("timestamps must be datetime values")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _nonempty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("text values must not be empty")
    return value


class CanonicalModel(BaseModel):
    """Immutable C02 values with one explicit serialized schema version."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
        str_strip_whitespace=True,
    )

    schema_version: str = DOMAIN_SCHEMA_VERSION
    _schema_version: ClassVar[str] = DOMAIN_SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != cls._schema_version:
            raise ValueError(f"unsupported schema version: {value}")
        return value

    @field_validator(
        "timestamp",
        "source_timestamp",
        "received_timestamp",
        "start_timestamp",
        "end_timestamp",
        "as_of_timestamp",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return _aware_utc(value)

    @field_validator("symbol", "source", "source_type", "source_id", "evidence_id", "evidence_type", mode="before", check_fields=False)
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        return None if value is None else _nonempty(value)


class DataQualityState(StrEnum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class SourceProvenance(CanonicalModel):
    source: str
    source_type: str
    source_id: str | None = None
    source_timestamp: datetime
    received_timestamp: datetime

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "SourceProvenance":
        if self.received_timestamp < self.source_timestamp:
            raise ValueError("received_timestamp cannot precede source_timestamp")
        return self


class EvidenceReference(CanonicalModel):
    """Small addressable evidence link; registry behavior belongs to C15."""

    evidence_id: str
    evidence_type: str
    provenance: SourceProvenance
    related_symbol: str | None = None


class MarketTrade(CanonicalModel):
    symbol: str
    price: Decimal = Field(gt=Decimal("0"))
    quantity: Decimal = Field(gt=Decimal("0"))
    timestamp: datetime
    provenance: SourceProvenance


class OrderBookLevel(CanonicalModel):
    price: Decimal = Field(gt=Decimal("0"))
    quantity: Decimal = Field(ge=Decimal("0"))


class OrderBookSnapshot(CanonicalModel):
    symbol: str
    bids: tuple[OrderBookLevel, ...] = ()
    asks: tuple[OrderBookLevel, ...] = ()
    timestamp: datetime
    provenance: SourceProvenance


class Candle(CanonicalModel):
    symbol: str
    start_timestamp: datetime
    end_timestamp: datetime
    open: Decimal = Field(gt=Decimal("0"))
    high: Decimal = Field(gt=Decimal("0"))
    low: Decimal = Field(gt=Decimal("0"))
    close: Decimal = Field(gt=Decimal("0"))
    volume: Decimal = Field(ge=Decimal("0"))
    provenance: SourceProvenance

    @model_validator(mode="after")
    def validate_candle(self) -> "Candle":
        if self.end_timestamp <= self.start_timestamp:
            raise ValueError("candle end_timestamp must be after start_timestamp")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("candle high/low must contain open and close")
        return self


class FundingSnapshot(CanonicalModel):
    symbol: str
    funding_rate: Decimal
    timestamp: datetime
    provenance: SourceProvenance


class OpenInterestSnapshot(CanonicalModel):
    symbol: str
    open_interest: Decimal = Field(ge=Decimal("0"))
    timestamp: datetime
    provenance: SourceProvenance


class LiquidationEvent(CanonicalModel):
    symbol: str
    price: Decimal = Field(gt=Decimal("0"))
    quantity: Decimal = Field(gt=Decimal("0"))
    timestamp: datetime
    provenance: SourceProvenance


class PriceSnapshot(CanonicalModel):
    symbol: str
    price: Decimal = Field(gt=Decimal("0"))
    timestamp: datetime
    provenance: SourceProvenance


class MarketContext(CanonicalModel):
    symbol: str
    as_of_timestamp: datetime
    data_quality: DataQualityState
    evidence: tuple[EvidenceReference, ...] = ()
    provenance: tuple[SourceProvenance, ...] = ()
