from dataclasses import replace

from traid.harness.lifecycle import (
    COMPLETE,
    READY_FOR_HUMAN_REVIEW,
    LifecycleFacts,
    ReadinessFacts,
    evaluate_delivery_authority,
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
