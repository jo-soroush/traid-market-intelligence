#!/usr/bin/env python3
"""Fail-closed, Card-agnostic validation of TraID's canonical lifecycle state."""

from __future__ import annotations

import re
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from traid.harness.lifecycle import LifecycleFacts, evaluate_state_consistency


CANONICAL_LEARNING_RECORD_FIELDS = (
    "What We Wanted To Build", "Why It Matters", "System Before This Card",
    "Design Decision", "Alternatives Considered", "Why We Chose This Approach",
    "What We Implemented", "What We Built", "Why We Built It", "Engineering problem",
    "AI / Data / Financial concept", "How it works", "Architecture before",
    "Architecture after", "Important files and ownership", "Source / provenance",
    "Tests / evaluations and actual results", "Financial / data / security invariants",
    "Problems We Hit", "Root Cause", "How We Solved It", "Why The Fix Is Correct",
    "What We Rejected", "Problem(s) discovered", "How we diagnosed / solved them",
    "Known Limitations", "Professional engineering lesson", "Student takeaway",
    "Exit Gate proof", "What this enables next",
)
# Backward-compatible name for existing Harness tests and callers.
C01_LEARNING_RECORD_FIELDS = CANONICAL_LEARNING_RECORD_FIELDS
LEARNING_PLACEHOLDERS = frozenset({"", "pending", "not verified", "tbd", "todo", "not run"})
EMPTY_RATIONALES = LEARNING_PLACEHOLDERS | {"n/a", "na", "none", "not applicable", "-"}
CARD_STATES = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "READY_FOR_HUMAN_REVIEW", "COMPLETE", "DEFERRED"}
ACTIVE_STATES = {"IN_PROGRESS", "BLOCKED", "READY_FOR_HUMAN_REVIEW"}
CARD_ROW = re.compile(r"^\|\s*(V1-C\d{2})\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|\s*(YES|NO)\s*\|", re.MULTILINE)
CARD_ID = re.compile(r"^(V1-C\d{2})(?:\s+—\s+(.+))?$")
AEVS_ADOPTION_START_CARD_NUMBER = 6
VERIFICATION_TECHNIQUES = (
    "deterministic invariant testing",
    "property-based testing",
    "failure injection",
    "fuzzing",
    "mutation testing",
    "differential testing",
    "adversarial testing",
    "chaos testing",
    "formal methods",
)
TECHNIQUE_DECISIONS = {"REQUIRED", "CONDITIONAL", "NOT_APPLICABLE"}
INDEPENDENT_AUDIT_STATES = {"NOT_RUN", "PASS", "PASS_WITH_GAPS", "BLOCKED"}
CONDITIONAL_RESOLUTIONS = {"NOT_TRIGGERED", "TRIGGERED_EXECUTED", "REVISED_WITH_AUTHORIZATION"}
FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
AUDIT_RECONCILIATION_FIELDS = frozenset({
    "Status", "Candidate Type", "Branch", "Base SHA", "Candidate Commit SHA",
    "Candidate Diff SHA-256", "Untracked Files", "Verifier context",
    "Canonical inputs reviewed", "Evidence reviewed", "Findings",
    "Unresolved blockers", "Gap dispositions", "Limitations", "Verdict",
    "Delivery authorization/performance",
})
MAINTENANCE_BRANCH = re.compile(r"^(maintenance|hotfix)/[^/\s]+(?:[-/][^\s]+)*$")
MAINTENANCE_STATUSES = {
    "IN_PROGRESS",
    "READY_FOR_HUMAN_REVIEW",
    "READY_TO_DELIVER",
    "PUSHED",
    "CI_VERIFIED",
    "MERGED",
    "POST_MERGE_VERIFIED",
    "CLOSED / DELIVERED / VERIFIED",
}
MAINTENANCE_AUDIT_REQUIRED_STAGES = {
    "READY_FOR_HUMAN_REVIEW", "READY_TO_DELIVER", "PUSHED", "CI_VERIFIED", "MERGED", "POST_MERGE_VERIFIED",
}
MAINTENANCE_POST_MERGE_STAGES = {"MERGED", "POST_MERGE_VERIFIED", "CLOSED / DELIVERED / VERIFIED"}
MAINTENANCE_FIELDS = (
    "Maintenance Task ID",
    "Title",
    "Status",
    "Reason",
    "Originating Evidence",
    "Base Commit",
    "Branch",
    "Authorized Scope",
    "Prohibited Scope",
    "Expected Areas",
    "Required Validation",
    "External Git Permissions",
    "Closure Evidence",
    "Safe Resume",
    "Allowed Paths",
)


@dataclass(frozen=True)
class CardRecord:
    card_id: str
    title: str
    state: str
    start_approved: bool


@dataclass(frozen=True)
class ResolvedState:
    cards: tuple[CardRecord, ...]
    active_card: str
    active_state: str
    declared_next_card: str
    derived_next_card: str
    active_start_authorized: bool
    delivery_approval: bool
    delivery_verified: bool
    current_state_unambiguous: bool
    errors: tuple[str, ...]


def learning_record_issues(evidence_section: str) -> tuple[str, ...]:
    """Validate the canonical Learning Record for any completed/review-ready Card."""

    learning = re.search(r"^### Learning Record\n(.*?)(?=^### Exit Gate Proof$)", evidence_section, re.MULTILINE | re.DOTALL)
    if not learning:
        return ("LEARNING_RECORD_SECTION_MISSING",)
    body = learning.group(1)
    issues: list[str] = []
    for field in CANONICAL_LEARNING_RECORD_FIELDS:
        match = re.search(rf"^{re.escape(field)}:\s*(.*)$", body, re.MULTILINE)
        if not match:
            issues.append(f"LEARNING_FIELD_MISSING:{field}")
        elif match.group(1).strip().lower() in LEARNING_PLACEHOLDERS:
            issues.append(f"LEARNING_FIELD_EMPTY:{field}")
    return tuple(issues)


def card_evidence_section(evidence: str, card_id: str) -> str:
    match = re.search(rf"^## {re.escape(card_id)} .*?(?=^## V1-C\d{{2}} |\Z)", evidence, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


def current_evidence_issues(evidence_section: str) -> tuple[str, ...]:
    """Validate the optional structured current Exit-Gate matrix.

    Historical prose may contain failure words. Only the explicitly structured
    current matrix is interpreted as a live status source.
    """

    matrix = re.search(r"^### Exit Gate Evidence Matrix\n(.*?)(?=^### CARD_QUALITY_GATE$)", evidence_section, re.MULTILINE | re.DOTALL)
    if not matrix:
        return ()
    rows = re.findall(r"^\|\s*[^|]+\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+?)\s*\|\s*$", matrix.group(1), re.MULTILINE)
    if not rows:
        return ("CURRENT_EVIDENCE_MATRIX_EMPTY",)
    unresolved = []
    for value in rows:
        status = value.strip().split(" —", 1)[0].strip().upper()
        if status in {"CURRENT STATUS", "---"}:
            continue
        if status not in {"PASS", "NOT_APPLICABLE"}:
            unresolved.append(status)
    return ("CURRENT_EVIDENCE_UNRESOLVED:" + ",".join(unresolved),) if unresolved else ()


def validation_checkpoint_issues(evidence_section: str) -> tuple[str, ...]:
    """Validate optional structured validation checkpoints without parsing prose counts."""

    checkpoints = re.search(
        r"^### Validation Checkpoints\n(.*?)(?=^### |\Z)",
        evidence_section,
        re.MULTILINE | re.DOTALL,
    )
    if not checkpoints:
        return ()
    rows = re.findall(
        r"^\|\s*[^|]+\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+?)\s*\|\s*$",
        checkpoints.group(1),
        re.MULTILINE,
    )
    rows = [row.strip().upper() for row in rows if row.strip().upper() not in {"CURRENT", "---"}]
    if not rows:
        return ("VALIDATION_CHECKPOINTS_EMPTY",)
    current = [row for row in rows if row == "YES"]
    if len(current) != 1:
        return ("VALIDATION_CHECKPOINT_CURRENT_DECLARATION_INVALID",)
    return ()


def card_documentation_issues(evidence: str, record: "CardRecord") -> tuple[str, ...]:
    """Apply documentation requirements only to review-ready/completed Cards."""
    section = card_evidence_section(evidence, record.card_id)
    quality_block = re.search(r"^### CARD_QUALITY_GATE\n(.*?)(?=^### |\Z)", section, re.MULTILINE | re.DOTALL)
    quality_pass = bool(quality_block and re.search(r"^Status: PASS[ \t]*$", quality_block.group(1), re.MULTILINE))
    future = int(record.card_id[-2:]) >= AEVS_ADOPTION_START_CARD_NUMBER
    if record.state not in {"READY_FOR_HUMAN_REVIEW", "COMPLETE"} and not (future and quality_pass):
        return ()
    if not section:
        return (f"CARD_EVIDENCE_SECTION_MISSING:{record.card_id}",)
    issues: list[str] = []
    if record.state in {"READY_FOR_HUMAN_REVIEW", "COMPLETE"}:
        issues.extend(f"{record.card_id}:{issue}" for issue in learning_record_issues(section))
        issues.extend(f"{record.card_id}:{issue}" for issue in current_evidence_issues(section))
        issues.extend(f"{record.card_id}:{issue}" for issue in validation_checkpoint_issues(section))
    if future:
        closure = re.search(r"^### Verification Technique Closure\n(.*?)(?=^### |\Z)", section, re.MULTILINE | re.DOTALL)
        if not closure:
            issues.append(f"{record.card_id}:AEVS_TECHNIQUE_CLOSURE_MISSING")
        else:
            issues.extend(f"{record.card_id}:{issue}" for issue in technique_issues(closure.group(1), require_closure=True))
    if record.state in {"READY_FOR_HUMAN_REVIEW", "COMPLETE"}:
        issues.extend(independent_audit_issues(section, record))
    return tuple(issues)


def normalize_card_identity(value: str, titles: dict[str, str]) -> str:
    value = value.strip()
    if value == "NONE":
        return value
    match = CARD_ID.fullmatch(value)
    if not match or match.group(1) not in titles:
        raise ValueError(f"CARD_ID_UNRESOLVED:{value}")
    if match.group(2) is not None and match.group(2).strip() != titles[match.group(1)]:
        raise ValueError(f"CARD_TITLE_MISMATCH:{match.group(1)}")
    return match.group(1)


def parse_card_table(control: str) -> tuple[CardRecord, ...]:
    records = tuple(CardRecord(card_id, title, state, approved == "YES") for card_id, title, state, approved in CARD_ROW.findall(control))
    expected = tuple(f"V1-C{i:02d}" for i in range(1, 28))
    if len(records) != 27 or tuple(record.card_id for record in records) != expected:
        raise ValueError("CARD_ORDER_OR_COUNT_INVALID")
    if any(record.state not in CARD_STATES for record in records):
        raise ValueError("CARD_STATE_INVALID")
    return records


def _line_values(pattern: str, text: str) -> tuple[str, ...]:
    return tuple(match.group(1).strip() for match in re.finditer(pattern, text, re.MULTILINE))


def _maintenance_record(control: str) -> str:
    match = re.search(r"^### Current Maintenance Record\n(.*?)(?=^---$|^## \d+\.)", control, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def _current_repository_section(control: str) -> str:
    match = re.search(r"^## 4\. Repository / Git Reality\n(.*?)(?=^### Previous Maintenance Record$)", control, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def current_state_issues(control: str, evidence: str, head: str) -> tuple[str, ...]:
    """Reject mutable current-state prose that conflicts with runtime/owned state."""
    issues: list[str] = []
    current = _current_repository_section(control)
    if re.search(r"^Git HEAD:\s*[0-9a-f]{7,40}\b", current, re.MULTILINE):
        issues.append("CURRENT_HEAD_STORED_AS_LIVE_FACT")
    checkpoint = re.search(r"^Git Checkpoint:\s*([0-9a-f]{7,40})\b", current, re.MULTILINE)
    if checkpoint:
        sha = checkpoint.group(1)
        exists = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], check=False).returncode == 0
        ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", sha, head], check=False).returncode == 0
        if not exists:
            issues.append("GIT_CHECKPOINT_MISSING")
        elif not ancestor:
            issues.append("GIT_CHECKPOINT_NOT_ANCESTOR")
    expected = {record.card_id for record in parse_card_table(control) if record.state == "COMPLETE"}
    implementation_summary = re.search(r"^Implementation:\s*COMPLETE\s+—\s*(.+)$", current, re.MULTILINE)
    summaries: list[tuple[str, str | None]] = []
    if implementation_summary or re.search(r"^Implementation:\s*COMPLETE\b", current, re.MULTILINE):
        summaries.append(("IMPLEMENTATION", implementation_summary.group(1) if implementation_summary else None))
    roadmap_position = re.search(r"^## 8\. Roadmap Position\n(.*?)(?=^## 9\.|\Z)", control, re.MULTILINE | re.DOTALL)
    summaries.append(("ROADMAP_POSITION", (match.group(1) if roadmap_position and (match := re.search(r"^Completed Cards:\s*(.+)$", roadmap_position.group(1), re.MULTILINE)) else None)))
    for label, declared_text in summaries:
        if declared_text is None:
            issues.append(f"COMPLETED_CARD_SUMMARY_MISSING:{label}")
        elif set(re.findall(r"\bV1-C\d{2}\b", declared_text)) != expected:
            issues.append(f"COMPLETED_CARD_SUMMARY_MISMATCH:{label}")
    safe_resume = re.search(r"^## 34\. Current Safe Resume Point\n(.*?)(?=^## 35\.)", control, re.MULTILINE | re.DOTALL)
    if safe_resume:
        safe_text = safe_resume.group(1)
        completed_ids = {record.card_id for record in parse_card_table(control) if record.state == "COMPLETE"}
        actionable = re.compile(r"\b(?:resume|continue|reopen)\s+(?:(?:the|a)\s+)?(?:V1-)?(C\d{2})\b", re.IGNORECASE)
        for match in actionable.finditer(safe_text):
            context = safe_text[max(0, match.start() - 32):match.start()]
            if re.search(r"\b(?:do not|don't|never|must not|cannot)\s*$", context, re.IGNORECASE):
                continue
            if f"V1-{match.group(1).upper()}" in completed_ids:
                issues.append("SAFE_RESUME_POINTS_TO_COMPLETED_WORK")
                break
        if re.search(r"\b(?:resume|continue|reopen)\s+(?:the\s+)?maintenance\b", safe_text, re.IGNORECASE) and not re.search(r"\b(?:do not|don't|never|must not|cannot)\s+resume\s+maintenance\b", safe_text, re.IGNORECASE):
            issues.append("SAFE_RESUME_POINTS_TO_COMPLETED_WORK")
    maintenance = _maintenance_record(control)
    status = re.search(r"^Status:\s*(CLOSED / DELIVERED / VERIFIED)\b", maintenance, re.MULTILINE)
    if status and re.search(r"\b(pending|awaiting|not merged|not verified|incomplete)\b", maintenance, re.IGNORECASE):
        issues.append("CLOSED_MAINTENANCE_HAS_PENDING_TEXT")
    oi = re.search(r"^## 22\. OI Contract Reconciliation.*?^```\n(.*?)^```", evidence, re.MULTILINE | re.DOTALL)
    if oi and "State: CLOSED / DELIVERED / VERIFIED" in oi.group(1) and ("D-008" not in control or "D-OI-001" not in control):
        issues.append("OI_RECONCILIATION_STATE_INCOMPLETE")
    return tuple(dict.fromkeys(issues))


def _substantive(value: str) -> bool:
    return value.strip().casefold() not in EMPTY_RATIONALES


def _valid_untracked_manifest(value: str) -> bool:
    if value == "NONE":
        return True
    if value.casefold() in EMPTY_RATIONALES | {"latest", "head", "current candidate", "current branch"}:
        return False
    return bool(value) and all(
        re.fullmatch(r"[A-Za-z0-9_./-]+", path.strip())
        and not path.strip().startswith("/")
        and ".." not in Path(path.strip()).parts
        for path in value.split(",")
    )


def technique_issues(body: str, *, require_closure: bool) -> tuple[str, ...]:
    """Check declaration at Phase 0 and execution/trigger closure at the quality gate."""
    issues: list[str] = []
    for technique in VERIFICATION_TECHNIQUES:
        start = re.search(rf"^[ \t]*{re.escape(technique)}:[ \t]*([^\n]*)$", body, re.MULTILINE | re.IGNORECASE)
        if not start:
            issues.append(f"AEVS_TECHNIQUE_DECISION_MISSING:{technique}")
            continue
        next_technique = re.search(
            r"^[ \t]*(?:" + "|".join(re.escape(item) for item in VERIFICATION_TECHNIQUES) + r"):[ \t]*",
            body[start.end():], re.MULTILINE | re.IGNORECASE,
        )
        detail = body[start.end():start.end() + next_technique.start()] if next_technique else body[start.end():]
        line = re.fullmatch(r"(REQUIRED|CONDITIONAL|NOT_APPLICABLE)[ \t]+—[ \t]*(.*)", start.group(1).strip())
        if not line:
            issues.append(f"AEVS_TECHNIQUE_DECISION_INVALID:{technique}")
            continue
        decision, rationale = line.groups()
        if not _substantive(rationale):
            issues.append(f"AEVS_TECHNIQUE_RATIONALE_MISSING:{technique}")
        values = {match.group(1): match.group(2).strip() for match in re.finditer(
            r"^[ \t]*(Trigger|Resolution|Resolution reason|Execution|Evidence|Authorization reference):[ \t]*([^\n]*)$",
            detail, re.MULTILINE,
        )}
        if decision == "CONDITIONAL":
            if not _substantive(values.get("Trigger", "")):
                issues.append(f"AEVS_TECHNIQUE_TRIGGER_MISSING:{technique}")
            if require_closure:
                resolution = values.get("Resolution", "")
                if resolution not in CONDITIONAL_RESOLUTIONS:
                    issues.append(f"AEVS_TECHNIQUE_RESOLUTION_MISSING_OR_INVALID:{technique}")
                elif resolution == "NOT_TRIGGERED" and not _substantive(values.get("Resolution reason", "")):
                    issues.append(f"AEVS_TECHNIQUE_NOT_TRIGGERED_REASON_MISSING:{technique}")
                elif resolution == "TRIGGERED_EXECUTED" and not _substantive(values.get("Evidence", "")):
                    issues.append(f"AEVS_TECHNIQUE_EXECUTION_EVIDENCE_MISSING:{technique}")
                elif resolution == "REVISED_WITH_AUTHORIZATION" and (
                    not _substantive(values.get("Resolution reason", "")) or
                    not _substantive(values.get("Authorization reference", ""))
                ):
                    issues.append(f"AEVS_TECHNIQUE_REVISION_AUTHORIZATION_MISSING:{technique}")
        elif decision == "REQUIRED" and require_closure:
            if values.get("Execution") != "EXECUTED" or not _substantive(values.get("Evidence", "")):
                issues.append(f"AEVS_TECHNIQUE_REQUIRED_EXECUTION_MISSING:{technique}")
    return tuple(issues)


def active_contract_map_issues(control: str, active_card: str) -> tuple[str, ...]:
    """Validate future active work's Phase 0 AEVS risk map."""
    if active_card == "NONE" or int(active_card[-2:]) < AEVS_ADOPTION_START_CARD_NUMBER:
        return ()
    match = re.search(
        r"^Current active-Card Contract/Risk Map:\s*\n\s*```text\n(.*?)^```",
        control,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return ("AEVS_CONTRACT_RISK_MAP_MISSING",)
    body = match.group(1)
    issues: list[str] = []
    level = re.search(r"^Card Verification Level:\s*(\S+)\s*$", body, re.MULTILINE)
    if not level or level.group(1) not in {"LEVEL_1", "LEVEL_2", "LEVEL_3", "LEVEL_4"}:
        issues.append("AEVS_VERIFICATION_LEVEL_MISSING_OR_INVALID")
    rationale = re.search(r"^Risk rationale:[ \t]*(\S.*)$", body, re.MULTILINE)
    if not rationale or rationale.group(1).strip().lower() in LEARNING_PLACEHOLDERS:
        issues.append("AEVS_RISK_RATIONALE_MISSING")
    invariants = re.search(r"^Invariants affected:[ \t]*(\S.*)$", body, re.MULTILINE)
    if not invariants:
        issues.append("AEVS_AFFECTED_INVARIANTS_MISSING")
    elif invariants.group(1).strip().upper().startswith("NONE"):
        reason = re.fullmatch(r"NONE[ \t]+—[ \t]*(.*)", invariants.group(1).strip(), re.IGNORECASE)
        if not reason or not _substantive(reason.group(1)):
            issues.append("AEVS_AFFECTED_INVARIANTS_REASON_MISSING")
    elif not _substantive(invariants.group(1)):
        issues.append("AEVS_AFFECTED_INVARIANTS_MISSING")
    if not re.search(r"^Verification-technique applicability:\s*$", body, re.MULTILINE):
        issues.append("AEVS_TECHNIQUE_APPLICABILITY_MISSING")
    issues.extend(technique_issues(body, require_closure=False))
    return tuple(issues)


def technique_alignment_issues(control: str, evidence_section: str, active_card: str) -> tuple[str, ...]:
    """Closure cannot silently revise a Phase 0 decision or trigger."""
    if active_card == "NONE" or int(active_card[-2:]) < AEVS_ADOPTION_START_CARD_NUMBER:
        return ()
    contract = re.search(r"^Current active-Card Contract/Risk Map:\s*\n\s*```text\n(.*?)^```", control, re.MULTILINE | re.DOTALL)
    closure = re.search(r"^### Verification Technique Closure\n(.*?)(?=^### |\Z)", evidence_section, re.MULTILINE | re.DOTALL)
    if not contract or not closure:
        return ()  # Dedicated validators own missing records.
    issues: list[str] = []
    technique_pattern = r"^[ \t]*(?:" + "|".join(re.escape(item) for item in VERIFICATION_TECHNIQUES) + r"):[ \t]*"
    for technique in VERIFICATION_TECHNIQUES:
        pattern = rf"^[ \t]*{re.escape(technique)}:[ \t]*(REQUIRED|CONDITIONAL|NOT_APPLICABLE)[ \t]+—[ \t]*"
        declared = re.search(pattern, contract.group(1), re.MULTILINE | re.IGNORECASE)
        closed = re.search(pattern, closure.group(1), re.MULTILINE | re.IGNORECASE)
        if declared and closed and declared.group(1) != closed.group(1):
            issues.append(f"{active_card}:AEVS_TECHNIQUE_DECISION_DRIFT:{technique}")
        if declared and closed and declared.group(1) == closed.group(1) == "CONDITIONAL":
            triggers: list[str] = []
            for source, marker in ((contract.group(1), declared), (closure.group(1), closed)):
                tail = source[marker.end():]
                next_technique = re.search(technique_pattern, tail, re.MULTILINE | re.IGNORECASE)
                detail = tail[:next_technique.start()] if next_technique else tail
                trigger = re.search(r"^[ \t]*Trigger:[ \t]*([^\n]*)$", detail, re.MULTILINE)
                triggers.append(trigger.group(1).strip() if trigger else "")
            if all(triggers) and triggers[0] != triggers[1]:
                issues.append(f"{active_card}:AEVS_TECHNIQUE_TRIGGER_DRIFT:{technique}")
    return tuple(issues)


def independent_audit_issues(evidence_section: str, record: "CardRecord") -> tuple[str, ...]:
    """Allow pre-audit review, but require a bound, resolved audit at completion."""
    if record.state not in {"READY_FOR_HUMAN_REVIEW", "COMPLETE"} or int(record.card_id[-2:]) < AEVS_ADOPTION_START_CARD_NUMBER:
        return ()
    match = re.search(r"^### Independent Audit\n(.*?)(?=^### |\Z)", evidence_section, re.MULTILINE | re.DOTALL)
    if not match:
        return (f"{record.card_id}:INDEPENDENT_AUDIT_RECORD_MISSING",)
    body = match.group(1)
    issues: list[str] = []
    values = {match.group(1): match.group(2).strip() for match in re.finditer(
        r"^[ \t-]*(Status|Candidate Type|Branch|Base SHA|Candidate Commit SHA|Candidate Diff SHA-256|Untracked Files|Verifier context|Canonical inputs reviewed|Evidence reviewed|Findings|Unresolved blockers|Gap dispositions|Limitations|Verdict):[ \t]*([^\n]*)$",
        body, re.MULTILINE,
    )}
    status = values.get("Status", "")
    if status not in INDEPENDENT_AUDIT_STATES:
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_STATUS_INVALID")
    elif record.state == "COMPLETE" and status in {"NOT_RUN", "BLOCKED"}:
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_NOT_COMPLETE")
    kind = values.get("Candidate Type", "")
    if kind not in {"COMMIT", "WORKTREE"}:
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_CANDIDATE_TYPE_INVALID")
    if not MAINTENANCE_BRANCH.fullmatch(values.get("Branch", "")) and not re.fullmatch(r"card/v1-c\d{2}-[a-z0-9-]+", values.get("Branch", "")):
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_BRANCH_INVALID")
    if not FULL_GIT_SHA.fullmatch(values.get("Base SHA", "")):
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_BASE_SHA_INVALID")
    if kind == "COMMIT":
        if not FULL_GIT_SHA.fullmatch(values.get("Candidate Commit SHA", "")):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_COMMIT_SHA_INVALID")
        if values.get("Candidate Diff SHA-256") or values.get("Untracked Files"):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_CANDIDATE_SCHEMA_AMBIGUOUS")
    if kind == "WORKTREE":
        if values.get("Candidate Commit SHA"):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_CANDIDATE_SCHEMA_AMBIGUOUS")
        if not SHA256.fullmatch(values.get("Candidate Diff SHA-256", "")):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_DIFF_SHA256_INVALID")
        untracked = values.get("Untracked Files", "")
        if not _valid_untracked_manifest(untracked):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_UNTRACKED_FILES_INVALID")
    if status == "NOT_RUN" and record.state == "READY_FOR_HUMAN_REVIEW":
        return tuple(issues)
    for field in ("Verifier context", "Canonical inputs reviewed", "Evidence reviewed", "Findings", "Unresolved blockers", "Verdict"):
        if not _substantive(values.get(field, "")) and not (field in {"Findings", "Unresolved blockers"} and values.get(field) == "NONE"):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_FIELD_MISSING:{field}")
    if status in {"PASS", "PASS_WITH_GAPS"} and values.get("Unresolved blockers") != "NONE":
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_BLOCKER_PRESENT")
    if status == "PASS_WITH_GAPS":
        if values.get("Findings") == "NONE":
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_GAP_FINDINGS_MISSING")
        gaps = values.get("Gap dispositions", "")
        if not gaps or gaps == "NONE" or not all(
            (entry := re.fullmatch(r"(ACCEPTED|DEFERRED|NON_BLOCKING)[ \t]+—[ \t]*(.*)", item.strip())) and _substantive(entry.group(2))
            for item in gaps.split(";")
        ):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_GAP_DISPOSITION_MISSING")
        if not _substantive(values.get("Limitations", "")):
            issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_LIMITATIONS_MISSING")
    return tuple(issues)


def _normalize_audit_recording(path: str, content: bytes) -> bytes:
    """Ignore only values in designated audit-result records, never their structure."""
    if path != "TRAID_CARD_EVIDENCE_MAP.md":
        return content
    prefix = b"FILE\0" if content.startswith(b"FILE\0") else b""
    content = content[len(prefix):]
    text = content.decode("utf-8")
    lines = text.splitlines(keepends=True)
    owner = ""
    recording = False
    for index, line in enumerate(lines):
        if line.startswith("# "):
            owner = ""
            recording = False
        elif line.startswith("## "):
            owner = line.strip()
            recording = False
        elif line.startswith("### "):
            heading = line.strip()
            recording = (
                heading == "### Independent Audit" and re.match(r"## V1-C\d{2} ", owner) is not None
            ) or (heading == "### Current Maintenance Re-Audit Record" and owner.startswith("## 25. AEVS"))
        if recording:
            for field in AUDIT_RECONCILIATION_FIELDS:
                lines[index] = re.sub(
                    rf"^([ \t-]*{re.escape(field)}:[ \t]*)[^\n]*",
                    r"\g<1><audit-result>", lines[index],
                )
    return prefix + "".join(lines).encode("utf-8")


def _hash_part(digest: "hashlib._Hash", label: bytes, value: bytes) -> None:
    digest.update(len(label).to_bytes(8, "big") + label + len(value).to_bytes(8, "big") + value)


def worktree_candidate_identity(repo: Path, base_sha: str) -> dict[str, str]:
    """Bind branch/base, effective tracked content, divergent index content, and untracked files."""
    if not FULL_GIT_SHA.fullmatch(base_sha):
        raise ValueError("CANDIDATE_BASE_SHA_INVALID")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    tracked = sorted(path.decode() for path in subprocess.check_output(["git", "ls-files", "-z"], cwd=repo).split(b"\0") if path)
    untracked = sorted(path.decode() for path in subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=repo).split(b"\0") if path)
    digest = hashlib.sha256()
    _hash_part(digest, b"schema", b"TraID frozen worktree v1")
    _hash_part(digest, b"branch", branch.encode())
    _hash_part(digest, b"base", base_sha.encode())
    for path in sorted(set(tracked) | set(untracked)):
        target = repo / path
        if target.is_symlink():
            worktree = b"SYMLINK\0" + os.readlink(target).encode()
            worktree_mode = b"120000"
        elif target.exists():
            worktree = b"FILE\0" + target.read_bytes()
            worktree_mode = b"100755" if os.lstat(target).st_mode & 0o111 else b"100644"
        else:
            worktree = b"DELETED"
            worktree_mode = b"000000"
        worktree = _normalize_audit_recording(path, worktree) if path == "TRAID_CARD_EVIDENCE_MAP.md" and worktree.startswith(b"FILE\0") else worktree
        index = subprocess.run(["git", "show", f":{path}"], cwd=repo, capture_output=True, check=False)
        if index.returncode == 0:
            staged = b"FILE\0" + index.stdout
            staged = _normalize_audit_recording(path, staged) if path == "TRAID_CARD_EVIDENCE_MAP.md" else staged
            stage_row = subprocess.check_output(["git", "ls-files", "--stage", "--", path], cwd=repo).splitlines()
            index_mode = stage_row[0].split(b" ", 1)[0] if stage_row else b"000000"
        else:
            staged = b"DELETED"
            index_mode = b"000000"
        _hash_part(digest, b"tracked path", path.encode())
        _hash_part(digest, b"worktree", worktree)
        _hash_part(digest, b"worktree mode", worktree_mode)
        if staged != worktree or index_mode != worktree_mode:
            base = subprocess.run(["git", "show", f"{base_sha}:{path}"], cwd=repo, capture_output=True, check=False)
            baseline = b"FILE\0" + base.stdout if base.returncode == 0 else b"DELETED"
            baseline = _normalize_audit_recording(path, baseline) if path == "TRAID_CARD_EVIDENCE_MAP.md" and base.returncode == 0 else baseline
            base_row = subprocess.check_output(["git", "ls-tree", base_sha, "--", path], cwd=repo).splitlines()
            base_mode = base_row[0].split(b" ", 1)[0] if base_row else b"000000"
            if staged != baseline or index_mode != base_mode:
                _hash_part(digest, b"divergent index", staged)
                _hash_part(digest, b"divergent index mode", index_mode)
    return {"Candidate Type": "WORKTREE", "Branch": branch, "Base SHA": base_sha,
            "Candidate Diff SHA-256": digest.hexdigest(), "Untracked Files": ", ".join(untracked) if untracked else "NONE"}


def candidate_applicability_issues(recorded: dict[str, str], actual: dict[str, str]) -> tuple[str, ...]:
    """Only an identical normalized candidate retains a worktree audit verdict."""
    return tuple(f"AUDITED_CANDIDATE_CHANGED:{field}" for field in ("Branch", "Base SHA", "Candidate Diff SHA-256") if recorded.get(field) != actual[field])


def active_card_candidate_issues(evidence: str, record: CardRecord | None, repo: Path, branch: str) -> tuple[str, ...]:
    """A review-ready Card's audit must still name the candidate on disk."""
    if record is None or record.state != "READY_FOR_HUMAN_REVIEW" or int(record.card_id[-2:]) < AEVS_ADOPTION_START_CARD_NUMBER:
        return ()
    section = card_evidence_section(evidence, record.card_id)
    match = re.search(r"^### Independent Audit\n(.*?)(?=^### |\Z)", section, re.MULTILINE | re.DOTALL)
    if not match:
        return ()  # The audit record validator owns the missing-record error.
    values = {key: value.strip() for key, value in re.findall(
        r"^[ \t-]*(Candidate Type|Branch|Base SHA|Candidate Commit SHA|Candidate Diff SHA-256|Untracked Files):[ \t]*([^\n]*)$",
        match.group(1), re.MULTILINE,
    )}
    if values.get("Branch") != branch:
        return (f"{record.card_id}:AUDITED_CANDIDATE_BRANCH_MISMATCH",)
    if values.get("Candidate Type") == "WORKTREE" and FULL_GIT_SHA.fullmatch(values.get("Base SHA", "")) and SHA256.fullmatch(values.get("Candidate Diff SHA-256", "")):
        actual = worktree_candidate_identity(repo, values["Base SHA"])
        return tuple(f"{record.card_id}:{issue}" for issue in candidate_applicability_issues(values, actual))
    if values.get("Candidate Type") == "COMMIT" and FULL_GIT_SHA.fullmatch(values.get("Candidate Commit SHA", "")):
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        if head != values["Candidate Commit SHA"]:
            return (f"{record.card_id}:AUDITED_CANDIDATE_COMMIT_MISMATCH",)
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, text=True)
        if any(line[3:] != "TRAID_CARD_EVIDENCE_MAP.md" for line in dirty.splitlines() if line):
            return (f"{record.card_id}:AUDITED_COMMIT_HAS_MATERIAL_WORKTREE_CHANGE",)
        if dirty:
            baseline = subprocess.check_output(["git", "show", "HEAD:TRAID_CARD_EVIDENCE_MAP.md"], cwd=repo)
            current = (repo / "TRAID_CARD_EVIDENCE_MAP.md").read_bytes()
            index = subprocess.check_output(["git", "show", ":TRAID_CARD_EVIDENCE_MAP.md"], cwd=repo)
            if not (_normalize_audit_recording("TRAID_CARD_EVIDENCE_MAP.md", baseline)
                    == _normalize_audit_recording("TRAID_CARD_EVIDENCE_MAP.md", current)
                    == _normalize_audit_recording("TRAID_CARD_EVIDENCE_MAP.md", index)):
                return (f"{record.card_id}:AUDITED_COMMIT_HAS_MATERIAL_WORKTREE_CHANGE",)
    return ()


def _maintenance_audit_records(evidence: str) -> tuple[tuple[str, str], ...]:
    """Return explicitly classified maintenance audit records and their bodies."""
    pattern = re.compile(r"^### (Current|Historical) Maintenance Re-Audit Record\n(.*?)(?=^# |^## |^### |\Z)", re.MULTILINE | re.DOTALL)
    return tuple((match.group(1).upper(), match.group(2)) for match in pattern.finditer(evidence))


def maintenance_audit_record_lifecycle_issues(control: str, evidence: str, branch: str) -> tuple[str, ...]:
    """Enforce CURRENT/HISTORICAL classification without binding history to live Git."""
    maintenance = _maintenance_record(control)
    task = re.search(r"^Maintenance Task ID:[ \t]*([^\n]+)$", maintenance, re.MULTILINE)
    task_id = task.group(1).strip() if task else ""
    status_match = re.search(r"^Status:[ \t]*([^\n]+)$", maintenance, re.MULTILINE)
    maintenance_status = status_match.group(1).split(" —", 1)[0].strip() if status_match else ""
    records = _maintenance_audit_records(evidence)
    current = [body for classification, body in records if classification == "CURRENT"]
    issues: list[str] = []
    if len(current) > 1:
        issues.append("MAINTENANCE_MULTIPLE_CURRENT_AUDIT_RECORDS")
    for classification, body in records:
        declared = re.search(r"^Record Classification:[ \t]*([^\n]+)$", body, re.MULTILINE)
        if not declared or declared.group(1).strip() != classification:
            issues.append("MAINTENANCE_AUDIT_RECORD_CLASSIFICATION_INVALID")
            continue
        record_task = re.search(r"^Maintenance Task ID:[ \t]*([^\n]+)$", body, re.MULTILINE)
        if not record_task or not record_task.group(1).strip():
            issues.append("MAINTENANCE_AUDIT_TASK_ID_MISSING")
            continue
        if classification == "CURRENT":
            if maintenance_status in MAINTENANCE_POST_MERGE_STAGES:
                issues.append("MAINTENANCE_AUDIT_RECORD_NOT_RETIRED_AFTER_DELIVERY")
            record_branch = re.search(r"^Branch:[ \t]*([^\n]+)$", body, re.MULTILINE)
            if record_branch and record_branch.group(1).strip() != branch:
                issues.append("MAINTENANCE_CANDIDATE_BRANCH_MISMATCH")
            if task_id and record_task.group(1).strip() != task_id:
                issues.append("MAINTENANCE_AUDIT_TASK_ID_MISMATCH")
    return tuple(dict.fromkeys(issues))


def current_maintenance_candidate_issues(
    evidence: str,
    branch: str,
    repo: Path,
    maintenance_task_id: str | None = None,
) -> tuple[str, ...]:
    """Check that the active maintenance's current audit record binds this worktree."""
    records = _maintenance_audit_records(evidence)
    current_records = [body for classification, body in records if classification == "CURRENT"]
    if len(current_records) > 1:
        return ("MAINTENANCE_MULTIPLE_CURRENT_AUDIT_RECORDS",)
    if not current_records:
        return ()
    body = current_records[0]
    classification = re.search(r"^Record Classification:[ \t]*([^\n]+)$", body, re.MULTILINE)
    if not classification or classification.group(1).strip() != "CURRENT":
        return ("MAINTENANCE_AUDIT_RECORD_CLASSIFICATION_INVALID",)
    values = {key: value.strip() for key, value in re.findall(
        r"^(Maintenance Task ID|Candidate Type|Branch|Base SHA|Candidate Diff SHA-256|Untracked Files):[ \t]*([^\n]*)$",
        body, re.MULTILINE,
    )}
    if maintenance_task_id and values.get("Maintenance Task ID") != maintenance_task_id:
        return ("MAINTENANCE_AUDIT_TASK_ID_MISMATCH",)
    issues: list[str] = []
    if values.get("Candidate Type") != "WORKTREE":
        issues.append("MAINTENANCE_CANDIDATE_TYPE_INVALID")
    if values.get("Branch") != branch:
        issues.append("MAINTENANCE_CANDIDATE_BRANCH_MISMATCH")
    if not FULL_GIT_SHA.fullmatch(values.get("Base SHA", "")):
        issues.append("MAINTENANCE_CANDIDATE_BASE_INVALID")
    if not SHA256.fullmatch(values.get("Candidate Diff SHA-256", "")):
        issues.append("MAINTENANCE_CANDIDATE_DIFF_INVALID")
    if not _valid_untracked_manifest(values.get("Untracked Files", "")):
        issues.append("MAINTENANCE_CANDIDATE_UNTRACKED_INVALID")
    if issues:
        return tuple(issues)
    actual = worktree_candidate_identity(repo, values["Base SHA"])
    issues.extend(candidate_applicability_issues(values, actual))
    audit_status = re.search(r"^Status:[ \t]*([^\n]+)$", body, re.MULTILINE)
    if values["Untracked Files"] != actual["Untracked Files"] and audit_status and audit_status.group(1) == "NOT_RUN":
        issues.append("MAINTENANCE_CANDIDATE_UNTRACKED_MISMATCH")
    elif values["Untracked Files"] != actual["Untracked Files"]:
        # The manifest is the freeze-time list. Staging identical files later
        # changes Git representation but not the content-bound digest.
        if values["Candidate Diff SHA-256"] != actual["Candidate Diff SHA-256"]:
            issues.append("MAINTENANCE_CANDIDATE_UNTRACKED_MISMATCH")
    return tuple(issues)


def maintenance_delivery_audit_issues(control: str, evidence: str) -> tuple[str, ...]:
    """Maintenance may reach delivery stages only after its current audit resolves."""
    record = _maintenance_record(control)
    status_match = re.search(r"^Status:[ \t]*([^\n]+)$", record, re.MULTILINE)
    maintenance_status = status_match.group(1).split(" —", 1)[0].strip() if status_match else ""
    task_match = re.search(r"^Maintenance Task ID:[ \t]*([^\n]+)$", record, re.MULTILINE)
    task_id = task_match.group(1).strip() if task_match else ""
    records = _maintenance_audit_records(evidence)
    current_records = [body for classification, body in records if classification == "CURRENT"]
    if len(current_records) > 1:
        return ("MAINTENANCE_MULTIPLE_CURRENT_AUDIT_RECORDS",)
    audit_body = current_records[0] if current_records else ""
    matching_task = lambda body: bool(task_id and re.search(
        rf"^Maintenance Task ID:[ \t]*{re.escape(task_id)}[ \t]*$", body, re.MULTILINE
    ))
    historical_post_merge = False
    if not audit_body or not matching_task(audit_body):
        historical = [body for classification, body in records if classification == "HISTORICAL" and matching_task(body)]
        if maintenance_status in MAINTENANCE_POST_MERGE_STAGES and len(historical) == 1:
            audit_body = historical[0]
            historical_post_merge = True
        elif maintenance_status in MAINTENANCE_AUDIT_REQUIRED_STAGES:
            return ("MAINTENANCE_CURRENT_AUDIT_RECORD_MISSING",)
        else:
            return ()
    classification = re.search(r"^Record Classification:[ \t]*([^\n]+)$", audit_body, re.MULTILINE)
    expected_classification = "HISTORICAL" if historical_post_merge else "CURRENT"
    if not classification or classification.group(1).strip() != expected_classification:
        return ("MAINTENANCE_AUDIT_RECORD_CLASSIFICATION_INVALID",)
    values = {key: value.strip() for key, value in re.findall(
        r"^(Status|Verifier context|Canonical inputs reviewed|Evidence reviewed|Findings|Unresolved blockers|Gap dispositions|Limitations|Verdict):[ \t]*([^\n]*)$",
        audit_body, re.MULTILINE,
    )}
    if maintenance_status in {"IN_PROGRESS", "READY_FOR_HUMAN_REVIEW"}:
        return () if values.get("Status") in INDEPENDENT_AUDIT_STATES else ("MAINTENANCE_AUDIT_STATUS_INVALID",)
    if maintenance_status not in MAINTENANCE_STATUSES:
        return ()  # The maintenance status validator owns this failure.
    issues: list[str] = []
    if values.get("Status") not in {"PASS", "PASS_WITH_GAPS"}:
        issues.append("MAINTENANCE_DELIVERY_WITHOUT_RESOLVED_AUDIT")
    if values.get("Unresolved blockers") != "NONE":
        issues.append("MAINTENANCE_AUDIT_BLOCKER_PRESENT")
    if not _substantive(values.get("Verdict", "")):
        issues.append("MAINTENANCE_AUDIT_VERDICT_MISSING")
    for field in ("Verifier context", "Canonical inputs reviewed", "Evidence reviewed", "Findings"):
        if not _substantive(values.get(field, "")) and not (field == "Findings" and values.get(field) == "NONE"):
            issues.append(f"MAINTENANCE_AUDIT_FIELD_MISSING:{field}")
    if values.get("Status") == "PASS_WITH_GAPS":
        gaps = values.get("Gap dispositions", "")
        if values.get("Findings") == "NONE" or not gaps or not all(
            (entry := re.fullmatch(r"(ACCEPTED|DEFERRED|NON_BLOCKING)[ \t]+—[ \t]*(.*)", item.strip())) and _substantive(entry.group(2))
            for item in gaps.split(";")
        ):
            issues.append("MAINTENANCE_AUDIT_GAPS_UNCLASSIFIED")
        if not _substantive(values.get("Limitations", "")):
            issues.append("MAINTENANCE_AUDIT_LIMITATIONS_MISSING")
    return tuple(issues)


def maintenance_consistency_issues(
    control: str,
    branch: str,
    head: str,
    changed_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Validate the generic, record-backed maintenance/hotfix contract."""

    if not (branch.startswith("maintenance/") or branch.startswith("hotfix/")):
        return ()
    issues: list[str] = []
    if not MAINTENANCE_BRANCH.fullmatch(branch):
        issues.append("MAINTENANCE_BRANCH_NAME_INVALID")
    record = _maintenance_record(control)
    values = {
        key: match.group(1).strip()
        for key in MAINTENANCE_FIELDS
        if (match := re.search(rf"^{re.escape(key)}:\s*(.+)$", record, re.MULTILINE))
    }
    missing = [field for field in MAINTENANCE_FIELDS if not values.get(field)]
    if missing:
        issues.append(f"MAINTENANCE_RECORD_MISSING:{','.join(missing)}")
        return tuple(issues)
    if values["Branch"] != branch:
        issues.append("MAINTENANCE_BRANCH_AUTHORIZATION_MISMATCH")
    status = values["Status"].split(" —", 1)[0].strip()
    if status not in MAINTENANCE_STATUSES:
        issues.append("MAINTENANCE_STATUS_INVALID")
    base = values["Base Commit"].split(" —", 1)[0].strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", base):
        issues.append("MAINTENANCE_BASE_INVALID")
    else:
        ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", base, head], check=False)
        if ancestry.returncode != 0:
            issues.append("MAINTENANCE_BASE_NOT_ANCESTOR")
    allowed = {path.strip().lstrip("./") for path in values["Allowed Paths"].split(",") if path.strip()}
    unexpected = sorted(path for path in changed_paths if path.lstrip("./") not in allowed)
    if unexpected:
        issues.append(f"MAINTENANCE_OUT_OF_SCOPE:{','.join(unexpected)}")
    return tuple(dict.fromkeys(issues))


def resolve_card_state(control: str) -> ResolvedState:
    errors: list[str] = []
    try:
        cards = parse_card_table(control)
        titles = {record.card_id: record.title for record in cards}
    except ValueError as exc:
        return ResolvedState((), "", "", "", "", False, False, False, False, (str(exc),))

    active_values = _line_values(r"^Active Card:\s*(.+)$", control)
    active_state_values = _line_values(r"^Active Card State:\s*(.+)$", control)
    next_values = _line_values(r"^Next Roadmap Card:\s*(.+)$", control)
    next_auth_values = _line_values(r"^Next Card Authorized:\s*(.+)$", control)
    try:
        active_ids = tuple(normalize_card_identity(value, titles) for value in active_values)
        next_ids = tuple(normalize_card_identity(value.split(" — available", 1)[0], titles) for value in next_values)
    except ValueError as exc:
        errors.append(str(exc))
        active_ids, next_ids = (), ()

    active_card = active_ids[0] if active_ids and len(set(active_ids)) == 1 else ""
    if not active_ids or len(set(active_ids)) != 1:
        errors.append("ACTIVE_CARD_DECLARATIONS_CONFLICT" if active_ids else "ACTIVE_CARD_MISSING")
    if next_ids and len(set(next_ids)) != 1:
        errors.append("NEXT_CARD_DECLARATIONS_CONFLICT")
    declared_next = next_ids[0] if next_ids and len(set(next_ids)) == 1 else ""

    records = {record.card_id: record for record in cards}
    active_state = records[active_card].state if active_card in records else ""
    if active_card != "NONE":
        if not active_state_values or len(set(active_state_values)) != 1:
            errors.append("ACTIVE_CARD_STATE_DECLARATION_MISSING_OR_CONFLICTING")
        elif active_state_values[0].split(" —", 1)[0].strip() != active_state:
            errors.append("ACTIVE_CARD_STATE_MISMATCH")
    if active_card not in ("", "NONE") and active_state not in ACTIVE_STATES:
        errors.append("ACTIVE_CARD_STATE_INVALID")

    if active_card == "NONE":
        active_count = sum(record.state in ACTIVE_STATES for record in cards)
        if active_count:
            errors.append("ACTIVE_CARD_NONE_WITH_ACTIVE_STATE")
    else:
        active_count = sum(record.state in ACTIVE_STATES for record in cards)
        if active_count != 1:
            errors.append("MULTIPLE_ACTIVE_CARDS" if active_count > 1 else "ACTIVE_CARD_ROW_MISSING")

    active_record = records.get(active_card)
    auth_lines = {match.group(1): match.group(2) for match in re.finditer(r"^(V1-C\d{2}) Authorization:\s*(.+)$", control, re.MULTILINE)}
    active_block = re.search(r"^## 6\. Active Card Record\n(.*?)(?=^## 7\.)", control, re.MULTILINE | re.DOTALL)
    active_block_text = active_block.group(1) if active_block else ""
    active_record_state_values = _line_values(r"^State:\s*(.+)$", active_block_text)
    current_record_block = re.search(
        r"^Current active-Card record:\s*\n\s*```text\n(.*?)(?=^```)",
        control,
        re.MULTILINE | re.DOTALL,
    )
    if current_record_block:
        active_record_state_values = _line_values(r"^State:\s*(.+)$", current_record_block.group(1))
    if active_card != "NONE" and active_record_state_values:
        active_record_states = {
            value.split(" —", 1)[0].strip() for value in active_record_state_values
        }
        if len(active_record_states) != 1 or next(iter(active_record_states)) != active_state:
            errors.append("ACTIVE_CARD_RECORD_STATE_MISMATCH")
    start_values = _line_values(r"^Human Start Approval:\s*(.+)$", active_block_text)
    active_start = bool(active_record and active_record.start_approved)
    if active_record and start_values:
        active_start = active_start and start_values[-1].startswith("GRANTED")
    if active_card in auth_lines:
        active_start = active_start and "START_GRANTED" in auth_lines[active_card]
    if active_card != "NONE" and not active_start:
        errors.append("ACTIVE_CARD_START_APPROVAL_MISSING")

    delivery_values = _line_values(r"^Human Delivery Approval:\s*(.+)$", active_block_text)
    verified_values = _line_values(r"^Delivery Verified:\s*(.+)$", active_block_text)
    approval = bool(delivery_values and delivery_values[-1].startswith("GRANTED"))
    verified = bool(verified_values and verified_values[-1].startswith("YES"))
    if active_card == "NONE":
        complete_id = next((record.card_id for record in cards if record.state == "COMPLETE"), "")
        completion = auth_lines.get(complete_id, "")
        approval = "DELIVERY_GRANTED" in completion or "DELIVERY_COMPLETED" in completion
        verified = "DELIVERY_COMPLETED" in completion

    active_index = next((index for index, record in enumerate(cards) if record.card_id == active_card), -1)
    if active_card == "NONE":
        next_record = next((record for record in cards if record.state != "COMPLETE"), None)
    else:
        next_record = cards[active_index + 1] if active_index >= 0 and active_index + 1 < len(cards) else None
    derived_next = next_record.card_id if next_record else "NONE"
    if declared_next != derived_next:
        errors.append("NEXT_ROADMAP_CARD_MISMATCH")
    if declared_next == active_card and active_card != "NONE":
        errors.append("NEXT_CARD_EQUALS_ACTIVE_CARD")
    if next_record and next_record.start_approved and next_record.card_id != active_card:
        errors.append("NEXT_CARD_AUTHORIZATION_PRESENT")
    if any(record.start_approved and record.card_id != active_card and record.state == "NOT_STARTED" for record in cards):
        errors.append("FUTURE_CARD_AUTHORIZATION_PRESENT")
    if next_auth_values and any(value.startswith("YES") for value in next_auth_values):
        errors.append("NEXT_CARD_AUTHORIZATION_PRESENT")
    if active_card == "NONE" and not approval:
        errors.append("COMPLETE_WITHOUT_DELIVERY_PROOF")
    if active_card == "NONE" and not verified:
        errors.append("COMPLETE_WITHOUT_DELIVERY_VERIFICATION")

    return ResolvedState(tuple(cards), active_card, active_state, declared_next, derived_next, active_start, approval, verified, not errors, tuple(dict.fromkeys(errors)))


def main() -> int:
    control = Path("PROJECT_CONTROL.md").read_text()
    evidence = Path("TRAID_CARD_EVIDENCE_MAP.md").read_text()
    state = resolve_card_state(control)
    if state.errors:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(state.errors)}")
        return 1

    required_fields = {
        "Git Branch": re.search(r"^Git Branch:\s*.+$", control, re.MULTILINE),
        "Git Checkpoint": re.search(r"^Git Checkpoint:\s*[0-9a-f]+", control, re.MULTILINE),
        "Working Tree": re.search(r"^Working Tree:\s*.+$", control, re.MULTILINE),
        "CARD_QUALITY_GATE": re.search(r"^CARD_QUALITY_GATE:\s*(PASS|BLOCKED|NOT_RUN)$", control, re.MULTILINE),
    }
    missing_fields = tuple(name for name, match in required_fields.items() if match is None)
    if missing_fields:
        print(f"HARNESS_CONSISTENCY: BLOCKED: MISSING_REQUIRED_LIFECYCLE_FIELD:{','.join(missing_fields)}")
        return 1

    active_card = state.active_card
    current_card_id = active_card if active_card != "NONE" else next((record.card_id for record in state.cards if record.state == "COMPLETE"), "")
    current_record = next((record for record in state.cards if record.card_id == current_card_id), None)
    evidence_section = re.search(rf"## {re.escape(current_card_id)} .*?(?=\n## V1-C\d{{2}} |\Z)", evidence, re.DOTALL)
    evidence_current = evidence_section.group(0) if evidence_section else ""
    evidence_state = re.search(r"^\*\*Status:\*\* (.+)$", evidence_current, re.MULTILINE)
    evidence_state_value = evidence_state.group(1).split(" —", 1)[0].strip() if evidence_state else ""
    quality = re.search(r"^Status: (PASS|BLOCKED)$", evidence_current, re.MULTILINE)
    control_quality = re.search(r"^CARD_QUALITY_GATE: (PASS|BLOCKED|NOT_RUN)", control, re.MULTILINE)
    test_state = re.search(r"^TraID repository test state: (.+)$", control, re.MULTILINE)
    expected_branch = re.search(r"^Git Branch: (.+)$", control, re.MULTILINE)
    expected_head = re.search(r"^Git Checkpoint: ([0-9a-f]+)", control, re.MULTILINE)
    expected_tree = re.search(r"^Working Tree: (.+)$", control, re.MULTILINE)
    safe_resume = re.search(r"^## 34\. Current Safe Resume Point\n(.*?)(?=^## 35\.)", control, re.MULTILINE | re.DOTALL)
    safe_resume_text = safe_resume.group(1) if safe_resume else ""
    safe_resume_valid = bool(
        safe_resume
        and f"Active Card is {active_card}" in safe_resume_text
        and f"Next Roadmap Card: {state.derived_next_card}" in safe_resume_text
    )
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    changed_paths = tuple(
        line[3:] if len(line) > 3 else line
        for line in subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], text=True).splitlines()
        if line
    )
    maintenance_issues = maintenance_consistency_issues(control, branch, head, changed_paths)
    maintenance_record = _maintenance_record(control)
    task_match = re.search(r"^Maintenance Task ID:[ \t]*([^\n]+)$", maintenance_record, re.MULTILINE)
    maintenance_task_id = task_match.group(1).strip() if task_match else None
    maintenance_issues += maintenance_audit_record_lifecycle_issues(control, evidence, branch)
    maintenance_issues += current_maintenance_candidate_issues(evidence, branch, Path.cwd(), maintenance_task_id)
    maintenance_issues += maintenance_delivery_audit_issues(control, evidence)
    if maintenance_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(maintenance_issues)}")
        return 1
    current_issues = current_state_issues(control, evidence, head)
    if current_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(current_issues)}")
        return 1
    contract_map_issues = active_contract_map_issues(control, state.active_card)
    if contract_map_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(contract_map_issues)}")
        return 1
    checkpoint = bool(expected_head and subprocess.run(["git", "cat-file", "-e", f"{expected_head.group(1)}^{{commit}}"], check=False).returncode == 0 and subprocess.run(["git", "merge-base", "--is-ancestor", expected_head.group(1), head], check=False).returncode == 0)
    clean = not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    documentation_issues = tuple(
        issue for record in state.cards for issue in card_documentation_issues(evidence, record)
    )
    documentation_issues += active_card_candidate_issues(evidence, current_record if active_card != "NONE" else None, Path.cwd(), branch)
    if active_card != "NONE":
        documentation_issues += technique_alignment_issues(control, card_evidence_section(evidence, active_card), active_card)
    if active_card != "NONE" and state.delivery_approval and current_record and int(current_card_id[-2:]) >= AEVS_ADOPTION_START_CARD_NUMBER:
        documentation_issues += independent_audit_issues(
            card_evidence_section(evidence, current_card_id),
            CardRecord(current_card_id, current_record.title, "COMPLETE", True),
        )
    learning_issues = [issue for issue in documentation_issues if ":LEARNING_" in issue or "CARD_EVIDENCE_SECTION_MISSING" in issue]
    evidence_issues = [issue for issue in documentation_issues if issue not in learning_issues]
    complete = current_record is not None and current_record.state == "COMPLETE"
    facts = LifecycleFacts(
        card_id=current_card_id, card_state=current_record.state if current_record else "", active_card=active_card,
        quality_gate=quality.group(1) if quality else "", delivery_approval=state.delivery_approval,
        delivery_verified=state.delivery_verified, project_control_state=current_record.state if current_record else "",
        evidence_state=evidence_state_value, expected_branch=expected_branch.group(1).strip() if expected_branch else "",
        actual_branch=branch, expected_head=expected_head.group(1) if expected_head else "", actual_head=head,
        head_checkpoint_verified=checkpoint, test_state_verified=bool(test_state and test_state.group(1).startswith("VERIFIED")),
        quality_gate_state=control_quality.group(1) if control_quality else "", evidence_status=evidence_state_value,
        learning_status="COMPLETE" if complete else "", safe_resume_valid=safe_resume_valid, delivery_recorded=state.delivery_verified,
        evidence_delivery_recorded=state.delivery_verified if complete else True, learning_record_complete=not learning_issues,
        stale_completion_rationale="implementation has not started under this redesigned Evidence Map" in evidence,
        expected_working_tree_clean=bool(expected_tree and not expected_tree.group(1).startswith("DIRTY_ALLOWED")),
        actual_working_tree_clean=clean, active_card_exists=active_card == "NONE" or current_record is not None,
        active_card_start_authorized=state.active_start_authorized,
        active_card_state_valid=active_card == "NONE" or (current_record is not None and current_record.state in ACTIVE_STATES),
        current_state_unambiguous=state.current_state_unambiguous,
        active_execution_count=sum(record.state in ACTIVE_STATES for record in state.cards),
        declared_next_card=state.declared_next_card, derived_next_card=state.derived_next_card,
    )
    result = evaluate_state_consistency(facts)
    if result.passed and not documentation_issues:
        print("HARNESS_CONSISTENCY: PASS")
        return 0
    reasons = list(result.reason_codes) + list(documentation_issues)
    print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(dict.fromkeys(reasons))}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
