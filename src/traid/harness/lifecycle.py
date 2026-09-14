"""Deterministic Card readiness, lifecycle, and delivery-authority checks."""

from __future__ import annotations

from dataclasses import dataclass, field


READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
COMPLETE = "COMPLETE"
NOT_STARTED = "NOT_STARTED"
IN_PROGRESS = "IN_PROGRESS"
BLOCKED = "BLOCKED"
DEFERRED = "DEFERRED"
CARD_STATES = frozenset(
    {NOT_STARTED, IN_PROGRESS, BLOCKED, READY_FOR_HUMAN_REVIEW, COMPLETE, DEFERRED}
)


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
    repository_available: bool = True
    branch_condition_met: bool = True
    working_tree_condition_met: bool = True
    project_environment_available: bool = True
    dependencies_complete: bool = True
    required_config_present: bool = True


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


def evaluate_pre_card_readiness(facts: ReadinessFacts) -> GateResult:
    """Fail closed before implementation when a mandatory prerequisite is absent."""

    reasons: list[str] = []
    if not facts.repository_available:
        reasons.append("REPOSITORY_UNAVAILABLE")
    if not facts.branch_condition_met:
        reasons.append("BRANCH_CONDITION_UNMET")
    if not facts.working_tree_condition_met:
        reasons.append("WORKING_TREE_CONDITION_UNMET")
    if not facts.project_environment_available:
        reasons.append("PROJECT_ENVIRONMENT_UNAVAILABLE")
    if not facts.dependencies_complete:
        reasons.append("CARD_DEPENDENCY_INCOMPLETE")
    if not facts.required_config_present:
        reasons.append("REQUIRED_CONFIGURATION_MISSING")
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
    expected_head: str = ""
    actual_head: str = ""
    head_checkpoint_verified: bool | None = None
    test_state_verified: bool = True
    quality_gate_state: str = "PASS"
    evidence_status: str = "COMPLETE"
    learning_status: str = "COMPLETE"
    safe_resume_valid: bool = True
    delivery_recorded: bool = True
    evidence_delivery_recorded: bool = True
    learning_record_complete: bool = True
    c02_not_started: bool = True
    c02_authorized: bool = False
    stale_completion_rationale: bool = False
    expected_working_tree_clean: bool = True
    actual_working_tree_clean: bool = True
    start_authorized: bool = False
    mandatory_failure: bool = False
    next_card_requested: bool = False
    next_card_start_approval: bool = False
    pending_not_applicable: bool = False


def evaluate_lifecycle_transition(
    current_state: str,
    next_state: str,
    facts: LifecycleFacts,
) -> GateResult:
    """Enforce the small set of consequential Card state transitions."""

    reasons: list[str] = []
    if current_state not in CARD_STATES:
        reasons.append("INVALID_CURRENT_CARD_STATE")
    if next_state not in CARD_STATES:
        reasons.append("INVALID_NEXT_CARD_STATE")
    if current_state == NOT_STARTED and next_state == IN_PROGRESS and not facts.start_authorized:
        reasons.append("START_APPROVAL_MISSING")
    if current_state == IN_PROGRESS and next_state == BLOCKED and not facts.mandatory_failure:
        reasons.append("BLOCKED_WITHOUT_MANDATORY_FAILURE")
    if current_state == IN_PROGRESS and next_state == READY_FOR_HUMAN_REVIEW:
        if facts.quality_gate != "PASS":
            reasons.append("READY_WITHOUT_QUALITY_GATE")
        if facts.evidence_status != COMPLETE or facts.learning_status != COMPLETE:
            reasons.append("READY_WITHOUT_EVIDENCE_OR_LEARNING")
    if current_state == READY_FOR_HUMAN_REVIEW and next_state == COMPLETE:
        if not facts.delivery_approval:
            reasons.append("DELIVERY_APPROVAL_MISSING")
        if not facts.delivery_verified:
            reasons.append("DELIVERY_NOT_VERIFIED")
    if current_state == BLOCKED and next_state != BLOCKED:
        reasons.append("BLOCKED_STATE_CANNOT_PROGRESS_SILENTLY")
    if current_state == DEFERRED and next_state == COMPLETE:
        reasons.append("DEFERRED_CANNOT_COMPLETE")
    if next_state == COMPLETE and facts.active_card != "NONE":
        reasons.append("COMPLETE_CARD_STILL_ACTIVE")
    return GateResult(not reasons, tuple(dict.fromkeys(reasons)))


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
    if facts.card_state not in CARD_STATES:
        reasons.append("INVALID_CARD_STATE")
    if facts.project_control_state != facts.evidence_state:
        reasons.append("PROJECT_CONTROL_EVIDENCE_STATE_MISMATCH")
    if facts.actual_branch != facts.expected_branch:
        reasons.append("GIT_BRANCH_STATE_MISMATCH")
    if facts.expected_head and facts.actual_head != facts.expected_head and facts.head_checkpoint_verified is not True:
        reasons.append("GIT_HEAD_STATE_MISMATCH")
    if facts.expected_working_tree_clean != facts.actual_working_tree_clean:
        reasons.append("WORKING_TREE_STATE_MISMATCH")
    if facts.pending_not_applicable:
        reasons.append("PENDING_NOT_APPLICABLE_MISMATCH")
    if facts.next_card_requested and not facts.next_card_start_approval:
        reasons.append("NEXT_CARD_START_APPROVAL_MISSING")
    if not facts.c02_not_started:
        reasons.append("NEXT_CARD_ALREADY_STARTED")
    if facts.c02_authorized:
        reasons.append("NEXT_CARD_AUTHORIZATION_PRESENT")
    if facts.stale_completion_rationale:
        reasons.append("STALE_V1_COMPLETION_RATIONALE")

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
        if facts.quality_gate_state != "PASS" or facts.quality_gate != "PASS":
            reasons.append("COMPLETE_WITHOUT_QUALITY_GATE")
        if not facts.test_state_verified:
            reasons.append("COMPLETE_WITHOUT_VERIFIED_TEST_STATE")
        if facts.evidence_status != COMPLETE or not facts.evidence_delivery_recorded:
            reasons.append("COMPLETE_WITHOUT_CURRENT_EVIDENCE")
        if facts.learning_status != COMPLETE or not facts.learning_record_complete:
            reasons.append("COMPLETE_WITHOUT_COMPLETE_LEARNING_RECORD")
        if not facts.delivery_recorded:
            reasons.append("COMPLETE_WITHOUT_DELIVERY_RECORD")
        if not facts.safe_resume_valid:
            reasons.append("INVALID_SAFE_RESUME_STATE")

    if facts.active_card == "NONE" and facts.card_state == READY_FOR_HUMAN_REVIEW:
        reasons.append("READY_CARD_ACTIVE_CARD_NONE")

    return GateResult(not reasons, tuple(dict.fromkeys(reasons)))
