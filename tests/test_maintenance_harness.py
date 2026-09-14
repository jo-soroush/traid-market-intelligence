from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "harness_consistency_check.py"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _run_checker(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, str(CHECKER)], cwd=cwd, text=True, capture_output=True, env=env)


def _maintenance_fixture(tmp_path: Path, branch: str, *, dirty_path: str | None = None) -> Path:
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=tmp_path, check=True)
    control = (ROOT / "PROJECT_CONTROL.md").read_text()
    evidence = (ROOT / "TRAID_CARD_EVIDENCE_MAP.md").read_text()
    control = re.sub(r"^Git Branch: .+$", f"Git Branch: {branch}", control, flags=re.MULTILINE)
    control = re.sub(r"^Branch: maintenance/ci-python-portability$", f"Branch: {branch}", control, flags=re.MULTILINE)
    working_tree = "DIRTY_ALLOWED" if dirty_path else "CLEAN"
    control = re.sub(r"^Working Tree: .+$", f"Working Tree: {working_tree}", control, count=1, flags=re.MULTILINE)
    (tmp_path / "PROJECT_CONTROL.md").write_text(control)
    (tmp_path / "TRAID_CARD_EVIDENCE_MAP.md").write_text(evidence)
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    subprocess.run(["git", "add", "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True, env=env)
    base = _git(tmp_path, "rev-parse", "--short", "HEAD")
    control = re.sub(r"^Git HEAD: .+$", f"Git HEAD: {base}", control, count=1, flags=re.MULTILINE)
    control = re.sub(r"^Base Commit: .+$", f"Base Commit: {base} — verified fixture base", control, count=1, flags=re.MULTILINE)
    (tmp_path / "PROJECT_CONTROL.md").write_text(control)
    if dirty_path:
        target = tmp_path / dirty_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("authorized maintenance fixture\n")
    else:
        subprocess.run(["git", "add", "PROJECT_CONTROL.md"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "reconciled fixture"], cwd=tmp_path, check=True, env=env)
    return tmp_path


def test_authorized_maintenance_branch_with_in_scope_dirty_file_passes(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "maintenance/future-repository-fix", dirty_path="tests/test_harness_consistency.py")
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


def test_authorized_maintenance_branch_with_clean_state_passes(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "maintenance/clean-fix")
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


def test_authorized_hotfix_branch_passes(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "hotfix/recovery-fix")
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("branch", "mutator", "reason"),
    [
        ("maintenance/unknown-fix", lambda text: text.replace("### Current Maintenance Record", "### Removed Maintenance Record"), "MAINTENANCE_RECORD_MISSING"),
        ("maintenance/branch-mismatch", lambda text: re.sub(r"^Branch: maintenance/branch-mismatch$", "Branch: maintenance/other-fix", text, flags=re.MULTILINE), "MAINTENANCE_BRANCH_AUTHORIZATION_MISMATCH"),
        ("maintenance/wrong-base", lambda text: re.sub(r"^Base Commit: .+$", "Base Commit: 0000000", text, count=1, flags=re.MULTILINE), "MAINTENANCE_BASE_NOT_ANCESTOR"),
    ],
)
def test_invalid_maintenance_record_blocks(tmp_path: Path, branch: str, mutator, reason: str) -> None:
    fixture = _maintenance_fixture(tmp_path, branch)
    control_path = fixture / "PROJECT_CONTROL.md"
    control_path.write_text(mutator(control_path.read_text()))
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert reason in result.stdout


def test_out_of_scope_dirty_file_blocks(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "maintenance/out-of-scope", dirty_path="src/traid/unapproved.py")
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "MAINTENANCE_OUT_OF_SCOPE:src/traid/unapproved.py" in result.stdout


def test_maintenance_cannot_activate_a_card_or_authorize_next_card(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "maintenance/lifecycle-protection")
    control_path = fixture / "PROJECT_CONTROL.md"
    control = control_path.read_text().replace("Next Card Authorized: NO", "Next Card Authorized: YES", 1)
    control_path.write_text(control)
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "NEXT_CARD_AUTHORIZATION_PRESENT" in result.stdout


def test_maintenance_checker_is_not_incident_specific() -> None:
    source = CHECKER.read_text()
    assert "ci-python-portability" not in source
    assert "V1-C02" not in source
    assert "V1-C03" not in source
