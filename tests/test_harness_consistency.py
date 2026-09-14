from __future__ import annotations

import os
import subprocess
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "harness_consistency_check.py"
CONTROL = ROOT / "PROJECT_CONTROL.md"
EVIDENCE = ROOT / "TRAID_CARD_EVIDENCE_MAP.md"
SPEC = importlib.util.spec_from_file_location("harness_consistency_check", CHECKER)
assert SPEC and SPEC.loader
consistency = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = consistency
SPEC.loader.exec_module(consistency)


def c01_evidence_section() -> str:
    text = EVIDENCE.read_text()
    start = text.index("## V1-C01 —")
    end = text.index("\n## V1-C02 —", start)
    return text[start:end]


def test_all_30_learning_fields_are_required_and_nonempty() -> None:
    section = c01_evidence_section()
    assert consistency.learning_record_issues(section) == ()

    missing = section.replace("What this enables next:", "Removed field:", 1)
    assert any("What this enables next" in issue for issue in consistency.learning_record_issues(missing))

    empty = section.replace(
        "What this enables next: A separately authorized C02 after this corrective maintenance is delivered and verified; this record does not authorize C02.",
        "What this enables next:",
        1,
    )
    assert "LEARNING_FIELD_EMPTY:What this enables next" in consistency.learning_record_issues(empty)

    not_applicable = section.replace(
        "AI / Data / Financial concept: NOT_APPLICABLE — C01 adds no AI provider, market-data path, Strategy, Risk Gate, or financial calculation.",
        "AI / Data / Financial concept: NOT_APPLICABLE",
    )
    assert consistency.learning_record_issues(not_applicable) == ()


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _fixture(tmp_path: Path) -> tuple[Path, str, str]:
    subprocess.run(["git", "init", "-q", "-b", "test-branch"], cwd=tmp_path, check=True)
    evidence = """## V1-C01 — Repository Baseline & Engineering Harness
**Status:** READY_FOR_HUMAN_REVIEW
Status: PASS
**Delivery Approval:** NOT_GRANTED
Post-merge verification: NOT_RUN
### Learning Record
""" + "\n".join(f"{field}: verified" for field in consistency.C01_LEARNING_RECORD_FIELDS) + """
### Exit Gate Proof
Verified
## V1-C02 — Canonical Domain Models
"""
    rows = "\n".join(
        f"| V1-C{i:02d} | {('Repository Baseline & Engineering Harness' if i == 1 else 'Canonical Domain Models' if i == 2 else f'Card {i:02d}')} | {'READY_FOR_HUMAN_REVIEW' if i == 1 else 'NOT_STARTED'} | {'YES' if i == 1 else 'NO'} | NOT_RUN | PENDING |"
        for i in range(1, 28)
    )
    control = """Active Card: V1-C01 — Repository Baseline & Engineering Harness
Active Card State: READY_FOR_HUMAN_REVIEW
Next Roadmap Card: V1-C02 — Canonical Domain Models
Next Card Authorized: NO
## 6. Active Card Record
Human Start Approval: GRANTED — V1-C01
Human Delivery Approval: NOT_GRANTED
Delivery Verified: NO
## 7. Authorization Ledger
V1-C01: READY_FOR_HUMAN_REVIEW
Git Branch: test-branch
Git HEAD: PLACEHOLDER
Working Tree: DIRTY_ALLOWED
TraID repository test state: VERIFIED
CARD_QUALITY_GATE: PASS
Learning Record Status: COMPLETE
V1-C01 Authorization: START_GRANTED; DELIVERY_NOT_GRANTED
""" + rows
    (tmp_path / "PROJECT_CONTROL.md").write_text(control)
    (tmp_path / "TRAID_CARD_EVIDENCE_MAP.md").write_text(evidence)
    subprocess.run(["git", "add", "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"], cwd=tmp_path, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True, env=env)
    head = _git(tmp_path, "rev-parse", "--short", "HEAD")
    (tmp_path / "PROJECT_CONTROL.md").write_text(control.replace("PLACEHOLDER", head))
    return tmp_path, control.replace("PLACEHOLDER", head), evidence


def _run_checker(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([str(ROOT / ".venv" / "bin" / "python"), str(CHECKER)], cwd=tmp_path, text=True, capture_output=True, env=env)


def test_actual_checker_normalizes_titles_and_rejects_wrong_card(tmp_path: Path) -> None:
    tmp_path, control, _ = _fixture(tmp_path)
    assert _run_checker(tmp_path).returncode == 0

    wrong = control.replace(
        "Active Card: V1-C01 — Repository Baseline & Engineering Harness",
        "Active Card: V1-C02 — Canonical Domain Models",
    )
    (tmp_path / "PROJECT_CONTROL.md").write_text(wrong)
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "ACTIVE_CARD_STATE_INVALID" in result.stdout


def test_actual_checker_detects_stale_recorded_head(tmp_path: Path) -> None:
    tmp_path, control, _ = _fixture(tmp_path)
    stale = control.replace("Git HEAD:", "Git HEAD: 0000000 #")
    (tmp_path / "PROJECT_CONTROL.md").write_text(stale)
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "GIT_HEAD_STATE_MISMATCH" in result.stdout


CARD_TITLES = {f"V1-C{i:02d}": f"Card {i:02d}" for i in range(1, 28)}


def _state_fixture(active: str, state: str, *, start_approved: bool = True, next_card: str | None = None) -> str:
    rows = []
    for card_id, title in CARD_TITLES.items():
        row_state = state if card_id == active else ("COMPLETE" if active == "NONE" and card_id == "V1-C01" else "NOT_STARTED")
        approved = "YES" if card_id == active and start_approved else "NO"
        rows.append(f"| {card_id} | {title} | {row_state} | {approved} | NOT_RUN | PENDING |")
    if next_card is None:
        number = int(active[-2:]) + 1 if active != "NONE" else 2
        next_card = f"V1-C{number:02d}" if number <= 27 else "NONE"
    active_title = "NONE" if active == "NONE" else f"{active} — {CARD_TITLES[active]}"
    return "\n".join([
        f"Active Card: {active_title}",
        *( [f"Active Card State: {state}"] if active != "NONE" else [] ),
        f"Next Roadmap Card: {next_card} — {CARD_TITLES.get(next_card, '')}" if next_card != "NONE" else "Next Roadmap Card: NONE",
        "## 6. Active Card Record",
        f"Human Start Approval: {'GRANTED' if start_approved else 'NOT_GRANTED'}",
        "Human Delivery Approval: NOT_GRANTED",
        "Delivery Verified: NO",
        "## 7. Authorization Ledger",
        *( ["V1-C01 Authorization: START_GRANTED; DELIVERY_COMPLETED"] if active == "NONE" else [] ),
        "## 30. V1 Card Status Table",
        *rows,
    ])


@pytest.mark.parametrize("card_id", [f"V1-C{i:02d}" for i in range(1, 28)])
def test_generic_resolver_recognizes_all_cards_and_order(card_id: str) -> None:
    result = consistency.resolve_card_state(_state_fixture(card_id, "IN_PROGRESS"))
    assert not result.errors
    assert result.active_card == card_id
    index = int(card_id[-2:])
    expected_next = f"V1-C{index + 1:02d}" if index < 27 else "NONE"
    assert result.derived_next_card == expected_next


def test_active_c02_ready_normalizes_titled_identity() -> None:
    result = consistency.resolve_card_state(_state_fixture("V1-C02", "READY_FOR_HUMAN_REVIEW"))
    assert not result.errors
    assert result.active_card == "V1-C02"


@pytest.mark.parametrize(
    ("control", "reason"),
    [
        (_state_fixture("V1-C02", "NOT_STARTED"), "ACTIVE_CARD_STATE_INVALID"),
        (_state_fixture("V1-C02", "COMPLETE"), "ACTIVE_CARD_STATE_INVALID"),
        (_state_fixture("V1-C03", "IN_PROGRESS", start_approved=False), "ACTIVE_CARD_START_APPROVAL_MISSING"),
        (_state_fixture("V1-C10", "IN_PROGRESS") + "\nActive Card: V1-C11 — Card 11", "ACTIVE_CARD_DECLARATIONS_CONFLICT"),
        (_state_fixture("V1-C09", "IN_PROGRESS", next_card="V1-C09"), "NEXT_CARD_EQUALS_ACTIVE_CARD"),
        (_state_fixture("V1-C02", "READY_FOR_HUMAN_REVIEW", next_card="V1-C04"), "NEXT_ROADMAP_CARD_MISMATCH"),
        (_state_fixture("V1-C02", "READY_FOR_HUMAN_REVIEW").replace("V1-C02 — Card 02", "V1-C02 — Wrong Title"), "CARD_TITLE_MISMATCH:V1-C02"),
    ],
)
def test_generic_resolver_blocks_false_green_state(control: str, reason: str) -> None:
    result = consistency.resolve_card_state(control)
    assert reason in result.errors


def test_no_active_card_derives_first_incomplete_card() -> None:
    result = consistency.resolve_card_state(_state_fixture("NONE", "NOT_STARTED"))
    assert not result.errors
    assert result.active_card == "NONE"
    assert result.derived_next_card == "V1-C02"


def test_complete_without_delivery_proof_is_blocked() -> None:
    control = _state_fixture("NONE", "NOT_STARTED").replace(
        "V1-C01 Authorization: START_GRANTED; DELIVERY_COMPLETED\n", ""
    )
    result = consistency.resolve_card_state(control)
    assert "COMPLETE_WITHOUT_DELIVERY_PROOF" in result.errors
    assert "COMPLETE_WITHOUT_DELIVERY_VERIFICATION" in result.errors


def test_future_card_authorization_is_blocked() -> None:
    control = _state_fixture("V1-C02", "READY_FOR_HUMAN_REVIEW").replace(
        "| V1-C03 | Card 03 | NOT_STARTED | NO |", "| V1-C03 | Card 03 | NOT_STARTED | YES |"
    )
    result = consistency.resolve_card_state(control)
    assert "NEXT_CARD_AUTHORIZATION_PRESENT" in result.errors


def test_missing_active_card_field_fails_closed() -> None:
    result = consistency.resolve_card_state(_state_fixture("V1-C02", "IN_PROGRESS").replace("Active Card:", "Removed Active Card:", 1))
    assert "ACTIVE_CARD_MISSING" in result.errors


def test_generic_lifecycle_code_has_no_card_specific_bypass() -> None:
    source = CHECKER.read_text()
    assert "c02_not_started" not in source
    assert "c02_authorized" not in source
    assert not any(re.search(r"active.*V1-C\d{2}|V1-C\d{2}.*active", line, re.I) for line in source.splitlines())
