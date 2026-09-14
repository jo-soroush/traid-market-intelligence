from dataclasses import replace

from traid.harness.lifecycle import (
    BLOCKED,
    COMPLETE,
    DEFERRED,
    IN_PROGRESS,
    NOT_STARTED,
    READY_FOR_HUMAN_REVIEW,
    LifecycleFacts,
    ReadinessFacts,
    evaluate_delivery_authority,
    evaluate_lifecycle_transition,
    evaluate_pre_card_readiness,
    evaluate_state_consistency,
)


def ready_facts() -> LifecycleFacts:
    return LifecycleFacts(
        card_id="V1-C01",
        card_state=READY_FOR_HUMAN_REVIEW,
        active_card="V1-C01",
        quality_gate="PASS",
        delivery_approval=False,
        delivery_verified=False,
        project_control_state=READY_FOR_HUMAN_REVIEW,
        evidence_state=READY_FOR_HUMAN_REVIEW,
        expected_branch="card/v1-c01-repository-baseline",
        actual_branch="card/v1-c01-repository-baseline",
    )


def complete_facts() -> LifecycleFacts:
    return replace(
        ready_facts(),
        card_state=COMPLETE,
        active_card="NONE",
        delivery_approval=True,
        delivery_verified=True,
        project_control_state=COMPLETE,
        evidence_state=COMPLETE,
    )


def test_missing_docker_blocks_pre_card_readiness() -> None:
    result = evaluate_pre_card_readiness(ReadinessFacts("V1-C02", docker_required=True, docker_available=False))
    assert not result.passed
    assert "DOCKER_UNAVAILABLE" in result.reason_codes


def test_unavailable_repository_blocks_pre_card_readiness() -> None:
    result = evaluate_pre_card_readiness(ReadinessFacts("V1-C02", repository_available=False))
    assert not result.passed
    assert "REPOSITORY_UNAVAILABLE" in result.reason_codes


def test_incomplete_dependency_blocks_pre_card_readiness() -> None:
    result = evaluate_pre_card_readiness(ReadinessFacts("V1-C02", dependencies_complete=False))
    assert not result.passed
    assert "CARD_DEPENDENCY_INCOMPLETE" in result.reason_codes


def test_phase_one_is_ready_but_has_no_delivery_authority() -> None:
    facts = ready_facts()
    assert evaluate_state_consistency(facts).passed
    result = evaluate_delivery_authority(facts)
    assert not result.passed
    assert "DELIVERY_APPROVAL_MISSING" in result.reason_codes


def test_explicit_delivery_approval_makes_delivery_eligible() -> None:
    result = evaluate_delivery_authority(replace(ready_facts(), delivery_approval=True))
    assert result.passed


def test_quality_gate_pass_does_not_imply_complete() -> None:
    facts = ready_facts()
    assert facts.quality_gate == "PASS"
    assert facts.card_state == READY_FOR_HUMAN_REVIEW


def test_complete_without_verified_delivery_is_blocked() -> None:
    facts = replace(complete_facts(), delivery_verified=False)
    result = evaluate_state_consistency(facts)
    assert not result.passed
    assert "COMPLETE_WITHOUT_VERIFIED_DELIVERY" in result.reason_codes


def test_complete_after_approved_verified_delivery_clears_active_card() -> None:
    assert evaluate_state_consistency(complete_facts()).passed


def test_next_card_without_separate_start_approval_is_blocked() -> None:
    result = evaluate_state_consistency(replace(ready_facts(), next_card_requested=True))
    assert not result.passed
    assert "NEXT_CARD_START_APPROVAL_MISSING" in result.reason_codes


def test_project_control_and_evidence_disagreement_is_blocked() -> None:
    result = evaluate_state_consistency(replace(ready_facts(), evidence_state=COMPLETE))
    assert not result.passed
    assert "PROJECT_CONTROL_EVIDENCE_STATE_MISMATCH" in result.reason_codes


def test_pending_not_applicable_is_blocked() -> None:
    result = evaluate_state_consistency(replace(ready_facts(), pending_not_applicable=True))
    assert not result.passed
    assert "PENDING_NOT_APPLICABLE_MISMATCH" in result.reason_codes


def test_branch_state_disagreement_is_blocked() -> None:
    result = evaluate_state_consistency(replace(ready_facts(), actual_branch="main"))
    assert not result.passed
    assert "GIT_BRANCH_STATE_MISMATCH" in result.reason_codes


def test_head_state_disagreement_is_blocked() -> None:
    facts = replace(ready_facts(), expected_head="abc1234", actual_head="def5678")
    result = evaluate_state_consistency(facts)
    assert not result.passed
    assert "GIT_HEAD_STATE_MISMATCH" in result.reason_codes


def test_stale_completion_rationale_is_blocked() -> None:
    result = evaluate_state_consistency(replace(complete_facts(), stale_completion_rationale=True))
    assert not result.passed
    assert "STALE_V1_COMPLETION_RATIONALE" in result.reason_codes


def test_complete_without_current_learning_record_is_blocked() -> None:
    result = evaluate_state_consistency(replace(complete_facts(), learning_record_complete=False))
    assert not result.passed
    assert "COMPLETE_WITHOUT_COMPLETE_LEARNING_RECORD" in result.reason_codes


def test_complete_with_dirty_tree_when_clean_expected_is_blocked() -> None:
    result = evaluate_state_consistency(
        replace(complete_facts(), expected_working_tree_clean=True, actual_working_tree_clean=False)
    )
    assert not result.passed
    assert "WORKING_TREE_STATE_MISMATCH" in result.reason_codes


def test_not_started_requires_explicit_start_authorization() -> None:
    facts = replace(ready_facts(), start_authorized=False)
    result = evaluate_lifecycle_transition(NOT_STARTED, IN_PROGRESS, facts)
    assert not result.passed
    assert "START_APPROVAL_MISSING" in result.reason_codes


def test_in_progress_can_block_only_on_mandatory_failure() -> None:
    facts = replace(ready_facts(), mandatory_failure=True)
    assert evaluate_lifecycle_transition(IN_PROGRESS, BLOCKED, facts).passed


def test_in_progress_requires_quality_and_evidence_before_review() -> None:
    facts = replace(ready_facts(), quality_gate="BLOCKED", evidence_status=BLOCKED)
    result = evaluate_lifecycle_transition(IN_PROGRESS, READY_FOR_HUMAN_REVIEW, facts)
    assert not result.passed
    assert "READY_WITHOUT_QUALITY_GATE" in result.reason_codes


def test_ready_requires_approved_verified_delivery_before_complete() -> None:
    result = evaluate_lifecycle_transition(READY_FOR_HUMAN_REVIEW, COMPLETE, ready_facts())
    assert not result.passed
    assert "DELIVERY_APPROVAL_MISSING" in result.reason_codes
    assert "DELIVERY_NOT_VERIFIED" in result.reason_codes


def test_blocked_and_deferred_cannot_silently_complete() -> None:
    blocked = evaluate_lifecycle_transition(BLOCKED, COMPLETE, complete_facts())
    deferred = evaluate_lifecycle_transition(DEFERRED, COMPLETE, complete_facts())
    assert not blocked.passed
    assert "BLOCKED_STATE_CANNOT_PROGRESS_SILENTLY" in blocked.reason_codes
    assert not deferred.passed
    assert "DEFERRED_CANNOT_COMPLETE" in deferred.reason_codes
