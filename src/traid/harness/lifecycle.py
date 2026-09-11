"""Deterministic Card readiness, lifecycle, and delivery-authority checks."""

from __future__ import annotations

from dataclasses import dataclass, field


READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class ReadinessFacts:
    """Mandatory prerequisite availability known before implementation."""

    card_id: str
    docker_required: bool = False
    docker_available: bool = True
    python_available: bool = True
    test_tools_available: bool = True
    external_services_available: bool = True
    credentials_available: bool = True
    source_verification_available: bool = True
    datasets_available: bool = True


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


def evaluate_pre_card_readiness(facts: ReadinessFacts) -> GateResult:
    """Fail closed before implementation when a mandatory prerequisite is absent."""

    reasons: list[str] = []
    if facts.docker_required and not facts.docker_available:
        reasons.append("DOCKER_UNAVAILABLE")
    if not facts.python_available:
        reasons.append("PYTHON_UNAVAILABLE")
    if not facts.test_tools_available:
        reasons.append("TEST_TOOLS_UNAVAILABLE")
    if not facts.external_services_available:
        reasons.append("EXTERNAL_SERVICES_UNAVAILABLE")
    if not facts.credentials_available:
        reasons.append("CREDENTIAL_CONFIGURATION_UNAVAILABLE")
    if not facts.source_verification_available:
        reasons.append("SOURCE_VERIFICATION_UNAVAILABLE")
    if not facts.datasets_available:
        reasons.append("DATASET_OR_FIXTURE_UNAVAILABLE")
    return GateResult(not reasons, tuple(reasons))


@dataclass(frozen=True)
class LifecycleFacts:
    """Canonical state facts used for machine-checkable consistency validation."""

    card_id: str
    card_state: str
    active_card: str
    quality_gate: str
    delivery_approval: bool
    delivery_verified: bool
    project_control_state: str
    evidence_state: str
    expected_branch: str
    actual_branch: str
    next_card_requested: bool = False
    next_card_start_approval: bool = False
    pending_not_applicable: bool = False


def evaluate_delivery_authority(facts: LifecycleFacts) -> GateResult:
    """Separate implementation review readiness from consequential Git delivery."""

    reasons: list[str] = []
    if facts.card_state != READY_FOR_HUMAN_REVIEW:
        reasons.append("CARD_NOT_READY_FOR_HUMAN_REVIEW")
    if not facts.delivery_approval:
        reasons.append("DELIVERY_APPROVAL_MISSING")
    return GateResult(not reasons, tuple(reasons))


def evaluate_state_consistency(facts: LifecycleFacts) -> GateResult:
    """Detect contradictory Card, Evidence, approval, and branch state."""

    reasons: list[str] = []
    if facts.project_control_state != facts.evidence_state:
        reasons.append("PROJECT_CONTROL_EVIDENCE_STATE_MISMATCH")
    if facts.actual_branch != facts.expected_branch:
        reasons.append("GIT_BRANCH_STATE_MISMATCH")
    if facts.pending_not_applicable:
        reasons.append("PENDING_NOT_APPLICABLE_MISMATCH")
    if facts.next_card_requested and not facts.next_card_start_approval:
        reasons.append("NEXT_CARD_START_APPROVAL_MISSING")

    if facts.card_state == READY_FOR_HUMAN_REVIEW:
        if facts.active_card != facts.card_id:
            reasons.append("READY_CARD_NOT_ACTIVE")
        if facts.quality_gate != "PASS":
            reasons.append("READY_CARD_QUALITY_GATE_NOT_PASS")
        if facts.delivery_approval or facts.delivery_verified:
            reasons.append("READY_CARD_HAS_UNVERIFIED_DELIVERY_STATE")

    if facts.card_state == COMPLETE:
        if facts.active_card != "NONE":
            reasons.append("COMPLETE_CARD_STILL_ACTIVE")
        if not facts.delivery_approval:
            reasons.append("COMPLETE_WITHOUT_DELIVERY_APPROVAL")
        if not facts.delivery_verified:
            reasons.append("COMPLETE_WITHOUT_VERIFIED_DELIVERY")

    if facts.active_card == "NONE" and facts.card_state == READY_FOR_HUMAN_REVIEW:
        reasons.append("READY_CARD_ACTIVE_CARD_NONE")

    return GateResult(not reasons, tuple(dict.fromkeys(reasons)))
