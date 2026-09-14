import pytest

from traid.harness.alignment import CardRequest, evaluate_content_alignment


VALID = CardRequest(
    card_id="V1-C01",
    objective="Create a reproducible repository baseline and engineering harness",
    behaviors=("deterministic configuration", "health endpoint", "pytest discovery", "secret scan"),
    validation=("baseline tests", "CI skeleton"),
)


def test_correct_id_and_content_passes() -> None:
    result = evaluate_content_alignment(VALID)
    assert result.passed
    assert {"baseline", "harness"}.issubset(result.matched_domains)


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (CardRequest(**{**VALID.__dict__, "card_id": "V1-C02"}), "CARD_MISMATCH"),
        (CardRequest(**{**VALID.__dict__, "objective": "Create a reproducible repository baseline and canonical domain model"}), "FUTURE_CARD_LEAKAGE:V1-C02"),
        (CardRequest(**{**VALID.__dict__, "objective": "Create a canonical domain model and engineering harness"}), "FUTURE_CARD_LEAKAGE:V1-C02"),
        (CardRequest(**{**VALID.__dict__, "behaviors": ("market data ingestion",)}), "CARD_SCOPE_MISMATCH"),
        (CardRequest(**{**VALID.__dict__, "behaviors": ("adapter contract",)}), "FUTURE_CARD_LEAKAGE:V1-C03"),
        (CardRequest(**{**VALID.__dict__, "invented_material_requirement": True}), "INVENTED_REQUIREMENT"),
        (CardRequest(**{**VALID.__dict__, "dependencies_complete": False}), "CARD_DEPENDENCY_MISMATCH"),
        (CardRequest(**{**VALID.__dict__, "repository_state_conflict": True}), "PROJECT_STATE_CONFLICT"),
        (CardRequest(**{**VALID.__dict__, "next_card_requested": True}), "NEXT_CARD_AUTHORIZATION_BLOCKED"),
        (CardRequest(**{**VALID.__dict__, "next_card_requested": True, "current_card_complete": True}), "NEXT_CARD_AUTHORIZATION_BLOCKED"),
        (CardRequest(**{**VALID.__dict__, "asks_completion": True, "mandatory_validation_passed": False}), "CARD_QUALITY_GATE_BLOCKED"),
        (CardRequest(**{**VALID.__dict__, "behaviors": ("position sizing",)}), "FUTURE_CARD_LEAKAGE:V1-C17"),
    ],
)
def test_invalid_content_is_blocked(candidate: CardRequest, reason: str) -> None:
    result = evaluate_content_alignment(candidate)
    assert not result.passed
    assert reason in result.reason_codes
