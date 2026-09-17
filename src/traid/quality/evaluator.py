"""Pure deterministic quality evaluation with explicit fail-closed edges."""

from __future__ import annotations

from datetime import datetime, timezone

from traid.domain.models import DataQualityState, SourceProvenance
from traid.exchange.contract import CapabilityAvailability, CapabilityCoverage
from traid.exchange.contract_types import Capability
from traid.quality.models import (
    ContinuityStatus,
    FreshnessBasis,
    ProvenanceQuality,
    QualityAssessment,
    QualityPolicy,
    RecoveryStatus,
)


class QualityEvaluationError(ValueError):
    """Raised when a quality boundary cannot safely classify its input."""


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise QualityEvaluationError("evaluation_time must be timezone-aware")
    return value.astimezone(timezone.utc)


def _worst(left: DataQualityState, right: DataQualityState) -> DataQualityState:
    rank = {
        DataQualityState.LIVE: 0,
        DataQualityState.DELAYED: 1,
        DataQualityState.STALE: 2,
        DataQualityState.UNAVAILABLE: 3,
    }
    return left if rank[left] >= rank[right] else right


def assess_quality(
    *,
    capability: object,
    provenance: object,
    coverage: object,
    evaluation_time: datetime,
    policy: QualityPolicy,
    continuity: ContinuityStatus,
    recovery: RecoveryStatus,
    canonical_valid: bool,
) -> QualityAssessment:
    """Classify one already-normalized observation without reading the clock.

    Source and receipt ages are always calculated independently. A missing
    source timestamp retains the observation but prevents a LIVE result.
    """

    if not isinstance(capability, Capability):
        raise QualityEvaluationError("unknown capability cannot be quality-assessed")
    if not isinstance(provenance, SourceProvenance):
        raise QualityEvaluationError("quality boundary requires valid SourceProvenance")
    if not isinstance(coverage, CapabilityCoverage):
        raise QualityEvaluationError("quality boundary requires C03 CapabilityCoverage")
    if coverage.capability is not capability:
        raise QualityEvaluationError("coverage capability does not match quality capability")
    if not isinstance(policy, QualityPolicy):
        raise QualityEvaluationError("quality boundary requires QualityPolicy")
    if not isinstance(continuity, ContinuityStatus) or not isinstance(recovery, RecoveryStatus):
        raise QualityEvaluationError("unknown continuity or recovery status")
    if not canonical_valid:
        raise QualityEvaluationError("malformed canonical input is rejected")

    evaluated = _utc(evaluation_time)
    received = _utc(provenance.received_timestamp)
    if evaluated < received:
        raise QualityEvaluationError("evaluation_time cannot precede received_timestamp")
    receipt_age = evaluated - received
    reasons: list[str] = []
    source_age = None
    provenance_quality = ProvenanceQuality.COMPLETE
    freshness_basis = FreshnessBasis.SOURCE_TIMESTAMP

    if provenance.source_timestamp is None:
        provenance_quality = ProvenanceQuality.LIMITED
        freshness_basis = FreshnessBasis.RECEIPT_TIMESTAMP
        reasons.append("SOURCE_TIMESTAMP_UNAVAILABLE")
        age = receipt_age
    else:
        source = _utc(provenance.source_timestamp)
        if received < source:
            raise QualityEvaluationError("received_timestamp cannot precede source_timestamp")
        source_age = evaluated - source
        if source_age.total_seconds() < 0:
            raise QualityEvaluationError("source_timestamp is in the future")
        age = source_age

    if coverage.availability is CapabilityAvailability.UNAVAILABLE:
        reasons.append(coverage.limitation)
        return QualityAssessment(
            capability=capability,
            state=DataQualityState.UNAVAILABLE,
            coverage_availability=coverage.availability,
            coverage_limitation=coverage.limitation,
            provenance_quality=provenance_quality,
            freshness_basis=freshness_basis,
            source_age=source_age,
            receipt_age=receipt_age,
            evaluation_time=evaluated,
            policy_version=policy.policy_version,
            continuity=continuity,
            recovery=recovery,
            reasons=tuple(reasons),
            trusted_for_current_use=False,
        )

    try:
        threshold = policy.threshold_for(capability)
    except KeyError as exc:
        raise QualityEvaluationError(str(exc)) from exc

    if age <= threshold.live_max_age:
        state = DataQualityState.LIVE
    elif age <= threshold.delayed_max_age:
        state = DataQualityState.DELAYED
    else:
        state = DataQualityState.STALE

    if provenance_quality is ProvenanceQuality.LIMITED and state is DataQualityState.LIVE:
        state = DataQualityState.DELAYED
        reasons.append("SOURCE_FRESHNESS_NOT_PROVEN")
    if coverage.availability is CapabilityAvailability.LIMITED:
        reasons.append(coverage.limitation)
        state = _worst(state, DataQualityState.DELAYED)
    if continuity is ContinuityStatus.UNKNOWN:
        reasons.append("CONTINUITY_NOT_PROVEN")
        state = _worst(state, DataQualityState.DELAYED)
    elif continuity is ContinuityStatus.GAP_RISK:
        reasons.append("GAP_OR_CONTINUITY_RISK")
        state = _worst(state, DataQualityState.STALE)
    if recovery is RecoveryStatus.RECOVERING:
        reasons.append("RECOVERY_IN_PROGRESS_NO_REPLAY_CLAIM")
        state = _worst(state, DataQualityState.STALE)
    elif recovery is RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF:
        reasons.append("RECOVERY_OBSERVED_REPLAY_NOT_PROVEN")
        state = _worst(state, DataQualityState.DELAYED)

    trusted = (
        state is DataQualityState.LIVE
        and coverage.availability is CapabilityAvailability.SUPPORTED
        and provenance_quality is ProvenanceQuality.COMPLETE
        and continuity is ContinuityStatus.PROVEN
        and recovery is RecoveryStatus.NONE
    )
    return QualityAssessment(
        capability=capability,
        state=state,
        coverage_availability=coverage.availability,
        coverage_limitation=coverage.limitation or None,
        provenance_quality=provenance_quality,
        freshness_basis=freshness_basis,
        source_age=source_age,
        receipt_age=receipt_age,
        evaluation_time=evaluated,
        policy_version=policy.policy_version,
        continuity=continuity,
        recovery=recovery,
        reasons=tuple(reasons) or ("QUALITY_WITHIN_POLICY",),
        trusted_for_current_use=trusted,
    )
