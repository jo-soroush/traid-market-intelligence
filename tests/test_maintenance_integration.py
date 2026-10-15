"""Disposable Git histories exercise the actual checker and CI squash runner."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from test_maintenance_harness import ROOT, _git, _maintenance_fixture, _run_checker, consistency


GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, env=GIT_ENV, check=True, capture_output=True)


def commit(repo: Path, message: str = "fixture") -> None:
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)


def audit(repo: Path, base: str, branch: str, task: str) -> None:
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    body = f'''### Current Maintenance Re-Audit Record

```text
Record Classification: CURRENT
Maintenance Task ID: {task}
Status: PASS
Candidate Type: WORKTREE
Branch: {branch}
Base SHA: {base}
Candidate Diff SHA-256: placeholder
Untracked Files: NONE
Verifier context: synthetic independent Claude review fixture, not real authorization
Canonical inputs reviewed: synthetic contract and invariants
Evidence reviewed: synthetic scratch candidate
Findings: NONE
Unresolved blockers: NONE
Gap dispositions: NONE
Limitations: synthetic local scenario only
Verdict: PASS for isolated test only
Delivery authorization/performance: GRANTED / NOT_PERFORMED — synthetic human approval fixture only
```

'''
    p.write_text(p.read_text().replace("# 20. Final Evidence Principle", body + "# 20. Final Evidence Principle"))
    digest = consistency.worktree_candidate_identity(repo, base)["Candidate Diff SHA-256"]
    p.write_text(p.read_text().replace("Candidate Diff SHA-256: placeholder", "Candidate Diff SHA-256: " + digest))


def candidate(tmp_path: Path) -> tuple[Path, str, str]:
    branch = "maintenance/integration-fixture"
    repo = _maintenance_fixture(
        tmp_path, branch, working_tree_state="DIRTY_ALLOWED",
        allowed_paths=("PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md", "proof.txt", ".github/workflows/fixture.yml"),
    )
    # Put production code in the base so the disposable CI runner can execute it.
    shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    (repo / "scripts").mkdir()
    for name in ("harness_consistency_check.py", "check_maintenance_integration.py"):
        shutil.copy2(ROOT / "scripts" / name, repo / "scripts" / name)
    shutil.copy2(ROOT / ".gitignore", repo / ".gitignore")
    commit(repo, "production code baseline")
    base = _git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/main", base)
    p = repo / "PROJECT_CONTROL.md"
    text = p.read_text()
    text = re.sub(r"^Git Checkpoint:.*$", "Git Checkpoint: " + base, text, count=1, flags=re.M)
    text = re.sub(r"(^### Current Maintenance Record\n.*?^Base Commit: )[^\n]+", r"\g<1>" + base,
                  text, count=1, flags=re.M | re.S)
    text = re.sub(r"(^### Current Maintenance Record\n.*?^Status: )[^\n]+", r"\g<1>READY_FOR_HUMAN_REVIEW",
                  text, count=1, flags=re.M | re.S)
    p.write_text(text)
    (repo / "proof.txt").write_text("bounded maintenance change\n")
    audit(repo, base, branch, "TEST-MAINTENANCE-FIXTURE")
    commit(repo, "reviewed synthetic candidate")
    result = _run_checker(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    return repo, base, branch


def integrate(repo: Path, base: str, branch: str, *, squash: bool = True) -> None:
    git(repo, "switch", "-c", "main", base)
    if squash:
        git(repo, "merge", "--squash", branch)
        git(repo, "commit", "-m", "synthetic squash integration")
    else:
        git(repo, "merge", "--no-ff", "-m", "synthetic merge", branch)


@pytest.mark.parametrize("squash", [True, False])
def test_reviewed_delivery_survives_integration_without_writes(tmp_path: Path, squash: bool) -> None:
    repo, base, branch = candidate(tmp_path)
    before = {name: (repo / name).read_bytes() for name in ("PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md")}
    integrate(repo, base, branch, squash=squash)
    result = _run_checker(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "AUDIT_RUNTIME: HISTORICAL" in result.stdout
    assert "NO_ACTIVE_MAINTENANCE" in result.stdout
    assert all((repo / name).read_bytes() == content for name, content in before.items())
    assert not _git(repo, "status", "--porcelain")


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("Status", "NOT_RUN", "MAINTENANCE_DELIVERY_WITHOUT_RESOLVED_AUDIT"),
    ("Status", "BLOCKED", "MAINTENANCE_DELIVERY_WITHOUT_RESOLVED_AUDIT"),
    ("Verdict", "FAILED — failed review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "NOT_VERIFIED — unknown review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "UNRESOLVED — unresolved review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "UNKNOWN — unknown result", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "NOT_RUN — incomplete review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "not run — incomplete review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "BLOCKED — incomplete review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "FAIL — incomplete review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),
    ("Verdict", "PENDING — incomplete review", "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED"),

    ("Branch", "maintenance/wrong", "MAINTENANCE_CANDIDATE_BRANCH_MISMATCH"),
    ("Maintenance Task ID", "WRONG-TASK", "MAINTENANCE_AUDIT_TASK_ID_MISMATCH"),
    ("Base SHA", "a" * 40, "MAINTENANCE_CANDIDATE_BASE_MISMATCH"),
    ("Candidate Diff SHA-256", "b" * 64, "AUDITED_CANDIDATE_CHANGED"),
    ("Delivery authorization/performance", "NOT_GRANTED / NOT_PERFORMED", "MAINTENANCE_DELIVERY_AUTHORIZATION_MISSING"),
    ("Unresolved blockers", "blocking finding", "MAINTENANCE_AUDIT_BLOCKER_PRESENT"),
])
def test_integrated_invalid_audit_fails_closed(tmp_path: Path, field: str, value: str, reason: str) -> None:
    repo, base, branch = candidate(tmp_path)
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    text = p.read_text()
    start = text.index("### Current Maintenance Re-Audit Record")
    text = text[:start] + re.sub(r"^" + re.escape(field) + r":[^\n]*", field + ": " + value,
                               text[start:], count=1, flags=re.M)
    p.write_text(text)
    commit(repo, "invalid audit mutation")
    integrate(repo, base, branch)
    result = _run_checker(repo)
    assert result.returncode != 0
    assert reason in result.stdout, result.stdout


@pytest.mark.parametrize("mutation", ["content", "mode", "scope", "dirty", "duplicate", "duplicate_record", "stage", "declaration"])
def test_integrated_candidate_drift_is_rejected(tmp_path: Path, mutation: str) -> None:
    repo, base, branch = candidate(tmp_path)
    integrate(repo, base, branch)
    if mutation == "content":
        (repo / "proof.txt").write_text("unreviewed change\n")
    elif mutation == "mode":
        (repo / "proof.txt").chmod(0o755)
    elif mutation == "scope":
        (repo / "unauthorized.txt").write_text("outside scope\n")
    elif mutation == "dirty":
        (repo / "proof.txt").write_text("dirty main\n")
    elif mutation == "duplicate":
        p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
        p.write_text(p.read_text().replace("Status: PASS\nCandidate Type: WORKTREE",
                                          "Status: PASS\nStatus: PASS\nCandidate Type: WORKTREE", 1))
    elif mutation == "duplicate_record":
        p = repo / "PROJECT_CONTROL.md"
        p.write_text(p.read_text().replace("### Current Maintenance Record", "### Current Maintenance Record\n\n### Current Maintenance Record", 1))
    elif mutation == "stage":
        p = repo / "PROJECT_CONTROL.md"
        p.write_text(p.read_text().replace("Status: READY_FOR_HUMAN_REVIEW", "Status: IN_PROGRESS", 1))
    else:
        p = repo / "PROJECT_CONTROL.md"
        p.write_text(re.sub(r"^Git Branch:.*$", "Git Branch: maintenance/wrong", p.read_text(), count=1, flags=re.M))
    if mutation != "dirty":
        commit(repo, "unreviewed mutation")
    result = _run_checker(repo)
    assert result.returncode != 0, result.stdout


def test_multiple_deliveries_archive_previous_snapshot_in_next_pr(tmp_path: Path) -> None:
    repo, base, branch = candidate(tmp_path)
    integrate(repo, base, branch)
    assert _run_checker(repo).returncode == 0
    second_base = _git(repo, "rev-parse", "HEAD")
    second_branch = "maintenance/second-fixture"
    git(repo, "switch", "-c", second_branch)
    p = repo / "PROJECT_CONTROL.md"
    text = p.read_text()
    start = text.index("### Current Maintenance Record")
    end = text.index("\n---", start)
    previous = text[start:end]
    new = previous.replace("TEST-MAINTENANCE-FIXTURE", "TEST-SECOND-FIXTURE").replace(branch, second_branch).replace(base, second_base)
    text = text[:start] + new + "\n---\n\n" + previous.replace("### Current", "### Previous", 1) + text[end:]
    text = re.sub(r"^Git Branch:.*$", "Git Branch: " + second_branch, text, count=1, flags=re.M)
    p.write_text(text)
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    old_audit = p.read_text()
    p.write_text(old_audit.replace("### Current Maintenance Re-Audit Record", "### Historical Maintenance Re-Audit Record")
                 .replace("Record Classification: CURRENT", "Record Classification: HISTORICAL"))
    (repo / "proof.txt").write_text("second bounded delivery\n")
    audit(repo, second_base, second_branch, "TEST-SECOND-FIXTURE")
    commit(repo, "second reviewed candidate, previous snapshot archived")
    assert _run_checker(repo).returncode == 0
    git(repo, "switch", "main")
    git(repo, "merge", "--squash", second_branch)
    git(repo, "commit", "-m", "second squash integration")
    result = _run_checker(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TEST-MAINTENANCE-FIXTURE" in (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text()


@pytest.mark.parametrize("valid", [True, False])
def test_ci_runner_detects_post_merge_failure_before_merge(tmp_path: Path, valid: bool) -> None:
    repo, base, branch = candidate(tmp_path)
    if not valid:
        p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
        p.write_text(p.read_text().replace("GRANTED / NOT_PERFORMED", "NOT_GRANTED / NOT_PERFORMED"))
        commit(repo, "missing delivery approval")
    before = _git(repo, "rev-parse", "HEAD")
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/check_maintenance_integration.py"),
        "--base", base, "--head", before, "--branch", branch,
    ], cwd=repo, text=True, capture_output=True, check=False)
    assert (result.returncode == 0) is valid, result.stdout + result.stderr
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "branch", "--show-current") == branch
    assert not _git(repo, "status", "--porcelain")


def test_in_repo_review_attestation_does_not_authenticate_malicious_writer(tmp_path: Path) -> None:
    repo, base, branch = candidate(tmp_path)
    # A writer can manufacture identical bytes/metadata without a real review or
    # GitHub PR. Git has no way to distinguish this tree from a legitimate squash.
    git(repo, "switch", "-c", "main", base)
    git(repo, "merge", "--squash", branch)
    git(repo, "commit", "-m", "self-attested direct-main write, no GitHub PR")
    assert _run_checker(repo).returncode == 0


def test_ci_runner_rejects_wrong_source_branch(tmp_path: Path) -> None:
    repo, base, _ = candidate(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/check_maintenance_integration.py"),
        "--base", base, "--head", _git(repo, "rev-parse", "HEAD"), "--branch", "maintenance/wrong",
    ], cwd=repo, text=True, capture_output=True, check=False)
    assert result.returncode != 0
    assert "source must be the clean exact PR branch/head" in result.stdout


def test_shallow_history_fails_closed(tmp_path: Path) -> None:
    # The fixture helper expects its repository directory to exist.
    source = tmp_path / "source"
    source.mkdir()
    repo, base, branch = candidate(source)
    integrate(repo, base, branch)
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "--depth", "1", "--branch", "main", repo.as_uri(), str(shallow)],
                   check=True, capture_output=True)
    result = _run_checker(shallow)
    assert result.returncode != 0
    assert "MAINTENANCE_BASE_NOT_ANCESTOR" in result.stdout


@pytest.mark.parametrize("accepted", [True, False])
def test_integrated_review_gaps_keep_existing_disposition_gate(tmp_path: Path, accepted: bool) -> None:
    repo, base, branch = candidate(tmp_path)
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    text = p.read_text()
    start = text.index("### Current Maintenance Re-Audit Record")
    body = text[start:].replace("Status: PASS\n", "Status: PASS_WITH_GAPS\n", 1)
    body = body.replace("Findings: NONE", "Findings: documented non-blocking gap", 1)
    disposition = "NON_BLOCKING — synthetic accepted limitation" if accepted else "undisposed gap"
    body = body.replace("Gap dispositions: NONE", "Gap dispositions: " + disposition, 1)
    p.write_text(text[:start] + body)
    commit(repo, "synthetic review gap disposition")
    integrate(repo, base, branch)
    result = _run_checker(repo)
    assert (result.returncode == 0) is accepted, result.stdout
    if not accepted:
        assert "MAINTENANCE_AUDIT_GAPS_UNCLASSIFIED" in result.stdout


@pytest.mark.parametrize("conflict", [True, False])
def test_ci_runner_blocks_changed_or_conflicting_target(tmp_path: Path, conflict: bool) -> None:
    repo, base, branch = candidate(tmp_path)
    git(repo, "switch", "-c", "main", base)
    path = "proof.txt" if conflict else "outside-reviewed-candidate.txt"
    (repo / path).write_text("new main-side change\n")
    commit(repo, "target moved since independent review")
    target = _git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/main", target)
    git(repo, "switch", branch)
    source_head = _git(repo, "rev-parse", "HEAD")
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/check_maintenance_integration.py"),
        "--base", target, "--head", source_head, "--branch", branch,
    ], cwd=repo, text=True, capture_output=True, check=False)
    assert result.returncode != 0
    assert "MAINTENANCE_INTEGRATION: BLOCKED" in result.stdout
    assert _git(repo, "rev-parse", "HEAD") == source_head
    assert not _git(repo, "status", "--porcelain")


def test_reviewed_hidden_ci_path_remains_in_scope_after_squash(tmp_path: Path) -> None:
    repo, base, branch = candidate(tmp_path)
    target = repo / ".github" / "workflows" / "fixture.yml"
    target.parent.mkdir(parents=True)
    target.write_text("name: synthetic CI fixture\n")
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    digest = consistency.worktree_candidate_identity(repo, base)["Candidate Diff SHA-256"]
    start = p.read_text().index("### Current Maintenance Re-Audit Record")
    text = p.read_text()
    p.write_text(text[:start] + re.sub(r"^Candidate Diff SHA-256:.*$", "Candidate Diff SHA-256: " + digest,
                                    text[start:], count=1, flags=re.M))
    commit(repo, "reviewed CI path change")
    integrate(repo, base, branch)
    result = _run_checker(repo)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("missing", [True, False])
def test_ci_runner_requires_fresh_main_reference(tmp_path: Path, missing: bool) -> None:
    repo, base, branch = candidate(tmp_path)
    if missing:
        git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    else:
        remote = tmp_path.parent / (tmp_path.name + "-origin.git")
        git(repo, "init", "--bare", str(remote))
        git(repo, "remote", "add", "origin", str(remote))
        git(repo, "push", "origin", base + ":refs/heads/main")
        git(repo, "switch", "-c", "moved-target", base)
        (repo / "target-note.txt").write_text("main advanced after validation\n")
        commit(repo, "advance local remote main")
        git(repo, "push", "origin", "HEAD:refs/heads/main")
        git(repo, "switch", branch)
        # Execute the same fetch as CI against a local isolated origin.
        git(repo, "fetch", "--no-tags", "origin", "main")
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/check_maintenance_integration.py"),
        "--base", base, "--head", _git(repo, "rev-parse", "HEAD"), "--branch", branch,
    ], cwd=repo, text=True, capture_output=True, check=False)
    assert result.returncode != 0
    assert "MAINTENANCE_INTEGRATION: BLOCKED" in result.stdout
    if not missing:
        assert "current fetched main differs" in result.stdout
    assert not _git(repo, "status", "--porcelain")


def _hypothetical_card_start(repo: Path) -> None:
    git(repo,'switch','-c','card/v1-c07-hypothetical')
    p=repo/'PROJECT_CONTROL.md';s=p.read_text()
    s=re.sub(r'^Active Card: NONE$', 'Active Card: V1-C07',s,flags=re.M)
    s=re.sub(r'^Active Card State: NONE$', 'Active Card State: IN_PROGRESS',s,flags=re.M)
    s=re.sub(r'^Next Roadmap Card: V1-C07.*$', 'Next Roadmap Card: V1-C08',s,flags=re.M)
    s=re.sub(r'^Next Card Authorized:.*$', 'Next Card Authorized: NO — C08 NOT_GRANTED; scratch only',s,count=1,flags=re.M)
    s=re.sub(r'^Git Branch:.*$', 'Git Branch: card/v1-c07-hypothetical',s,count=1,flags=re.M)
    s=s.replace('| V1-C07 | Order Book & Liquidity Analytics | NOT_STARTED | NO |','| V1-C07 | Order Book & Liquidity Analytics | IN_PROGRESS | YES |',1)
    s=s.replace('Active Card is NONE','Active Card is V1-C07')
    active='''Current active-Card record:

```text
Card ID: V1-C07
Title: Order Book & Liquidity Analytics
State: IN_PROGRESS
Branch: card/v1-c07-hypothetical
Human Start Approval: GRANTED — SYNTHETIC ONLY; no real C07 permission
Human Delivery Approval: NOT_GRANTED
Delivery Verified: NO
```

V1-C07 Authorization: START_GRANTED; DELIVERY_NOT_GRANTED — SYNTHETIC ONLY

Current active-Card Contract/Risk Map:
```text
Card Verification Level: LEVEL_3
Risk rationale: synthetic workflow startup only; no financial computation implemented or authorized in reality
Invariants affected: FINANCIAL_AND_DATA_GUARDRAILS; unchanged deterministic ownership
Verification-technique applicability:
'''
    for name in consistency.VERIFICATION_TECHNIQUES:
        active += '  '+name+': NOT_APPLICABLE — state-only synthetic startup; real Card requires its own preflight/verification plan\n'
    active+='```\n\n'
    s=s.replace('## 7. Authorization Ledger',active+'## 7. Authorization Ledger',1);p.write_text(s)
    p=repo/'TRAID_CARD_EVIDENCE_MAP.md';s=p.read_text();a=s.index('## V1-C07 —');b=s.index('## V1-C08 —',a);body=s[a:b].replace('**Status:** NOT_STARTED','**Status:** IN_PROGRESS',1).replace('**Start Authorization:** NOT_GRANTED','**Start Authorization:** GRANTED — SYNTHETIC ONLY; no real C07 permission',1);p.write_text(s[:a]+body+s[b:])
    assert not consistency.resolve_card_state((repo/'PROJECT_CONTROL.md').read_text()).errors



def test_next_card_archives_predecessor_in_its_normal_startup(tmp_path: Path) -> None:
    repo, base, branch = candidate(tmp_path)
    integrate(repo, base, branch)
    main_head = _git(repo, "rev-parse", "HEAD")
    _hypothetical_card_start(repo)
    assert _run_checker(repo).returncode != 0  # Old binding cannot silently pass.
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    old = p.read_text()
    historical = old.replace("### Current Maintenance Re-Audit Record", "### Historical Maintenance Re-Audit Record", 1).replace("Record Classification: CURRENT", "Record Classification: HISTORICAL", 1)
    p.write_text(historical)
    p = repo / "PROJECT_CONTROL.md"
    text = p.read_text()
    start = text.index("### Current Maintenance Record")
    end = text.index("\n---", start)
    body = re.sub(r"^Status:.*$", "Status: CLOSED / DELIVERED / VERIFIED — synthetic integration", text[start:end], count=1, flags=re.M)
    p.write_text(text[:start] + body.replace("### Current Maintenance Record", "### Previous Maintenance Record", 1) + text[end:])
    result = _run_checker(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text() == historical
    assert _git(repo, "rev-parse", "main") == main_head
    assert _git(repo, "rev-list", "--count", base + "..main") == "1"


def test_review_branch_rejects_pass_with_unresolved_verdict(tmp_path: Path) -> None:
    repo, _, _ = candidate(tmp_path)
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    p.write_text(p.read_text().replace("Verdict: PASS for isolated test only", "Verdict: NOT_RUN — incomplete review"))
    result = _run_checker(repo)
    assert result.returncode != 0
    assert "MAINTENANCE_AUDIT_VERDICT_UNRESOLVED" in result.stdout


def test_hidden_alias_cannot_enter_review_candidate_scope(tmp_path: Path) -> None:
    repo, base, _ = candidate(tmp_path)
    allowed = "scripts/harness_consistency_check.py"
    p = repo / "PROJECT_CONTROL.md"
    p.write_text(p.read_text().replace("Allowed Paths: PROJECT_CONTROL.md,", "Allowed Paths: " + allowed + ", PROJECT_CONTROL.md,"))
    unexpected = repo / ".scripts" / "harness_consistency_check.py"
    unexpected.parent.mkdir()
    unexpected.write_text("unexpected source\n")
    git(repo, "add", str(unexpected))
    p = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    digest = consistency.worktree_candidate_identity(repo, base)["Candidate Diff SHA-256"]
    p.write_text(re.sub(r"^Candidate Diff SHA-256:.*$", "Candidate Diff SHA-256: " + digest, p.read_text(), flags=re.M))
    result = _run_checker(repo)
    assert result.returncode != 0
    assert "MAINTENANCE_OUT_OF_SCOPE:.scripts/harness_consistency_check.py" in result.stdout


def _isolated_install_script() -> str:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    section = workflow.split("- name: Install from isolated committed source\n", 1)[1]
    block = section.split("        run: |\n", 1)[1].split("      - ", 1)[0]
    return "\n".join(line[10:] for line in block.splitlines() if line.strip())


@pytest.mark.parametrize("mutation", [None, "tracked", "untracked", "checkout-build"])
def test_ci_install_boundary_preserves_identity_without_hiding_changes(tmp_path: Path, mutation: str | None) -> None:
    repo, base, _ = candidate(tmp_path)
    tools = tmp_path.parent / (tmp_path.name + "-tools")
    tools.mkdir()
    runtime = tmp_path.parent / (tmp_path.name + "-runner-temp")
    runtime.mkdir()
    # Controlled builder models setuptools' output while executing the actual
    # workflow shell. Real pip/setuptools installation is validated separately
    # by the full CI simulation, so this regression needs no network or wheel.
    wrapper = tools / "python"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import sys\nfrom pathlib import Path\n"
        "assert sys.argv[1:4] == ['-m', 'pip', 'install']\n"
        "source = Path(sys.argv[4].removesuffix('[dev]'))\n"
        "assert (source / 'src/traid/main.py').is_file()\n"
        "target = source / 'build/lib/traid/generated.py'\n"
        "target.parent.mkdir(parents=True)\ntarget.write_text('# generated build output\\n')\n"
    )
    wrapper.chmod(0o755)
    frozen = consistency.worktree_candidate_identity(repo, base)
    env = {**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"], "RUNNER_TEMP": str(runtime)}
    for _ in range(2):
        result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", _isolated_install_script()], cwd=repo, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not _git(repo, "status", "--porcelain")
        assert consistency.worktree_candidate_identity(repo, base) == frozen
        assert _run_checker(repo).returncode == 0
    assert len(list(runtime.glob("*/build/lib/traid/generated.py"))) == 2
    if mutation is None:
        return
    path = {"tracked": "proof.txt", "untracked": "src/traid/unexpected.py", "checkout-build": "build/lib/traid/unexpected.py"}[mutation]
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("unexpected candidate modification\n")
    result = _run_checker(repo)
    assert result.returncode != 0
    assert "AUDITED_CANDIDATE_CHANGED" in result.stdout
    assert target.exists()  # Validation must never clean away unexpected files.
