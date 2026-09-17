"""Immutable C05 quality contracts and explicit freshness policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from traid.domain.models import DataQualityState
from traid.exchange.contract import CapabilityAvailability
from traid.exchange.contract_types import Capability


QUALITY_SCHEMA_VERSION = "1.0"
QUALITY_POLICY_VERSION = "c05-policy-1"


class _QualityModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
        str_strip_whitespace=True,
    )


class FreshnessBasis(StrEnum):
    SOURCE_TIMESTAMP = "SOURCE_TIMESTAMP"
    RECEIPT_TIMESTAMP = "RECEIPT_TIMESTAMP"
    UNAVAILABLE = "UNAVAILABLE"


class ProvenanceQuality(StrEnum):
    COMPLETE = "COMPLETE"
    LIMITED = "LIMITED"


class ContinuityStatus(StrEnum):
    PROVEN = "PROVEN"
    UNKNOWN = "UNKNOWN"
    GAP_RISK = "GAP_RISK"


class RecoveryStatus(StrEnum):
    NONE = "NONE"
    RECOVERING = "RECOVERING"
    RECOVERED_WITHOUT_REPLAY_PROOF = "RECOVERED_WITHOUT_REPLAY_PROOF"


class FreshnessThreshold(_QualityModel):
    """Inclusive LIVE and DELAYED upper bounds for one capability."""

    capability: Capability
    live_max_age: timedelta = Field(gt=timedelta(0))
    delayed_max_age: timedelta = Field(gt=timedelta(0))

    @model_validator(mode="after")
    def validate_order(self) -> "FreshnessThreshold":
        if self.delayed_max_age <= self.live_max_age:
            raise ValueError("delayed_max_age must be greater than live_max_age")
        return self


class QualityPolicy(_QualityModel):
    """Versioned, inspectable C05 policy; no runtime environment is required."""

    schema_version: str = QUALITY_SCHEMA_VERSION
    policy_version: str = QUALITY_POLICY_VERSION
    thresholds: tuple[FreshnessThreshold, ...]

    @model_validator(mode="after")
    def validate_thresholds(self) -> "QualityPolicy":
        capabilities = tuple(item.capability for item in self.thresholds)
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("freshness thresholds must identify each capability once")
        return self

    def threshold_for(self, capability: Capability) -> FreshnessThreshold:
        for threshold in self.thresholds:
            if threshold.capability is capability:
                return threshold
        raise KeyError(f"no freshness threshold configured for {capability.value}")


class QualityAssessment(_QualityModel):
    """The complete deterministic quality fact set exposed downstream."""

    schema_version: str = QUALITY_SCHEMA_VERSION
    capability: Capability
    state: DataQualityState
    coverage_availability: CapabilityAvailability
    coverage_limitation: str | None = None
    provenance_quality: ProvenanceQuality
    freshness_basis: FreshnessBasis
    source_age: timedelta | None = None
    receipt_age: timedelta | None = None
    evaluation_time: datetime
    policy_version: str
    continuity: ContinuityStatus
    recovery: RecoveryStatus
    reasons: tuple[str, ...]
    trusted_for_current_use: bool

    @field_validator("evaluation_time")
    @classmethod
    def normalize_evaluation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluation_time must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("source_age", "receipt_age")
    @classmethod
    def validate_age(cls, value: timedelta | None) -> timedelta | None:
        if value is not None and value < timedelta(0):
            raise ValueError("quality ages cannot be negative")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> "QualityAssessment":
        if not self.reasons:
            raise ValueError("quality assessment requires at least one reason")
        if self.freshness_basis is FreshnessBasis.RECEIPT_TIMESTAMP and self.source_age is not None:
            raise ValueError("receipt freshness cannot report source age")
        if self.state is DataQualityState.UNAVAILABLE and self.trusted_for_current_use:
            raise ValueError("unavailable data cannot be trusted for current use")
        if self.trusted_for_current_use:
            violations: list[str] = []
            if self.state is not DataQualityState.LIVE:
                violations.append("state must be LIVE")
            if self.coverage_availability is not CapabilityAvailability.SUPPORTED:
                violations.append("coverage must be SUPPORTED")
            if self.coverage_limitation:
                violations.append("trusted data cannot carry a coverage limitation")
            if self.provenance_quality is not ProvenanceQuality.COMPLETE:
                violations.append("provenance must be COMPLETE")
            if self.freshness_basis is not FreshnessBasis.SOURCE_TIMESTAMP or self.source_age is None:
                violations.append("source freshness must be proven")
            if self.continuity is not ContinuityStatus.PROVEN:
                violations.append("continuity must be PROVEN")
            if self.recovery is not RecoveryStatus.NONE:
                violations.append("recovery must be NONE")
            if self.reasons != ("QUALITY_WITHIN_POLICY",):
                violations.append("trusted assessment cannot carry degradation reasons")
            if violations:
                raise ValueError("trusted_for_current_use invariants failed: " + "; ".join(violations))
        return self


def default_quality_policy() -> QualityPolicy:
    """Return the explicit conservative C05 policy shipped with V1.

    These are TraID classification thresholds, not claims about provider
    publication cadence. Open interest is intentionally absent because C04
    marks its Hyperliquid semantics unavailable and unverified.
    """

    return QualityPolicy(
        thresholds=(
            FreshnessThreshold(capability=Capability.TRADES, live_max_age=timedelta(seconds=5), delayed_max_age=timedelta(seconds=30)),
            FreshnessThreshold(capability=Capability.ORDER_BOOK, live_max_age=timedelta(seconds=5), delayed_max_age=timedelta(seconds=15)),
            FreshnessThreshold(capability=Capability.CANDLES, live_max_age=timedelta(seconds=90), delayed_max_age=timedelta(seconds=180)),
            FreshnessThreshold(capability=Capability.FUNDING, live_max_age=timedelta(minutes=5), delayed_max_age=timedelta(minutes=30)),
            FreshnessThreshold(capability=Capability.MARKET_CONTEXT, live_max_age=timedelta(seconds=30), delayed_max_age=timedelta(minutes=2)),
        ),
    )
