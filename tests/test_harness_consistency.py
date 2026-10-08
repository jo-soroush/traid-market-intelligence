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


def _valid_independent_audit(status: str = "PASS", kind: str = "WORKTREE") -> str:
    candidate = ("- Candidate Commit SHA: " + "b" * 40 + "\n") if kind == "COMMIT" else (
        "- Candidate Diff SHA-256: " + "c" * 64 + "\n- Untracked Files: CLAUDE.md\n"
    )
    return """### Independent Audit
- Status: """ + status + "\n- Candidate Type: " + kind + "\n- Branch: card/v1-c10-example\n- Base SHA: " + "a" * 40 + "\n" + candidate + """\
- Verifier context: fresh independent review context
- Canonical inputs reviewed: specification, Exit Gate, invariants, and risk record
- Evidence reviewed: diff, executed tests, validation, and Evidence Map
- Findings: minor documentation gap recorded
- Unresolved blockers: NONE
- Gap dispositions: ACCEPTED — minor documentation gap accepted with recorded rationale
- Limitations: minor documentation gap remains visible to delivery review
- Verdict: recommend delivery review
"""


def _valid_technique_closure() -> str:
    lines = ["### Verification Technique Closure"]
    for technique in consistency.VERIFICATION_TECHNIQUES:
        if technique == "property-based testing":
            lines.extend((f"  {technique}: CONDITIONAL — ordering complexity determines applicability",
                          "    Trigger: use if combinatorial ordering exceeds deterministic examples",
                          "    Resolution: NOT_TRIGGERED",
                          "    Resolution reason: deterministic examples covered all observed orderings"))
        elif technique == "fuzzing":
            lines.append(f"  {technique}: NOT_APPLICABLE — no untrusted parser boundary is changed")
        else:
            lines.extend((f"  {technique}: REQUIRED — verifies the relevant acceptance behavior",
                          "    Execution: EXECUTED", "    Evidence: focused test result in Evidence Map"))
    return "\n".join(lines) + "\n"


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


def test_current_c04_learning_record_uses_canonical_schema_and_matrix() -> None:
    section = EVIDENCE.read_text().split("## V1-C04 —", 1)[1].split("\n## V1-C05 —", 1)[0]
    section = "## V1-C04 —" + section
    record = consistency.CardRecord("V1-C04", "Hyperliquid Provider Verification & Adapter", "READY_FOR_HUMAN_REVIEW", True)
    assert consistency.card_documentation_issues(section, record) == ()


def test_ready_card_missing_learning_field_is_rejected() -> None:
    section = "## V1-C10 — Card 10\n### Learning Record\n" + "\n".join(
        f"{field}: verified" for field in consistency.CANONICAL_LEARNING_RECORD_FIELDS if field != "Known Limitations"
    ) + "\n### Exit Gate Proof\n### Exit Gate Evidence Matrix\n| Requirement | Implementation evidence | Test/runtime evidence | Current Status |\n|---|---|---|---|\n| x | x | x | PASS |\n### CARD_QUALITY_GATE\nStatus: PASS\n"
    record = consistency.CardRecord("V1-C10", "Card 10", "READY_FOR_HUMAN_REVIEW", True)
    assert any("LEARNING_FIELD_MISSING:Known Limitations" in issue for issue in consistency.card_documentation_issues(section, record))


def test_complete_future_card_missing_learning_field_is_rejected() -> None:
    section = "## V1-C27 — Card 27\n### Learning Record\nWhat We Built: verified\n### Exit Gate Proof\n"
    record = consistency.CardRecord("V1-C27", "Card 27", "COMPLETE", True)
    assert consistency.card_documentation_issues(section, record)


def test_not_started_card_pending_learning_is_allowed() -> None:
    record = consistency.CardRecord("V1-C05", "Data Quality", "NOT_STARTED", False)
    assert consistency.card_documentation_issues("## V1-C05 — Data Quality\n### Learning Record\nPending", record) == ()


def test_current_evidence_matrix_rejects_unresolved_status_but_allows_history() -> None:
    complete_fields = "\n".join(f"{field}: verified" for field in consistency.CANONICAL_LEARNING_RECORD_FIELDS)
    section = """## V1-C10 — Card 10
### Learning Record
""" + complete_fields + """
### Exit Gate Proof
Historical note: reconnect was incomplete before remediation.
### Exit Gate Evidence Matrix
| Requirement | Implementation evidence | Test/runtime evidence | Current Status |
|---|---|---|---|
| reconnect | implementation | test | IN_PROGRESS |
### CARD_QUALITY_GATE
Status: PASS
""" + _valid_technique_closure() + _valid_independent_audit()
    record = consistency.CardRecord("V1-C10", "Card 10", "READY_FOR_HUMAN_REVIEW", True)
    assert any("CURRENT_EVIDENCE_UNRESOLVED" in issue for issue in consistency.card_documentation_issues(section, record))
    section = section.replace("IN_PROGRESS", "PASS")
    assert consistency.card_documentation_issues(section, record) == ()


def test_validation_checkpoint_requires_one_current_checkpoint() -> None:
    section = """## V1-C10 — Card 10
### Learning Record
""" + "\n".join(f"{field}: verified" for field in consistency.CANONICAL_LEARNING_RECORD_FIELDS) + """
### Exit Gate Proof
### Validation Checkpoints
| Checkpoint | Test Count | Status | Current |
|---|---:|---|---|
| historical | 154 | PASS | NO |
| latest | 159 | PASS | YES |
### CARD_QUALITY_GATE
Status: PASS
""" + _valid_technique_closure() + _valid_independent_audit()
    record = consistency.CardRecord("V1-C10", "Card 10", "READY_FOR_HUMAN_REVIEW", True)
    assert consistency.card_documentation_issues(section, record) == ()
    stale = section.replace("| historical | 154 | PASS | NO |", "| historical | 154 | PASS | YES |")
    assert any("VALIDATION_CHECKPOINT_CURRENT_DECLARATION_INVALID" in issue for issue in consistency.card_documentation_issues(stale, record))


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
Git Checkpoint: PLACEHOLDER
Working Tree: DIRTY_ALLOWED
TraID repository test state: VERIFIED
CARD_QUALITY_GATE: PASS
Learning Record Status: COMPLETE
V1-C01 Authorization: START_GRANTED; DELIVERY_NOT_GRANTED
Implementation: IN_PROGRESS — no completed Cards
## 8. Roadmap Position
Completed Cards: NONE
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
    return subprocess.run([sys.executable, str(CHECKER)], cwd=tmp_path, text=True, capture_output=True, env=env)


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
    stale = control.replace("Git Checkpoint:", "Git Checkpoint: 0000000 #")
    (tmp_path / "PROJECT_CONTROL.md").write_text(stale)
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "GIT_HEAD_STATE_MISMATCH" in result.stdout


def test_live_current_head_claim_is_rejected() -> None:
    control = CONTROL.read_text().replace("Git Checkpoint:", "Git HEAD:", 1)
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "CURRENT_HEAD_STORED_AS_LIVE_FACT" in issues


def test_ancestor_checkpoint_is_accepted_without_head_equality() -> None:
    control = CONTROL.read_text()
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "CURRENT_HEAD_STORED_AS_LIVE_FACT" not in issues
    assert "GIT_CHECKPOINT_NOT_ANCESTOR" not in issues


def test_closed_maintenance_pending_text_is_rejected() -> None:
    control = re.sub(
        r"(^### Current Maintenance Record\n.*?^Status: )[^\r\n]+$",
        r"\g<1>CLOSED / DELIVERED / VERIFIED — validation pending completion",
        CONTROL.read_text(),
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "CLOSED_MAINTENANCE_HAS_PENDING_TEXT" in issues


def test_completed_card_summary_must_include_all_completed_cards() -> None:
    control = CONTROL.read_text().replace(
        "V1-C01, V1-C02, V1-C03, V1-C04, and V1-C05 implementation",
        "V1-C01 and V1-C02 implementation",
        1,
    )
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "COMPLETED_CARD_SUMMARY_MISMATCH:IMPLEMENTATION" in issues


def test_completed_card_summary_rejects_extra_noncomplete_card() -> None:
    control = CONTROL.read_text().replace(
        "Completed Cards: V1-C01, V1-C02, V1-C03, V1-C04, V1-C05",
        "Completed Cards: V1-C01, V1-C02, V1-C03, V1-C04, V1-C05, V1-C06",
        1,
    )
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "COMPLETED_CARD_SUMMARY_MISMATCH:ROADMAP_POSITION" in issues


def test_completed_card_summary_accepts_future_dynamically_completed_card() -> None:
    control = CONTROL.read_text()
    control = re.sub(
        r"^\| V1-C27 \|([^|]+)\| NOT_STARTED \| NO \|",
        r"| V1-C27 |\1| COMPLETE | YES |",
        control,
        count=1,
        flags=re.MULTILINE,
    )
    control = control.replace("V1-C04, and V1-C05 implementation", "V1-C04, V1-C05, and V1-C27 implementation", 1)
    control = control.replace(
        "Completed Cards: V1-C01, V1-C02, V1-C03, V1-C04, V1-C05",
        "Completed Cards: V1-C01, V1-C02, V1-C03, V1-C04, V1-C05, V1-C27",
        1,
    )
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert not any("COMPLETED_CARD_SUMMARY" in issue for issue in issues)


def test_historical_completed_sets_do_not_create_current_summary_failure() -> None:
    control = CONTROL.read_text()
    evidence = EVIDENCE.read_text() + "\nHistorical note: Completed Cards: V1-C01, V1-C02.\n"
    issues = consistency.current_state_issues(control, evidence, _git(ROOT, "rev-parse", "HEAD"))
    assert not any("COMPLETED_CARD_SUMMARY" in issue for issue in issues)


def _aevs_contract_map(*, level: str = "LEVEL_2", rationale: str = "This work changes a bounded contract and exercises limited data hazards.", invariants: str = "HARNESS §36; FINANCIAL_AND_DATA_GUARDRAILS §4") -> str:
    lines = [
        "Current active-Card Contract/Risk Map:",
        "```text",
        f"Card Verification Level: {level}",
        f"Risk rationale: {rationale}",
        f"Invariants affected: {invariants}",
        "Verification-technique applicability:",
    ]
    for technique in consistency.VERIFICATION_TECHNIQUES:
        if technique == "property-based testing":
            lines.extend((f"  {technique}: CONDITIONAL — ordering complexity determines applicability",
                          "    Trigger: use if combinatorial ordering exceeds deterministic examples"))
        elif technique == "fuzzing":
            lines.append(f"  {technique}: NOT_APPLICABLE — no untrusted parser boundary in this work")
        else:
            lines.append(f"  {technique}: REQUIRED — verifies the relevant acceptance behavior")
    lines.append("```")
    return "\n".join(lines)


def test_future_active_card_requires_aevs_contract_risk_fields() -> None:
    valid = _aevs_contract_map()
    assert consistency.active_contract_map_issues(valid, "V1-C06") == ()
    assert consistency.active_contract_map_issues("", "V1-C06") == ("AEVS_CONTRACT_RISK_MAP_MISSING",)
    assert consistency.active_contract_map_issues(valid, "NONE") == ()


@pytest.mark.parametrize(
    ("replacement", "reason"),
    [
        ("Card Verification Level: ", "AEVS_VERIFICATION_LEVEL_MISSING_OR_INVALID"),
        ("Risk rationale: \n", "AEVS_RISK_RATIONALE_MISSING"),
        ("Invariants affected: \n", "AEVS_AFFECTED_INVARIANTS_MISSING"),
        ("fuzzing: UNKNOWN — no parser", "AEVS_TECHNIQUE_DECISION_INVALID:fuzzing"),
    ],
)
def test_future_active_card_blocks_false_green_aevs_contract_fields(replacement: str, reason: str) -> None:
    contract = _aevs_contract_map()
    if replacement.startswith("Card Verification"):
        contract = contract.replace("Card Verification Level: LEVEL_2", replacement.rstrip())
    elif replacement.startswith("Risk rationale"):
        contract = contract.replace("Risk rationale: This work changes a bounded contract and exercises limited data hazards.", replacement.rstrip())
    elif replacement.startswith("Invariants"):
        contract = contract.replace("Invariants affected: HARNESS §36; FINANCIAL_AND_DATA_GUARDRAILS §4", replacement.rstrip())
    else:
        contract = contract.replace("fuzzing: NOT_APPLICABLE — no untrusted parser boundary in this work", replacement)
    assert reason in consistency.active_contract_map_issues(contract, "V1-C06")


def test_conditional_and_not_applicable_techniques_require_reason_and_trigger() -> None:
    valid = _aevs_contract_map()
    assert consistency.active_contract_map_issues(valid, "V1-C10") == ()
    missing_trigger = valid.replace("    Trigger: use if combinatorial ordering exceeds deterministic examples", "")
    assert any("AEVS_TECHNIQUE_TRIGGER_MISSING" in issue for issue in consistency.active_contract_map_issues(missing_trigger, "V1-C10"))


def test_independent_audit_required_for_future_review_and_completion() -> None:
    section = "## V1-C06 — Card 6\n"
    for state in ("READY_FOR_HUMAN_REVIEW", "COMPLETE"):
        record = consistency.CardRecord("V1-C06", "Card 6", state, True)
        assert consistency.independent_audit_issues(section, record)
    audit = _valid_independent_audit("PASS_WITH_GAPS")
    for state in ("READY_FOR_HUMAN_REVIEW", "COMPLETE"):
        record = consistency.CardRecord("V1-C06", "Card 6", state, True)
        assert consistency.independent_audit_issues(section + audit, record) == ()
    blocked = audit.replace("Status: PASS_WITH_GAPS", "Status: BLOCKED")
    record = consistency.CardRecord("V1-C06", "Card 6", "COMPLETE", True)
    assert any("INDEPENDENT_AUDIT_NOT_COMPLETE" in issue for issue in consistency.independent_audit_issues(section + blocked, record))
    unresolved = audit.replace("Unresolved blockers: NONE", "Unresolved blockers: unresolved contract gap")
    assert "V1-C06:INDEPENDENT_AUDIT_BLOCKER_PRESENT" in consistency.independent_audit_issues(section + unresolved, record)


@pytest.mark.parametrize(
    ("state", "status", "passes"),
    [
        ("READY_FOR_HUMAN_REVIEW", "NOT_RUN", True),
        ("COMPLETE", "NOT_RUN", False),
        ("COMPLETE", "BLOCKED", False),
        ("COMPLETE", "PASS", True),
        ("COMPLETE", "PASS_WITH_GAPS", True),
    ],
)
def test_independent_audit_lifecycle_stage(state: str, status: str, passes: bool) -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", state, True)
    assert (consistency.independent_audit_issues(_valid_independent_audit(status), record) == ()) is passes


def test_pass_with_gaps_cannot_hide_blockers_or_unclassified_gaps() -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", "COMPLETE", True)
    valid = _valid_independent_audit("PASS_WITH_GAPS")
    assert consistency.independent_audit_issues(valid, record) == ()
    assert any("BLOCKER_PRESENT" in issue for issue in consistency.independent_audit_issues(
        valid.replace("Unresolved blockers: NONE", "Unresolved blockers: unresolved safety issue"), record))
    assert any("GAP_DISPOSITION_MISSING" in issue for issue in consistency.independent_audit_issues(
        valid.replace("ACCEPTED — minor documentation gap accepted with recorded rationale", "TBD"), record))
    assert any("LIMITATIONS_MISSING" in issue for issue in consistency.independent_audit_issues(
        valid.replace("Limitations: minor documentation gap remains visible to delivery review", "Limitations: N/A"), record))


@pytest.mark.parametrize("kind", ["COMMIT", "WORKTREE"])
def test_strict_candidate_identity_accepts_both_schemas(kind: str) -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", "COMPLETE", True)
    assert consistency.independent_audit_issues(_valid_independent_audit(kind=kind), record) == ()


@pytest.mark.parametrize(
    ("before", "after", "reason"),
    [
        ("Candidate Type: WORKTREE", "Candidate Type: current candidate", "CANDIDATE_TYPE_INVALID"),
        ("Base SHA: " + "a" * 40, "Base SHA: latest", "BASE_SHA_INVALID"),
        ("Candidate Diff SHA-256: " + "c" * 64, "Candidate Diff SHA-256: deadbeef", "DIFF_SHA256_INVALID"),
        ("Untracked Files: CLAUDE.md", "Untracked Files: TBD", "UNTRACKED_FILES_INVALID"),
    ],
)
def test_vague_or_malformed_candidate_identity_is_rejected(before: str, after: str, reason: str) -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", "COMPLETE", True)
    issues = consistency.independent_audit_issues(_valid_independent_audit().replace(before, after), record)
    assert any(reason in issue for issue in issues)


def test_commit_candidate_rejects_short_sha() -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", "COMPLETE", True)
    audit = _valid_independent_audit(kind="COMMIT").replace("Candidate Commit SHA: " + "b" * 40, "Candidate Commit SHA: abc123")
    assert any("COMMIT_SHA_INVALID" in issue for issue in consistency.independent_audit_issues(audit, record))


def test_candidate_identity_rejects_mixed_commit_and_worktree_fields() -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", "COMPLETE", True)
    audit = _valid_independent_audit(kind="COMMIT").replace(
        "- Candidate Commit SHA:", "- Candidate Diff SHA-256: " + "c" * 64 + "\n- Candidate Commit SHA:")
    assert any("CANDIDATE_SCHEMA_AMBIGUOUS" in issue for issue in consistency.independent_audit_issues(audit, record))


@pytest.mark.parametrize("value", ["NONE", "NONE —", "NONE — N/A", "NONE — TBD"])
def test_invariants_none_requires_substantive_reason(value: str) -> None:
    assert "AEVS_AFFECTED_INVARIANTS_REASON_MISSING" in consistency.active_contract_map_issues(
        _aevs_contract_map(invariants=value), "V1-C06")


def test_invariants_none_with_reason_and_canonical_references_pass() -> None:
    assert consistency.active_contract_map_issues(_aevs_contract_map(
        invariants="NONE — no canonical invariant is affected because this change only updates documentation routing"), "V1-C06") == ()
    assert consistency.active_contract_map_issues(_aevs_contract_map(), "V1-C06") == ()


def test_technique_closure_is_stage_gated() -> None:
    early = _aevs_contract_map()
    assert consistency.active_contract_map_issues(early, "V1-C06") == ()
    record = consistency.CardRecord("V1-C06", "Card 6", "READY_FOR_HUMAN_REVIEW", True)
    section = "## V1-C06 — Card 6\n" + _valid_independent_audit("NOT_RUN")
    assert "V1-C06:AEVS_TECHNIQUE_CLOSURE_MISSING" in consistency.card_documentation_issues(section, record)


@pytest.mark.parametrize(
    ("before", "after", "reason"),
    [
        ("    Trigger: use if combinatorial ordering exceeds deterministic examples", "", "TRIGGER_MISSING"),
        ("    Resolution: NOT_TRIGGERED", "", "RESOLUTION_MISSING_OR_INVALID"),
        ("    Resolution reason: deterministic examples covered all observed orderings", "", "NOT_TRIGGERED_REASON_MISSING"),
        ("    Resolution: NOT_TRIGGERED", "    Resolution: TRIGGERED_EXECUTED", "EXECUTION_EVIDENCE_MISSING"),
        ("    Resolution: NOT_TRIGGERED", "    Resolution: REVISED_WITH_AUTHORIZATION", "REVISION_AUTHORIZATION_MISSING"),
        ("    Evidence: focused test result in Evidence Map", "", "REQUIRED_EXECUTION_MISSING"),
        ("    Execution: EXECUTED", "    Execution: PLANNED", "REQUIRED_EXECUTION_MISSING"),
        ("fuzzing: NOT_APPLICABLE — no untrusted parser boundary is changed", "fuzzing: NOT_APPLICABLE — N/A", "RATIONALE_MISSING"),
    ],
)
def test_technique_closure_rejects_false_green(before: str, after: str, reason: str) -> None:
    text = _valid_technique_closure().replace(before, after, 1)
    assert any(reason in issue for issue in consistency.technique_issues(text, require_closure=True))


def test_conditional_resolution_and_required_execution_positive_paths() -> None:
    valid = _valid_technique_closure()
    assert consistency.technique_issues(valid, require_closure=True) == ()
    triggered = valid.replace("Resolution: NOT_TRIGGERED", "Resolution: TRIGGERED_EXECUTED").replace(
        "Resolution reason: deterministic examples covered all observed orderings",
        "Evidence: executed property test result in Evidence Map")
    assert consistency.technique_issues(triggered, require_closure=True) == ()
    revised = valid.replace("Resolution: NOT_TRIGGERED", "Resolution: REVISED_WITH_AUTHORIZATION").replace(
        "Resolution reason: deterministic examples covered all observed orderings",
        "Resolution reason: approved risk-map revision after boundary change\n    Authorization reference: approved work item review record")
    assert consistency.technique_issues(revised, require_closure=True) == ()


def test_quality_gate_pass_requires_closure_even_before_ready_state() -> None:
    record = consistency.CardRecord("V1-C06", "Card 6", "IN_PROGRESS", True)
    assert consistency.card_documentation_issues("## V1-C06 — Card 6\n### CARD_QUALITY_GATE\nStatus: NOT_RUN\n", record) == ()
    issues = consistency.card_documentation_issues("## V1-C06 — Card 6\n### CARD_QUALITY_GATE\nStatus: PASS\n", record)
    assert "V1-C06:AEVS_TECHNIQUE_CLOSURE_MISSING" in issues


def test_technique_closure_cannot_silently_change_phase_zero_decision_or_trigger() -> None:
    contract = _aevs_contract_map()
    closure = _valid_technique_closure()
    assert consistency.technique_alignment_issues(contract, closure, "V1-C06") == ()
    drifted_decision = closure.replace("fuzzing: NOT_APPLICABLE — no untrusted parser boundary is changed",
                                       "fuzzing: REQUIRED — verifies parser behavior")
    assert any("DECISION_DRIFT:fuzzing" in issue for issue in consistency.technique_alignment_issues(
        contract, drifted_decision, "V1-C06"))
    drifted_trigger = closure.replace("Trigger: use if combinatorial ordering exceeds deterministic examples",
                                      "Trigger: use only on provider parser changes")
    assert any("TRIGGER_DRIFT:property-based testing" in issue for issue in consistency.technique_alignment_issues(
        contract, drifted_trigger, "V1-C06"))


def test_c01_to_c05_history_needs_no_independent_audit_retrofit() -> None:
    evidence = EVIDENCE.read_text()
    for number in range(1, 6):
        card_id = f"V1-C{number:02d}"
        record = consistency.CardRecord(card_id, f"Card {number}", "COMPLETE", True)
        assert consistency.independent_audit_issues(consistency.card_evidence_section(evidence, card_id), record) == ()


def _candidate_fixture(tmp_path: Path) -> tuple[Path, str]:
    subprocess.run(["git", "init", "-q", "-b", "maintenance/audit-fixture"], cwd=tmp_path, check=True)
    (tmp_path / "AGENTS.md").write_text("canonical governance behavior\n")
    (tmp_path / "TRAID_CARD_EVIDENCE_MAP.md").write_text("""## 25. AEVS Maintenance
Historical audit: BLOCKED
### Current Maintenance Re-Audit Record
Status: NOT_RUN
Candidate Type: WORKTREE
Branch: maintenance/audit-fixture
Base SHA: pending
Candidate Diff SHA-256: pending
Untracked Files: CLAUDE.md
Verdict: pending
""")
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    subprocess.run(["git", "add", "AGENTS.md", "TRAID_CARD_EVIDENCE_MAP.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True, env=env)
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "CLAUDE.md").write_text("non-canonical route\n")
    return tmp_path, base


def test_frozen_worktree_identity_is_reproducible_and_binds_untracked_content(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    assert frozen["Untracked Files"] == "CLAUDE.md"
    assert len(frozen["Candidate Diff SHA-256"]) == 64
    assert consistency.worktree_candidate_identity(repo, base) == frozen
    assert consistency.candidate_applicability_issues(frozen, frozen) == ()
    (repo / "CLAUDE.md").write_text("changed non-canonical route\n")
    assert consistency.candidate_applicability_issues(frozen, consistency.worktree_candidate_identity(repo, base))


def test_evidence_only_audit_recording_does_not_invalidate_frozen_candidate(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    evidence = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    evidence.write_text(evidence.read_text().replace("Verdict: pending", "Verdict: observed BLOCKED verdict"))
    assert consistency.candidate_applicability_issues(frozen, consistency.worktree_candidate_identity(repo, base)) == ()
    evidence.write_text(evidence.read_text().replace("Historical audit: BLOCKED", "Historical audit: PASS"))
    assert consistency.candidate_applicability_issues(frozen, consistency.worktree_candidate_identity(repo, base))


def test_extra_audit_record_field_is_not_exempt_from_candidate_hash(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    evidence = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    evidence.write_text(evidence.read_text().replace("Verdict: pending", "New governance rule: bypass validation\nVerdict: pending"))
    assert consistency.candidate_applicability_issues(frozen, consistency.worktree_candidate_identity(repo, base))


def test_current_maintenance_record_binds_actual_candidate(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    evidence_path = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    evidence = evidence_path.read_text().replace("Base SHA: pending", f"Base SHA: {base}").replace(
        "Candidate Diff SHA-256: pending", f"Candidate Diff SHA-256: {frozen['Candidate Diff SHA-256']}")
    evidence_path.write_text(evidence)
    assert consistency.current_maintenance_candidate_issues(evidence, "maintenance/audit-fixture", repo) == ()
    (repo / "AGENTS.md").write_text("changed governance behavior\n")
    assert any("AUDITED_CANDIDATE_CHANGED" in issue for issue in consistency.current_maintenance_candidate_issues(
        evidence, "maintenance/audit-fixture", repo))


def test_current_maintenance_manifest_rejects_vague_or_wrong_untracked_list(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    evidence = (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_text().replace("Base SHA: pending", f"Base SHA: {base}").replace(
        "Candidate Diff SHA-256: pending", f"Candidate Diff SHA-256: {frozen['Candidate Diff SHA-256']}")
    assert "MAINTENANCE_CANDIDATE_UNTRACKED_INVALID" in consistency.current_maintenance_candidate_issues(
        evidence.replace("Untracked Files: CLAUDE.md", "Untracked Files: TBD"), "maintenance/audit-fixture", repo)
    assert "MAINTENANCE_CANDIDATE_UNTRACKED_MISMATCH" in consistency.current_maintenance_candidate_issues(
        evidence.replace("Untracked Files: CLAUDE.md", "Untracked Files: NONE"), "maintenance/audit-fixture", repo)


def test_staging_identical_untracked_content_does_not_change_technical_identity(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    subprocess.run(["git", "add", "CLAUDE.md"], cwd=repo, check=True)
    staged = consistency.worktree_candidate_identity(repo, base)
    assert staged["Untracked Files"] == "NONE"
    assert consistency.candidate_applicability_issues(frozen, staged) == ()


def test_active_card_audit_is_bound_to_current_worktree(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    audit = _valid_independent_audit("NOT_RUN").replace("card/v1-c10-example", "maintenance/audit-fixture").replace("a" * 40, base)
    evidence_path = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    evidence_path.write_text("## V1-C06 — Card 6\n" + audit)
    frozen = consistency.worktree_candidate_identity(repo, base)
    evidence = evidence_path.read_text().replace("c" * 64, frozen["Candidate Diff SHA-256"])
    evidence_path.write_text(evidence)
    record = consistency.CardRecord("V1-C06", "Card 6", "READY_FOR_HUMAN_REVIEW", True)
    assert consistency.active_card_candidate_issues(evidence, record, repo, "maintenance/audit-fixture") == ()
    (repo / "AGENTS.md").write_text("changed implementation governance\n")
    assert any("AUDITED_CANDIDATE_CHANGED" in issue for issue in consistency.active_card_candidate_issues(
        evidence, record, repo, "maintenance/audit-fixture"))


def test_commit_audit_rejects_uncommitted_material_change_but_allows_evidence_recording(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    (repo / "CLAUDE.md").unlink()
    evidence_path = repo / "TRAID_CARD_EVIDENCE_MAP.md"
    audit = _valid_independent_audit("NOT_RUN", "COMMIT").replace("card/v1-c10-example", "maintenance/audit-fixture").replace("a" * 40, base).replace("b" * 40, "PENDING_COMMIT")
    evidence_path.write_text("## V1-C06 — Card 6\n" + audit)
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
    subprocess.run(["git", "add", "TRAID_CARD_EVIDENCE_MAP.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate fixture"], cwd=repo, check=True, env=env)
    commit = _git(repo, "rev-parse", "HEAD")
    evidence = evidence_path.read_text().replace("PENDING_COMMIT", commit)
    evidence_path.write_text(evidence)
    record = consistency.CardRecord("V1-C06", "Card 6", "READY_FOR_HUMAN_REVIEW", True)
    assert consistency.active_card_candidate_issues(evidence, record, repo, "maintenance/audit-fixture") == ()
    (repo / "AGENTS.md").write_text("material change after commit\n")
    assert "V1-C06:AUDITED_COMMIT_HAS_MATERIAL_WORKTREE_CHANGE" in consistency.active_card_candidate_issues(
        evidence, record, repo, "maintenance/audit-fixture")


def test_tracked_mode_and_divergent_index_are_bound_to_candidate(tmp_path: Path) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    target = repo / "AGENTS.md"
    target.chmod(0o755)
    assert consistency.candidate_applicability_issues(frozen, consistency.worktree_candidate_identity(repo, base))
    target.chmod(0o644)
    target.write_text("staged governance edit\n")
    subprocess.run(["git", "add", "AGENTS.md"], cwd=repo, check=True)
    target.write_text("different unstaged governance edit\n")
    with_index = consistency.worktree_candidate_identity(repo, base)
    subprocess.run(["git", "reset", "-q", "--", "AGENTS.md"], cwd=repo, check=True)
    without_index = consistency.worktree_candidate_identity(repo, base)
    assert with_index["Candidate Diff SHA-256"] != without_index["Candidate Diff SHA-256"]


def _maintenance_audit_scenario(
    *,
    stage: str = "READY_TO_DELIVER",
    audit_status: str = "NOT_RUN",
    findings: str = "one non-blocking documentation gap",
    blockers: str = "NONE",
    gaps: str = "NONE",
    limitations: str = "NONE",
) -> tuple[str, str]:
    """Build explicit policy inputs without inheriting the live maintenance state."""
    control = f"### Current Maintenance Record\nStatus: {stage}\n---\n"
    evidence = "\n".join((
        "### Current Maintenance Re-Audit Record",
        f"Status: {audit_status}",
        "Verifier context: independent review of the frozen fixture candidate",
        "Canonical inputs reviewed: specification, Exit Gate, invariants, and risk record",
        "Evidence reviewed: fixture diff, tests, validation, and Evidence Map",
        f"Findings: {findings}",
        f"Unresolved blockers: {blockers}",
        f"Gap dispositions: {gaps}",
        f"Limitations: {limitations}",
        "Verdict: recommend delivery review",
        "",
    ))
    return control, evidence


def test_maintenance_delivery_stage_requires_resolved_audit() -> None:
    control, not_run = _maintenance_audit_scenario(audit_status="NOT_RUN")
    assert "MAINTENANCE_DELIVERY_WITHOUT_RESOLVED_AUDIT" in consistency.maintenance_delivery_audit_issues(control, not_run)
    _, blocked = _maintenance_audit_scenario(audit_status="BLOCKED")
    assert "MAINTENANCE_DELIVERY_WITHOUT_RESOLVED_AUDIT" in consistency.maintenance_delivery_audit_issues(control, blocked)
    _, passed = _maintenance_audit_scenario(audit_status="PASS", findings="NONE")
    assert consistency.maintenance_delivery_audit_issues(control, passed) == ()
    review_control, _ = _maintenance_audit_scenario(stage="READY_FOR_HUMAN_REVIEW")
    assert consistency.maintenance_delivery_audit_issues(review_control, not_run) == ()


def test_maintenance_pass_with_gaps_requires_disposition_and_limitations() -> None:
    control, missing_disposition = _maintenance_audit_scenario(audit_status="PASS_WITH_GAPS")
    assert "MAINTENANCE_AUDIT_GAPS_UNCLASSIFIED" in consistency.maintenance_delivery_audit_issues(control, missing_disposition)
    accepted_gap = "DEFERRED — non-blocking hosted validation awaits delivery"
    _, missing_limitations = _maintenance_audit_scenario(audit_status="PASS_WITH_GAPS", gaps=accepted_gap)
    assert "MAINTENANCE_AUDIT_LIMITATIONS_MISSING" in consistency.maintenance_delivery_audit_issues(control, missing_limitations)
    _, unresolved_blocker = _maintenance_audit_scenario(
        audit_status="PASS_WITH_GAPS", gaps=accepted_gap, limitations="hosted validation remains pending",
        blockers="blocking audit finding remains open",
    )
    assert "MAINTENANCE_AUDIT_BLOCKER_PRESENT" in consistency.maintenance_delivery_audit_issues(control, unresolved_blocker)
    _, valid = _maintenance_audit_scenario(
        audit_status="PASS_WITH_GAPS", gaps=accepted_gap, limitations="hosted validation remains pending",
    )
    assert consistency.maintenance_delivery_audit_issues(control, valid) == ()


def test_maintenance_audit_policy_scenarios_do_not_read_live_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_live_read(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"policy scenario read live repository file: {self}")

    monkeypatch.setattr(Path, "read_text", reject_live_read)
    control, not_run = _maintenance_audit_scenario(audit_status="NOT_RUN")
    _, malformed_gaps = _maintenance_audit_scenario(audit_status="PASS_WITH_GAPS")
    assert "MAINTENANCE_DELIVERY_WITHOUT_RESOLVED_AUDIT" in consistency.maintenance_delivery_audit_issues(control, not_run)
    assert "MAINTENANCE_AUDIT_GAPS_UNCLASSIFIED" in consistency.maintenance_delivery_audit_issues(control, malformed_gaps)


@pytest.mark.parametrize("path", ["AGENTS.md", "tests/test_semantics.py", "scripts/harness_consistency_check.py"])
def test_material_governance_test_or_checker_change_invalidates_audit(tmp_path: Path, path: str) -> None:
    repo, base = _candidate_fixture(tmp_path)
    frozen = consistency.worktree_candidate_identity(repo, base)
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("material behavior change\n")
    assert consistency.candidate_applicability_issues(frozen, consistency.worktree_candidate_identity(repo, base))


def test_claude_entry_point_is_not_canonical_mutable_state_owner() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    bootstrap = (ROOT / "scripts/session_bootstrap.sh").read_text()
    checker = CHECKER.read_text()
    assert "non-canonical" in claude.lower()
    assert "Active Card" not in claude and "Git SHA" not in claude and "test counts" not in claude
    assert '"CLAUDE.md"' not in bootstrap
    assert "CLAUDE.md" not in checker


def test_aevs_does_not_create_a_second_validation_checkpoint_owner() -> None:
    control = CONTROL.read_text()
    active_map = re.search(r"^## 15\. Contract Map / Risk Map\n(.*?)(?=^## 16\.)", control, re.MULTILINE | re.DOTALL)
    assert active_map
    assert "Validation Checkpoints" not in active_map.group(1)
    assert consistency.validation_checkpoint_issues(
        "### Validation Checkpoints\n| Checkpoint | Result | Status | Current |\n|---|---|---|---|\n| current | local | PASS | YES |"
    ) == ()


def test_safe_resume_must_not_resume_completed_work() -> None:
    control = CONTROL.read_text()
    safe_resume = re.search(
        r"(^## 34\. Current Safe Resume Point\n)(.*?)(?=^## 35\.)",
        control,
        re.MULTILINE | re.DOTALL,
    )
    assert safe_resume
    updated = safe_resume.group(2).replace(
        "Do not resume a completed Card or\nmaintenance delivery.",
        "Resume C03 delivery.",
        1,
    )
    control = control[:safe_resume.start(2)] + updated + control[safe_resume.end(2):]
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "SAFE_RESUME_POINTS_TO_COMPLETED_WORK" in issues


@pytest.mark.parametrize("card_id", ["V1-C05", "V1-C10"])
def test_safe_resume_protection_derives_all_completed_cards(card_id: str) -> None:
    control = CONTROL.read_text()
    control = re.sub(
        rf"^\| {card_id} \|([^|]+)\| (?:NOT_STARTED \| NO|IN_PROGRESS \| YES|BLOCKED \| YES|READY_FOR_HUMAN_REVIEW \| YES) \|",
        rf"| {card_id} |\1| COMPLETE | YES |",
        control,
        count=1,
        flags=re.MULTILINE,
    )
    control = re.sub(
        r"(?s)(^## 34\. Current Safe Resume Point\n).*?(?=^## 35\.)",
        rf"\1Resume {card_id.removeprefix('V1-')} implementation.\n\n",
        control,
        count=1,
        flags=re.MULTILINE,
    )
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "SAFE_RESUME_POINTS_TO_COMPLETED_WORK" in issues


def test_negative_and_historical_card_references_remain_legal() -> None:
    control = CONTROL.read_text().replace("Do not resume a completed Card or maintenance delivery.", "Do not resume C03 delivery.", 1)
    issues = consistency.current_state_issues(control, EVIDENCE.read_text(), _git(ROOT, "rev-parse", "HEAD"))
    assert "SAFE_RESUME_POINTS_TO_COMPLETED_WORK" not in issues
    assert "V1-C03" in EVIDENCE.read_text()


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


@pytest.mark.parametrize("card_id", ["V1-C04", "V1-C10"])
def test_active_record_state_must_match_card_table(card_id: str) -> None:
    control = _state_fixture(card_id, "READY_FOR_HUMAN_REVIEW")
    control = control.replace(
        "## 6. Active Card Record\n",
        "## 6. Active Card Record\nState: IN_PROGRESS\n",
    )
    result = consistency.resolve_card_state(control)
    assert "ACTIVE_CARD_RECORD_STATE_MISMATCH" in result.errors


def test_matching_active_record_state_is_accepted() -> None:
    control = _state_fixture("V1-C04", "READY_FOR_HUMAN_REVIEW").replace(
        "## 6. Active Card Record\n",
        "## 6. Active Card Record\nState: READY_FOR_HUMAN_REVIEW\n",
    )
    assert not consistency.resolve_card_state(control).errors


def test_c27_matching_in_progress_active_record_state_is_accepted() -> None:
    control = _state_fixture("V1-C27", "IN_PROGRESS").replace(
        "## 6. Active Card Record\n",
        "## 6. Active Card Record\nState: IN_PROGRESS\n",
    )
    assert not consistency.resolve_card_state(control).errors


def test_historical_state_prose_does_not_trigger_current_state_check() -> None:
    control = _state_fixture("V1-C04", "READY_FOR_HUMAN_REVIEW") + "\nC04 previously entered IN_PROGRESS.\n"
    assert not consistency.resolve_card_state(control).errors


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
