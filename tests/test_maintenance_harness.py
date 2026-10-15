from __future__ import annotations

import os
import re
import subprocess
import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "harness_consistency_check.py"
SPEC = importlib.util.spec_from_file_location("maintenance_harness_checker", CHECKER)
assert SPEC and SPEC.loader
consistency = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = consistency
SPEC.loader.exec_module(consistency)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _run_checker(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, str(CHECKER)], cwd=cwd, text=True, capture_output=True, env=env)


def _idle_maintenance_scaffold(control: str, evidence: str) -> tuple[str, str]:
    """Give policy scenarios an explicit idle Card state, independent of live C06."""
    active = re.search(r"^Active Card: (V1-C\d{2}|NONE)$", control, re.MULTILINE)
    assert active, "canonical Card state must exist in the scaffold"
    card_id = active.group(1)
    if card_id == "NONE":
        return control, evidence

    row = re.search(rf"^\| {re.escape(card_id)} \| ([^|]+) \|[^\n]+$", control, re.MULTILINE)
    assert row, "active Card must have a canonical status row"
    title = row.group(1).strip()
    control, row_count = re.subn(
        rf"^\| {re.escape(card_id)} \| [^|]+ \|[^\n]+$",
        f"| {card_id} | {title} | NOT_STARTED | NO | NOT_RUN | PENDING |",
        control, count=1, flags=re.MULTILINE,
    )
    assert row_count == 1
    control = re.sub(r"^Active Card: V1-C\d{2}$", "Active Card: NONE", control, flags=re.MULTILINE)
    control = re.sub(r"^Active Card State: .+$", "Active Card State: NONE", control, count=1, flags=re.MULTILINE)
    control = re.sub(r"^Next Roadmap Card: .+$", f"Next Roadmap Card: {card_id}", control, flags=re.MULTILINE)
    control = re.sub(r"^Next Card Authorized: .+$", f"Next Card Authorized: NO — {card_id} start NOT_GRANTED", control, count=1, flags=re.MULTILINE)
    control = re.sub(r"^Implementation Authorization: .+$", "Implementation Authorization: NONE — synthetic maintenance fixture", control, count=1, flags=re.MULTILINE)
    control = re.sub(r"^Project Phase: .+$", "Project Phase: INTEGRATED / SYNTHETIC_IDLE", control, count=1, flags=re.MULTILINE)
    control = re.sub(r"^Card Start: .+$", "Card Start: NOT_GRANTED — synthetic maintenance fixture", control, count=1, flags=re.MULTILINE)
    control = re.sub(rf"^{re.escape(card_id)} Authorization: .+\n", "", control, flags=re.MULTILINE)
    # Idle scenarios verify the already-completed predecessor, not the active
    # Card's deliberately pending quality gate.
    a = control.index("## 21. Card Quality Gate State")
    b = control.index("## 22.", a)
    section = re.sub(r"^CARD_QUALITY_GATE: (PASS|BLOCKED|NOT_RUN).*$",
                     "CARD_QUALITY_GATE: PASS — synthetic completed predecessor",
                     control[a:b], flags=re.MULTILINE)
    control = control[:a] + section + control[b:]
    control, record_count = re.subn(
        r"^Current active-Card record:\n\n```text\n.*?^```\n",
        "", control, count=1, flags=re.MULTILINE | re.DOTALL,
    )
    assert record_count == 1
    control, resume_count = re.subn(
        r"^## 34\. Current Safe Resume Point\n.*?(?=^## 35\.)",
        f"## 34. Current Safe Resume Point\n\n```text\nSafe Resume: synthetic maintenance scenario only\nActive Card is NONE\nNext Roadmap Card: {card_id}\n```\n\n---\n\n",
        control, count=1, flags=re.MULTILINE | re.DOTALL,
    )
    assert resume_count == 1
    evidence, evidence_count = re.subn(
        rf"^## {re.escape(card_id)} — [^\n]+\n.*?(?=^## V1-C\d{{2}} |\Z)",
        f"## {card_id} — {title}\n\n**Status:** NOT_STARTED\n\n**Start Authorization:** NOT_GRANTED\n\n**Next Card Authorization:** NOT_GRANTED\n\n",
        evidence, count=1, flags=re.MULTILINE | re.DOTALL,
    )
    assert evidence_count == 1
    return control, evidence


def _maintenance_fixture(
    tmp_path: Path,
    branch: str,
    *,
    dirty_path: str | None = None,
    working_tree_state: str | None = None,
    allowed_paths: tuple[str, ...] = (
        "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md", "TRAID_ENGINEERING_HARNESS.md",
        "GIT_WORKFLOW.md", "scripts/harness_consistency_check.py", "tests/test_harness_consistency.py",
        "tests/test_maintenance_harness.py",
    ),
) -> Path:
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=tmp_path, check=True)
    # Live files supply only document structure. The policy scenario declares
    # an idle Card state and its own maintenance authorization.
    control = (ROOT / "PROJECT_CONTROL.md").read_text()
    evidence = (ROOT / "TRAID_CARD_EVIDENCE_MAP.md").read_text()
    control, evidence = _idle_maintenance_scaffold(control, evidence)
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
    # A normal next Card archives the predecessor; fixture authorization must
    # not depend on a live current-maintenance heading existing indefinitely.
    if count == 0:
        anchor = "## 5."
        position = control.index(anchor)
        control = control[:position] + maintenance + "\n---\n\n" + control[position:]
    assert "### Current Maintenance Record" in control
    working_tree = working_tree_state or ("DIRTY_ALLOWED" if dirty_path else "CLEAN")
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


def _add_current_audit_record(repo: Path) -> str:
    evidence_path = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    evidence = evidence_path.read_text()
    evidence = re.sub(
        r"^### (?:Current|Historical) Maintenance Re-Audit Record\n.*?(?=^### |^## |\Z)",
        "",
        evidence,
        flags=re.MULTILINE | re.DOTALL,
    )
    section = re.search(r"^## 25\.[^\n]*\n", evidence, re.MULTILINE)
    assert section, "synthetic repository must retain the canonical AEVS evidence owner"
    base_short = re.search(
        r"^### Current Maintenance Record\n.*?^Base Commit: ([0-9a-f]{7,40})\b",
        (repo / "PROJECT_CONTROL.md").read_text(), re.MULTILINE | re.DOTALL,
    )
    assert base_short, "maintenance fixture must declare its own base commit"
    base = _git(repo, "rev-parse", base_short.group(1))
    record = """### Current Maintenance Re-Audit Record

```text
Record Classification: CURRENT
Maintenance Task ID: TEST-MAINTENANCE-FIXTURE
Status: NOT_RUN
Candidate Type: WORKTREE
Branch: BRANCH
Base SHA: BASE_SHA
Candidate Diff SHA-256: pending
Untracked Files: pending
Verifier context: NOT_RUN
Canonical inputs reviewed: NOT_RUN
Evidence reviewed: NOT_RUN
Findings: NOT_RUN
Unresolved blockers: NOT_RUN
Gap dispositions: NOT_RUN
Limitations: audit not run
Verdict: NOT_RUN
```

""".replace("BRANCH", _git(repo, "branch", "--show-current")).replace("BASE_SHA", base)
    end_of_owner = re.search(r"^# 20\. Final Evidence Principle", evidence, re.MULTILINE)
    assert end_of_owner and section.start() < end_of_owner.start()
    evidence = evidence[:end_of_owner.start()] + "\n" + record + evidence[end_of_owner.start():]
    evidence_path.write_text(evidence)
    identity = consistency.worktree_candidate_identity(repo, base)
    evidence = evidence.replace("Candidate Diff SHA-256: pending", f"Candidate Diff SHA-256: {identity['Candidate Diff SHA-256']}", 1)
    evidence = evidence.replace("Untracked Files: pending", f"Untracked Files: {identity['Untracked Files']}", 1)
    evidence_path.write_text(evidence)
    return base


def test_real_current_audit_record_survives_dirty_stage_and_clean_commit(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/current-audit-transition",
        working_tree_state="DIRTY_ALLOWED",
        allowed_paths=("PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md", "TRAID_ENGINEERING_HARNESS.md"),
    )
    harness_doc = fixture / "TRAID_ENGINEERING_HARNESS.md"
    harness_doc.write_text("baseline tracked harness content\n")
    subprocess.run(["git", "add", "TRAID_ENGINEERING_HARNESS.md"], cwd=fixture, check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    subprocess.run(["git", "commit", "-qm", "add tracked maintenance fixture path"], cwd=fixture, check=True, env=env)
    harness_doc.write_text("authorized dirty harness content\n")
    base = _add_current_audit_record(fixture)
    record = (fixture / "TRAID_CARD_EVIDENCE_MAP.md").read_text()
    current_identity = consistency.worktree_candidate_identity(fixture, base)
    assert consistency.current_maintenance_candidate_issues(
        record, _git(fixture, "branch", "--show-current"), fixture, "TEST-MAINTENANCE-FIXTURE"
    ) == ()

    dirty_result = _run_checker(fixture)
    assert dirty_result.returncode == 0, dirty_result.stdout + dirty_result.stderr

    subprocess.run(["git", "add", "PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md", "TRAID_ENGINEERING_HARNESS.md"], cwd=fixture, check=True)
    staged_identity = consistency.worktree_candidate_identity(fixture, base)
    assert staged_identity["Candidate Diff SHA-256"] == current_identity["Candidate Diff SHA-256"]

    subprocess.run(["git", "commit", "-qm", "commit current audit candidate"], cwd=fixture, check=True, env=env)
    assert not _git(fixture, "status", "--porcelain")
    committed_identity = consistency.worktree_candidate_identity(fixture, base)
    assert committed_identity["Candidate Diff SHA-256"] == current_identity["Candidate Diff SHA-256"]
    clean_result = _run_checker(fixture)
    assert clean_result.returncode == 0, clean_result.stdout + clean_result.stderr


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


def test_authorized_maintenance_branch_with_clean_tree_and_dirty_allowed_passes(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/clean-dirty-allowed",
        working_tree_state="DIRTY_ALLOWED",
    )
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


def test_authorized_dirty_change_then_clean_commit_passes_both_states(tmp_path: Path) -> None:
    dirty_path = "tests/test_maintenance_harness.py"
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/dirty-to-clean-transition",
        dirty_path=dirty_path,
        working_tree_state="DIRTY_ALLOWED",
        allowed_paths=("PROJECT_CONTROL.md", dirty_path),
    )
    dirty_result = _run_checker(fixture)
    assert dirty_result.returncode == 0, dirty_result.stdout + dirty_result.stderr

    target = fixture / dirty_path
    assert target.read_text() == "authorized maintenance fixture\n"
    subprocess.run(["git", "add", "PROJECT_CONTROL.md", dirty_path], cwd=fixture, check=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }
    subprocess.run(["git", "commit", "-qm", "authorized fixture change"], cwd=fixture, check=True, env=env)
    assert not _git(fixture, "status", "--porcelain")
    clean_result = _run_checker(fixture)
    assert clean_result.returncode == 0, clean_result.stdout + clean_result.stderr


def test_clean_required_rejects_authorized_but_dirty_maintenance_tree(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/clean-required-dirty",
        dirty_path="tests/test_maintenance_harness.py",
        working_tree_state="CLEAN",
        allowed_paths=("PROJECT_CONTROL.md", "tests/test_maintenance_harness.py"),
    )
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "WORKING_TREE_STATE_MISMATCH" in result.stdout


def test_dirty_allowed_without_maintenance_authorization_fails_closed(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/missing-authorization",
        working_tree_state="DIRTY_ALLOWED",
    )
    control_path = fixture / "PROJECT_CONTROL.md"
    control = control_path.read_text()
    control, count = re.subn(
        r"^### Current Maintenance Record\n.*?(?=^---$)",
        "",
        control,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert count == 1
    control_path.write_text(control)
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "MAINTENANCE_RECORD_MISSING" in result.stdout


def test_dirty_allowed_on_idle_main_with_uncommitted_file_is_unauthorized(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "main",
        dirty_path="tests/unapproved.py",
        working_tree_state="DIRTY_ALLOWED",
        allowed_paths=("PROJECT_CONTROL.md", "tests/unapproved.py"),
    )
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "UNAUTHORIZED_DIRTY_WORKTREE" in result.stdout


def test_unknown_working_tree_state_is_rejected(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/unknown-working-tree-state",
        working_tree_state="DIRTY_REQUIRED",
    )
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "WORKING_TREE_POLICY_INVALID" in result.stdout


def test_dirty_allowed_does_not_bypass_mismatched_audit_identity(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(
        tmp_path,
        "maintenance/mismatched-audit-identity",
        working_tree_state="DIRTY_ALLOWED",
    )
    base = _git(fixture, "rev-parse", "HEAD")
    evidence_path = fixture / "TRAID_CARD_EVIDENCE_MAP.md"
    evidence = evidence_path.read_text()
    evidence += """

### Current Maintenance Re-Audit Record

```text
Record Classification: CURRENT
Maintenance Task ID: TEST-MAINTENANCE-FIXTURE
Status: NOT_RUN
Candidate Type: WORKTREE
Branch: maintenance/mismatched-audit-identity
Base SHA: BASE_SHA
Candidate Diff SHA-256: 0000000000000000000000000000000000000000000000000000000000000000
Untracked Files: NONE
Verifier context: NOT_RUN
Canonical inputs reviewed: NOT_RUN
Evidence reviewed: NOT_RUN
Findings: NOT_RUN
Unresolved blockers: NOT_RUN
Gap dispositions: NOT_RUN
Limitations: audit not run
Verdict: NOT_RUN
```
""".replace("BASE_SHA", base)
    evidence_path.write_text(evidence)
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "AUDITED_CANDIDATE_CHANGED:Candidate Diff SHA-256" in result.stdout


def test_authorized_maintenance_branch_with_clean_state_passes(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "maintenance/clean-fix")
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


def test_authorized_hotfix_branch_passes(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "hotfix/recovery-fix")
    result = _run_checker(fixture)
    assert result.returncode == 0, result.stdout + result.stderr


def test_maintenance_fixture_has_idle_card_precondition_and_fails_if_activated(tmp_path: Path) -> None:
    fixture = _maintenance_fixture(tmp_path, "maintenance/idle-card-precondition")
    control_path = fixture / "PROJECT_CONTROL.md"
    control = control_path.read_text()
    assert re.search(r"^Active Card: NONE$", control, re.MULTILINE)
    assert re.search(r"^Active Card State: NONE$", control, re.MULTILINE)
    assert _run_checker(fixture).returncode == 0
    first_pending = re.search(r"^\| (V1-C\d{2}) \| ([^|]+) \| NOT_STARTED \| NO \| NOT_RUN \| PENDING \|$", control, re.MULTILINE)
    assert first_pending
    card_id, title = first_pending.groups()
    control_path.write_text(control.replace(first_pending.group(0), f"| {card_id} | {title} | IN_PROGRESS | YES | BLOCKED | IN_PROGRESS |", 1))
    result = _run_checker(fixture)
    assert result.returncode != 0
    assert "ACTIVE_CARD_NONE_WITH_ACTIVE_STATE" in result.stdout


@pytest.mark.parametrize(
    ("branch", "mutator", "reason"),
    [
        ("maintenance/unknown-fix", lambda text: text.replace("### Current Maintenance Record", "### Removed Maintenance Record"), "MAINTENANCE_RECORD_MISSING"),
        ("maintenance/branch-mismatch", lambda text: re.sub(r"(^### Current Maintenance Record\n[\s\S]*?^Branch: ).+$", r"\g<1>maintenance/other-fix", text, count=1, flags=re.MULTILINE), "MAINTENANCE_BRANCH_AUTHORIZATION_MISMATCH"),
        ("maintenance/wrong-base", lambda text: re.sub(r"(^### Current Maintenance Record\n[\s\S]*?^Base Commit: ).+$", r"\g<1>0000000", text, count=1, flags=re.MULTILINE), "MAINTENANCE_BASE_NOT_ANCESTOR"),
    ],
)
def test_invalid_maintenance_record_blocks(tmp_path: Path, branch: str, mutator, reason: str) -> None:
    fixture = _maintenance_fixture(tmp_path, branch, working_tree_state="DIRTY_ALLOWED")
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
