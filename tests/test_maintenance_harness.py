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


def _maintenance_fixture(
    tmp_path: Path,
    branch: str,
    *,
    dirty_path: str | None = None,
    allowed_paths: tuple[str, ...] = (
        "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md", "TRAID_ENGINEERING_HARNESS.md",
        "GIT_WORKFLOW.md", "scripts/harness_consistency_check.py", "tests/test_harness_consistency.py",
        "tests/test_maintenance_harness.py",
    ),
) -> Path:
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=tmp_path, check=True)
    # Live files provide unrelated Card/evidence scaffolding only. Replace the
    # entire maintenance authorization so policy tests use explicit scenarios.
    control = (ROOT / "PROJECT_CONTROL.md").read_text()
    evidence = (ROOT / "TRAID_CARD_EVIDENCE_MAP.md").read_text()
    evidence = re.sub(r"^### (?:Current|Historical) Maintenance Re-Audit Record\n.*?(?=^# 20\.)", "", evidence, flags=re.MULTILINE | re.DOTALL)
    control = re.sub(r"^Git Branch: .+$", f"Git Branch: {branch}", control, count=1, flags=re.MULTILINE)
    maintenance = "\n".join((
        "### Current Maintenance Record", "", "```text",
        "Maintenance Task ID: TEST-MAINTENANCE-FIXTURE",
        "Title: Synthetic maintenance scope scenario",
        "Status: IN_PROGRESS — explicit fixture scenario",
        "Reason: exercise production maintenance scope validation",
        "Originating Evidence: isolated deterministic governance test",
        "Base Commit: pending — fixture base is filled after initial commit",
        f"Branch: {branch}",
        "Maintenance Start Authorization: GRANTED — synthetic test fixture only",
        "Authorized Scope: synthetic maintenance checker scenario",
        "Prohibited Scope: unrelated files and Card lifecycle changes",
        "Expected Areas: PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md",
        "Required Validation: production checker invocation",
        "External Git Permissions: NOT_GRANTED",
        "Closure Evidence: fixture only; no delivery",
        "Safe Resume: continue the isolated test scenario only",
        f"Allowed Paths: {', '.join(allowed_paths)}",
        "```", "",
    ))
    control, count = re.subn(
        r"^### Current Maintenance Record\n.*?(?=^---$)", maintenance, control,
        count=1, flags=re.MULTILINE | re.DOTALL,
    )
    assert count == 1
    working_tree = "DIRTY_ALLOWED" if dirty_path else "CLEAN"
    control = re.sub(r"^Working Tree: .+$", f"Working Tree: {working_tree}", control, count=1, flags=re.MULTILINE)
    (tmp_path / "PROJECT_CONTROL.md").write_text(control)
    (tmp_path / "TRAID_CARD_EVIDENCE_MAP.md").write_text(evidence)
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    subprocess.run(["git", "add", "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True, env=env)
    base = _git(tmp_path, "rev-parse", "--short", "HEAD")
    control = re.sub(r"^Git Checkpoint: .+$", f"Git Checkpoint: {base} — verified fixture checkpoint", control, count=1, flags=re.MULTILINE)
    control = re.sub(
        r"(^### Current Maintenance Record\n.*?^Base Commit: )[^\r\n]+$",
        rf"\g<1>{base} — verified fixture base",
        control,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
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
    dirty_path = "tests/test_maintenance_harness.py"
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/future-repository-fix",
        dirty_path=dirty_path,
        allowed_paths=("PROJECT_CONTROL.md", dirty_path),
    )
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
        ("maintenance/branch-mismatch", lambda text: re.sub(r"(^### Current Maintenance Record\n[\s\S]*?^Branch: ).+$", r"\g<1>maintenance/other-fix", text, count=1, flags=re.MULTILINE), "MAINTENANCE_BRANCH_AUTHORIZATION_MISMATCH"),
        ("maintenance/wrong-base", lambda text: re.sub(r"(^### Current Maintenance Record\n[\s\S]*?^Base Commit: ).+$", r"\g<1>0000000", text, count=1, flags=re.MULTILINE), "MAINTENANCE_BASE_NOT_ANCESTOR"),
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


def test_maintenance_scope_scenario_ignores_live_allowed_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_read_text = Path.read_text

    def altered_live_control(path: Path, *args: object, **kwargs: object) -> str:
        content = original_read_text(path, *args, **kwargs)
        if path.resolve() == (ROOT / "PROJECT_CONTROL.md").resolve():
            return re.sub(r"^Allowed Paths:.*$", "Allowed Paths: unrelated/live/path.py", content, flags=re.MULTILINE)
        return content

    monkeypatch.setattr(Path, "read_text", altered_live_control)
    dirty_path = "tests/test_maintenance_harness.py"
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/live-scope-isolation",
        dirty_path=dirty_path,
        allowed_paths=("PROJECT_CONTROL.md", dirty_path),
    )
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


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
