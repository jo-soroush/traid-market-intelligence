from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from traid.domain import DataQualityState, OpenInterestSnapshot, SourceProvenance
from traid.exchange import Capability, CapabilityAvailability, CapabilityCoverage
from traid.quality import (
    ContinuityStatus,
    FreshnessBasis,
    ProvenanceQuality,
    QualityEvaluationError,
    QualityAssessment,
    RecoveryStatus,
    assess_quality,
    default_quality_policy,
)


NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
POLICY = default_quality_policy()


def provenance(*, source_age: timedelta | None = timedelta(seconds=1), receipt_age: timedelta = timedelta(seconds=0)) -> SourceProvenance:
    received = NOW - receipt_age
    source = None if source_age is None else NOW - source_age
    return SourceProvenance(
        source="fixture",
        source_type="test",
        source_timestamp=source,
        received_timestamp=received,
    )


def coverage(capability: Capability, availability: CapabilityAvailability = CapabilityAvailability.SUPPORTED) -> CapabilityCoverage:
    limitation = "fixture limitation" if availability is not CapabilityAvailability.SUPPORTED else ""
    return CapabilityCoverage(capability, availability, limitation)


def assess(
    *,
    capability: Capability = Capability.TRADES,
    source_age: timedelta | None = timedelta(seconds=1),
    receipt_age: timedelta = timedelta(seconds=0),
    availability: CapabilityAvailability = CapabilityAvailability.SUPPORTED,
    continuity: ContinuityStatus = ContinuityStatus.PROVEN,
    recovery: RecoveryStatus = RecoveryStatus.NONE,
    evaluation_time: datetime = NOW,
    canonical_valid: bool = True,
):
    return assess_quality(
        capability=capability,
        provenance=provenance(source_age=source_age, receipt_age=receipt_age),
        coverage=coverage(capability, availability),
        evaluation_time=evaluation_time,
        policy=POLICY,
        continuity=continuity,
        recovery=recovery,
        canonical_valid=canonical_valid,
    )


def direct_assessment(**overrides) -> QualityAssessment:
    values = {
        "capability": Capability.TRADES,
        "state": DataQualityState.LIVE,
        "coverage_availability": CapabilityAvailability.SUPPORTED,
        "coverage_limitation": None,
        "provenance_quality": ProvenanceQuality.COMPLETE,
        "freshness_basis": FreshnessBasis.SOURCE_TIMESTAMP,
        "source_age": timedelta(seconds=1),
        "receipt_age": timedelta(seconds=0),
        "evaluation_time": NOW,
        "policy_version": POLICY.policy_version,
        "continuity": ContinuityStatus.PROVEN,
        "recovery": RecoveryStatus.NONE,
        "reasons": ("QUALITY_WITHIN_POLICY",),
        "trusted_for_current_use": True,
    }
    values.update(overrides)
    return QualityAssessment(**values)


def test_live_and_exact_live_boundary_are_live_and_trusted():
    assert assess().state is DataQualityState.LIVE
    exact = assess(source_age=timedelta(seconds=5))
    assert exact.state is DataQualityState.LIVE
    assert exact.trusted_for_current_use is True


def test_delayed_and_exact_delayed_boundary_are_delayed():
    assert assess(source_age=timedelta(seconds=6)).state is DataQualityState.DELAYED
    exact = assess(source_age=timedelta(seconds=30))
    assert exact.state is DataQualityState.DELAYED
    assert exact.trusted_for_current_use is False


def test_clearly_stale_is_stale():
    assert assess(source_age=timedelta(seconds=31)).state is DataQualityState.STALE


@pytest.mark.parametrize("threshold", POLICY.thresholds)
def test_every_shipped_threshold_has_explicit_inclusive_boundaries(threshold):
    live = assess(capability=threshold.capability, source_age=threshold.live_max_age)
    delayed = assess(capability=threshold.capability, source_age=threshold.delayed_max_age)
    assert live.state is DataQualityState.LIVE
    assert delayed.state is DataQualityState.DELAYED


def test_evaluation_before_source_is_rejected_without_clamping():
    with pytest.raises(QualityEvaluationError, match="evaluation_time cannot precede"):
        assess(evaluation_time=NOW - timedelta(seconds=1))


def test_excessive_future_timestamp_is_rejected():
    invalid_future = SourceProvenance.model_construct(
        source="fixture",
        source_type="test",
        source_timestamp=NOW + timedelta(seconds=1),
        received_timestamp=NOW,
    )
    with pytest.raises(QualityEvaluationError, match="received_timestamp cannot precede"):
        assess_quality(
            capability=Capability.TRADES,
            provenance=invalid_future,
            coverage=coverage(Capability.TRADES),
            evaluation_time=NOW,
            policy=POLICY,
            continuity=ContinuityStatus.PROVEN,
            recovery=RecoveryStatus.NONE,
            canonical_valid=True,
        )


def test_same_input_time_and_policy_is_deterministic():
    assert assess().model_dump() == assess().model_dump()


def test_source_and_receipt_ages_are_independent():
    result = assess(source_age=timedelta(seconds=20), receipt_age=timedelta(seconds=2))
    assert result.source_age == timedelta(seconds=20)
    assert result.receipt_age == timedelta(seconds=2)
    assert result.freshness_basis is FreshnessBasis.SOURCE_TIMESTAMP


def test_missing_source_time_uses_receipt_age_without_fabricating_source_age():
    result = assess(source_age=None, receipt_age=timedelta(seconds=1))
    assert result.source_age is None
    assert result.receipt_age == timedelta(seconds=1)
    assert result.freshness_basis is FreshnessBasis.RECEIPT_TIMESTAMP
    assert result.provenance_quality is ProvenanceQuality.LIMITED
    assert result.state is DataQualityState.DELAYED
    assert result.trusted_for_current_use is False


def test_invalid_public_quality_boundary_fails_closed():
    with pytest.raises(QualityEvaluationError, match="SourceProvenance"):
        assess_quality(
            capability=Capability.TRADES,
            provenance={"source": "fixture"},
            coverage=coverage(Capability.TRADES),
            evaluation_time=NOW,
            policy=POLICY,
            continuity=ContinuityStatus.PROVEN,
            recovery=RecoveryStatus.NONE,
            canonical_valid=True,
        )
    with pytest.raises(QualityEvaluationError, match="malformed"):
        assess(canonical_valid=False)


def test_supported_and_limited_coverage_are_distinct():
    assert assess().coverage_availability is CapabilityAvailability.SUPPORTED
    limited = assess(availability=CapabilityAvailability.LIMITED)
    assert limited.coverage_availability is CapabilityAvailability.LIMITED
    assert limited.state is DataQualityState.DELAYED
    assert limited.coverage_limitation == "fixture limitation"


def test_unavailable_capability_is_unavailable_not_empty_or_live():
    result = assess(capability=Capability.OPEN_INTEREST, availability=CapabilityAvailability.UNAVAILABLE)
    assert result.state is DataQualityState.UNAVAILABLE
    assert result.trusted_for_current_use is False
    assert result.coverage_limitation == "fixture limitation"


def test_unknown_capability_and_unsupported_threshold_fail_closed():
    with pytest.raises(QualityEvaluationError, match="unknown capability"):
        assess_quality(
            capability="trades",
            provenance=provenance(),
            coverage=coverage(Capability.TRADES),
            evaluation_time=NOW,
            policy=POLICY,
            continuity=ContinuityStatus.PROVEN,
            recovery=RecoveryStatus.NONE,
            canonical_valid=True,
        )
    with pytest.raises(QualityEvaluationError, match="no freshness threshold"):
        assess(capability=Capability.OPEN_INTEREST)


def test_gap_and_unknown_continuity_are_visible_and_not_complete():
    unknown = assess(continuity=ContinuityStatus.UNKNOWN)
    assert unknown.state is DataQualityState.DELAYED
    assert "CONTINUITY_NOT_PROVEN" in unknown.reasons
    gap = assess(continuity=ContinuityStatus.GAP_RISK)
    assert gap.state is DataQualityState.STALE
    assert "GAP_OR_CONTINUITY_RISK" in gap.reasons


def test_recovery_labels_do_not_claim_replay():
    recovering = assess(recovery=RecoveryStatus.RECOVERING)
    assert recovering.state is DataQualityState.STALE
    assert "RECOVERY_IN_PROGRESS_NO_REPLAY_CLAIM" in recovering.reasons
    recovered = assess(recovery=RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF)
    assert recovered.state is DataQualityState.DELAYED
    assert "RECOVERY_OBSERVED_REPLAY_NOT_PROVEN" in recovered.reasons


def test_stale_last_observation_remains_stale_without_new_evidence():
    result = assess(source_age=timedelta(seconds=31))
    later = assess(source_age=timedelta(seconds=61))
    assert result.state is DataQualityState.STALE
    assert later.state is DataQualityState.STALE


def test_policy_is_versioned_serializable_and_has_no_oi_threshold():
    assert POLICY.policy_version == "c05-policy-1"
    assert "open_interest" not in POLICY.model_dump_json()
    assert POLICY.model_dump()["thresholds"][0]["capability"] == Capability.TRADES


def test_oi_quality_cannot_create_a_canonical_snapshot_or_promote_unverified_data():
    result = assess(capability=Capability.OPEN_INTEREST, availability=CapabilityAvailability.UNAVAILABLE)
    assert result.state is DataQualityState.UNAVAILABLE
    assert not isinstance(result, OpenInterestSnapshot)
    assert result.coverage_availability is CapabilityAvailability.UNAVAILABLE


@pytest.mark.parametrize(
    "overrides",
    [
        {"state": DataQualityState.STALE},
        {"state": DataQualityState.DELAYED},
        {"state": DataQualityState.UNAVAILABLE},
        {"provenance_quality": ProvenanceQuality.LIMITED},
        {"coverage_availability": CapabilityAvailability.LIMITED, "coverage_limitation": "partial"},
        {"coverage_availability": CapabilityAvailability.UNAVAILABLE, "coverage_limitation": "offline"},
        {"continuity": ContinuityStatus.UNKNOWN},
        {"continuity": ContinuityStatus.GAP_RISK},
        {"recovery": RecoveryStatus.RECOVERING},
        {"recovery": RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF},
        {"freshness_basis": FreshnessBasis.RECEIPT_TIMESTAMP, "source_age": None},
        {"reasons": ("CONTINUITY_NOT_PROVEN",)},
    ],
)
def test_direct_trusted_assessment_rejects_unsafe_combinations(overrides):
    with pytest.raises(ValueError, match="cannot be trusted|trusted_for_current_use invariants failed"):
        direct_assessment(**overrides)


def test_direct_clean_trusted_assessment_is_supported():
    result = direct_assessment()
    assert result.trusted_for_current_use is True
    assert result.evaluation_time == NOW


@pytest.mark.parametrize(
    "overrides",
    [
        {"state": DataQualityState.STALE},
        {"provenance_quality": ProvenanceQuality.LIMITED},
        {"state": DataQualityState.UNAVAILABLE, "coverage_availability": CapabilityAvailability.UNAVAILABLE, "coverage_limitation": "offline"},
        {"continuity": ContinuityStatus.GAP_RISK},
    ],
)
def test_direct_degraded_assessment_with_false_trust_remains_representable(overrides):
    result = direct_assessment(trusted_for_current_use=False, **overrides)
    assert result.trusted_for_current_use is False


def test_evaluation_time_requires_timezone_awareness_and_normalizes_utc():
    with pytest.raises(ValueError, match="timezone-aware"):
        direct_assessment(evaluation_time=datetime(2026, 1, 1, 12, 0))
    aware = direct_assessment(evaluation_time=datetime(2026, 1, 1, 14, 0, tzinfo=timezone(timedelta(hours=2))))
    assert aware.evaluation_time == NOW


def test_model_validate_and_json_paths_cannot_bypass_trust_invariants():
    payload = direct_assessment().model_dump(mode="json")
    payload["state"] = DataQualityState.STALE.value
    with pytest.raises(ValueError, match="trusted_for_current_use invariants failed"):
        QualityAssessment.model_validate(payload)
    with pytest.raises(ValueError, match="trusted_for_current_use invariants failed"):
        QualityAssessment.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"source_age": timedelta(seconds=31)},
        {"source_age": None},
        {"continuity": ContinuityStatus.GAP_RISK},
        {"recovery": RecoveryStatus.RECOVERING},
        {"availability": CapabilityAvailability.UNAVAILABLE},
    ],
)
def test_evaluator_outputs_always_satisfy_model_trust_invariants(kwargs):
    result = assess(**kwargs)
    assert result.trusted_for_current_use is False
