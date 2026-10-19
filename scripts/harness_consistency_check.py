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
    statuses = _line_values(r"^\*\*Status:\*\*[ \t]*(.+)$", section)
    if len(statuses) != 1 or statuses[0].split(" —", 1)[0].strip() != record.state:
        issues.append(f"{record.card_id}:PROJECT_CONTROL_EVIDENCE_STATE_MISMATCH")
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
    if record.state == "COMPLETE" and int(record.card_id[-2:]) >= 7:
        receipts = re.findall(r"^### Delivery Verification\n(.*?)(?=^### |\Z)", section, re.M | re.S)
        fields = dict(re.findall(r"^([^:\n]+): ([^\n]+)$", receipts[0], re.M)) if len(receipts) == 1 else {}
        audit = re.search(r"^### Independent Audit\n(.*?)(?=^### |\Z)", section, re.M | re.S)
        audit_fields = dict(re.findall(r"^[ \t-]*([^:\n]+):[ \t]*([^\n]*)$", audit.group(1), re.M)) if audit else {}
        valid = (fields.get("State") == "POST_MERGE_VERIFIED"
                 and fields.get("Audit Digest") == audit_fields.get("Candidate Diff SHA-256")
                 and fields.get("Source Branch") == audit_fields.get("Branch")
                 and fields.get("Base SHA") == audit_fields.get("Base SHA")
                 and all(FULL_GIT_SHA.fullmatch(fields.get(k, "")) for k in ("Source Commit", "Merge Anchor", "Validated Main"))
                 and re.fullmatch(r"[1-9][0-9]*", fields.get("Hosted Run", ""))
                 and _substantive(fields.get("Local Validation Evidence", ""))
                 and fields.get("Closure Approval", "").startswith("GRANTED — "))
        if not valid:
            issues.append(f"{record.card_id}:DELIVERY_VERIFICATION_RECEIPT_MISSING_OR_INVALID")
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
    records = tuple(CardRecord(card_id, title, state, approved == "YES") for card_id, title, state, approved in CARD_ROW.findall(control_section(control, "30. V1 Card Status Table")))
    expected = tuple(f"V1-C{i:02d}" for i in range(1, 28))
    if len(records) != 27 or tuple(record.card_id for record in records) != expected:
        raise ValueError("CARD_ORDER_OR_COUNT_INVALID")
    if any(record.state not in CARD_STATES for record in records):
        raise ValueError("CARD_STATE_INVALID")
    return records


def _line_values(pattern: str, text: str) -> tuple[str, ...]:
    return tuple(match.group(1).strip() for match in re.finditer(pattern, text, re.MULTILINE))


def control_section(control: str, heading: str) -> str:
    """Read one designated operational section; history is never a fallback."""
    matches = re.findall(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", control, re.MULTILINE | re.DOTALL)
    return matches[0] if len(matches) == 1 else ""


def completed_card_ids(control: str) -> tuple[str, ...]:
    return tuple(record.card_id for record in parse_card_table(control) if record.state == "COMPLETE")


def _maintenance_record(control: str) -> str:
    match = re.search(r"^### Current Maintenance Record\n(.*?)(?=^---$|^## \d+\.)", control, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def _current_repository_section(control: str) -> str:
    section = control_section(control, "4. Repository / Git Reality")
    return re.split(r"^### Previous Maintenance Record\b", section, maxsplit=1, flags=re.MULTILINE)[0]


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


def independent_audit_issues(evidence_section: str, record: "CardRecord", *, correction_branch: str | None = None) -> tuple[str, ...]:
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
    if not MAINTENANCE_BRANCH.fullmatch(values.get("Branch", "")) and not re.fullmatch(r"card/v1-c\d{2}-[a-z0-9-]+", values.get("Branch", "")) and not (correction_branch and values.get("Branch") == correction_branch and re.fullmatch(r"fix/card-integration-[a-z0-9-]+", correction_branch)):
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
    if record.state != "COMPLETE" and status in {"PASS", "PASS_WITH_GAPS"} and not affirmative_audit_verdict(values.get("Verdict", "")):
        issues.append(f"{record.card_id}:INDEPENDENT_AUDIT_VERDICT_UNRESOLVED")
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
                heading == "### Independent Audit" and (re.match(r"## V1-C\d{2} ", owner) is not None or owner == "## 26. Card Integration Lifecycle Correction")
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


def worktree_candidate_identity(
    repo: Path, base_sha: str, *, recorded_branch: str | None = None,
) -> dict[str, str]:
    """Bind branch/base, effective content/modes, partial index, and untracked files.

    Only validated integration uses recorded_branch to reproduce the original
    branch component after squash; it never skips content verification.
    """
    if not FULL_GIT_SHA.fullmatch(base_sha):
        raise ValueError("CANDIDATE_BASE_SHA_INVALID")
    branch = recorded_branch if recorded_branch is not None else subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=repo, text=True,
    ).strip()
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
        worktree = _normalize_integration_results(path, worktree)
        worktree = _normalize_audit_recording(path, worktree) if path == "TRAID_CARD_EVIDENCE_MAP.md" and worktree.startswith(b"FILE\0") else worktree
        index = subprocess.run(["git", "show", f":{path}"], cwd=repo, capture_output=True, check=False)
        if index.returncode == 0:
            staged = _normalize_integration_results(path, b"FILE\0" + index.stdout)
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
            head = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=repo, capture_output=True, check=False)
            head_content = _normalize_integration_results(path, b"FILE\0" + head.stdout) if head.returncode == 0 else b"DELETED"
            head_content = _normalize_audit_recording(path, head_content) if path == "TRAID_CARD_EVIDENCE_MAP.md" and head.returncode == 0 else head_content
            head_row = subprocess.check_output(["git", "ls-tree", "HEAD", "--", path], cwd=repo).splitlines()
            head_mode = head_row[0].split(b" ", 1)[0] if head_row else b"000000"
            if staged != head_content or index_mode != head_mode:
                _hash_part(digest, b"divergent index", staged)
                _hash_part(digest, b"divergent index mode", index_mode)
    return {"Candidate Type": "WORKTREE", "Branch": branch, "Base SHA": base_sha,
            "Candidate Diff SHA-256": digest.hexdigest(), "Untracked Files": ", ".join(untracked) if untracked else "NONE"}


def _integration_record(control: str) -> dict[str, str]:
    section = control_section(control, "6. Active Card Record")
    blocks = re.findall(r"^Card Integration Record:\n\n```text\n(.*?)^```", section, re.M | re.S)
    if not blocks:
        return {}
    if len(blocks) != 1:
        raise ValueError("CARD_INTEGRATION_RECORD_AMBIGUOUS")
    pairs = re.findall(r"^([^:\n]+): ([^\n]+)$", blocks[0], re.M)
    if len(pairs) != len([line for line in blocks[0].splitlines() if line.strip()]):
        raise ValueError("CARD_INTEGRATION_RECORD_MALFORMED")
    if len(dict(pairs)) != len(pairs):
        raise ValueError("CARD_INTEGRATION_FIELD_DUPLICATED")
    return dict(pairs)


def _normalize_integration_results(path: str, content: bytes) -> bytes:
    # Only designated self-digest/merge-receipt values, never scope, source
    # identity, correction authority or record structure. A receipt value is
    # still evaluated by the authority gate; normalization grants no permission.
    if path == "PROJECT_CONTROL.md":
        prefix = b"FILE\0" if content.startswith(b"FILE\0") else b""
        text = content[len(prefix):].decode()
        section = control_section(text, "6. Active Card Record")
        normalized = re.sub(r"(Card Integration Record:\n\n```text\n)(.*?)(^```)",
                            lambda m: m[1] + re.sub(r"(?m)^((?:Correction Diff SHA-256|Human Merge Approval): )[^\n]*", r"\g<1><integration-result>", m[2]) + m[3],
                            section, flags=re.M | re.S)
        if section:
            text = re.sub(r"(^## 6\. Active Card Record\n)(.*?)(?=^## |\Z)",
                          lambda m: m[1] + normalized, text, flags=re.M | re.S)
        content = prefix + text.encode()
    return content


def committed_candidate_digest(repo: Path, commit: str, base: str, branch: str) -> str:
    """Reproduce the effective-content digest from immutable Git objects/modes."""
    digest = hashlib.sha256()
    _hash_part(digest, b"schema", b"TraID frozen worktree v1")
    _hash_part(digest, b"branch", branch.encode())
    _hash_part(digest, b"base", base.encode())
    rows = subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", commit], cwd=repo).split(b"\0")
    entries = []
    for row in rows:
        if not row:
            continue
        metadata, path = row.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob" or mode not in {b"100644", b"100755", b"120000"}:
            raise ValueError("CARD_INTEGRATION_UNSUPPORTED_GIT_ENTRY")
        entries.append((path, mode, oid))
    proc = subprocess.run(["git", "cat-file", "--batch"], cwd=repo,
                          input=b"".join(oid + b"\n" for _, _, oid in entries), capture_output=True, check=True)
    offset = 0
    contents = {}
    for path, mode, oid in entries:
        end = proc.stdout.index(b"\n", offset)
        size = int(proc.stdout[offset:end].split()[-1])
        contents[path] = proc.stdout[end + 1:end + 1 + size]
        offset = end + 2 + size
    for path, mode, oid in sorted(entries):
        name = path.decode()
        content = (b"SYMLINK\0" if mode == b"120000" else b"FILE\0") + contents[path]
        if mode != b"120000":
            content = _normalize_audit_recording(name, content)
            content = _normalize_integration_results(name, content)
        _hash_part(digest, b"tracked path", path)
        _hash_part(digest, b"worktree", content)
        _hash_part(digest, b"worktree mode", mode)
    return digest.hexdigest()


def github_card_merge_issues(pr: str, source: str, base: str, anchor: str, branch: str) -> tuple[str, ...]:
    """Read the actual public PR; no credential, write, or approval inference."""
    import json
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    if not re.fullmatch(r"[1-9][0-9]*", pr) and pr != "DISCOVER":
        return ("CARD_INTEGRATION_PR_INVALID",)
    prefix = "https://api.github.com/repos/jo-soroush/traid-market-intelligence/pulls"
    url = prefix + ("?" + urlencode({"state": "closed", "base": "main", "head": "jo-soroush:" + branch, "per_page": 100}) if pr == "DISCOVER" else "/" + pr)
    try:
        with urlopen(Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "TraID-Harness"}), timeout=10) as response:
            value = json.load(response)
        if pr == "DISCOVER":
            matches = [v for v in value if v.get("head", {}).get("sha") == source and v.get("merge_commit_sha") == anchor]
            if len(matches) != 1:
                return ("CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH",)
            number = matches[0].get("number")
            if type(number) is not int or number <= 0:
                return ("CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH",)
            # List responses do not carry the authoritative `merged` boolean.
            with urlopen(Request(prefix + "/" + str(number), headers={"Accept": "application/vnd.github+json", "User-Agent": "TraID-Harness"}), timeout=10) as response:
                value = json.load(response)
        else:
            number = int(pr)
        valid = (value["number"] == number and value["state"] == "closed" and value["merged"] is True and value["merge_commit_sha"] == anchor
                 and value["head"]["sha"] == source and value["head"]["ref"] == branch
                 and value["base"]["sha"] == base and value["base"]["ref"] == "main"
                 and value["head"]["repo"]["full_name"] == "jo-soroush/traid-market-intelligence"
                 and value["base"]["repo"]["full_name"] == "jo-soroush/traid-market-intelligence")
        return () if valid else ("CARD_INTEGRATION_GITHUB_RELATIONSHIP_MISMATCH",)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ("CARD_INTEGRATION_GITHUB_EVIDENCE_UNAVAILABLE",)


def github_card_closure_issues(value: str, repo: Path, head: str) -> tuple[str, ...]:
    """A recorded closure requires a real successful main run, not a status token."""
    import json
    from urllib.request import Request, urlopen
    match = re.fullmatch(r"PASS — run:([1-9][0-9]*) sha:([0-9a-f]{40}) local:(\S.+)", value)
    if not match:
        return ("CARD_CLOSURE_VERIFICATION_MISSING",)
    run_id, sha, reference = match.groups()
    if subprocess.run(["git", "merge-base", "--is-ancestor", sha, head], cwd=repo, capture_output=True).returncode:
        return ("CARD_CLOSURE_VALIDATION_NOT_ANCESTOR",)
    changed = subprocess.check_output(["git", "diff", "--name-only", "--no-renames", sha, head], cwd=repo, text=True).splitlines()
    if not set(changed) <= {"PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"}:
        return ("CARD_CLOSURE_UNVALIDATED_CODE_CHANGE",)
    prefix = "https://api.github.com/repos/jo-soroush/traid-market-intelligence/actions/runs/" + run_id
    try:
        def read(url):
            with urlopen(Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "TraID-Harness"}), timeout=10) as response:
                return json.load(response)
        run, jobs = read(prefix), read(prefix + "/jobs?per_page=100")
        if (run["status"] != "completed" or run["conclusion"] != "success" or run["head_sha"] != sha
                or run["head_branch"] != "main" or run["event"] != "push" or run["path"] != ".github/workflows/ci.yml"):
            return ("CARD_CLOSURE_HOSTED_NOT_VERIFIED",)
        tests = [job for job in jobs["jobs"] if job["name"] == "test"]
        required = {"Install from isolated committed source", "Run pytest", "Run bash scripts/check_secrets.sh",
                    "Run python scripts/harness_consistency_check.py"}
        if len(tests) != 1 or tests[0]["conclusion"] != "success" or not required <= {
                step["name"] for step in tests[0]["steps"] if step["conclusion"] == "success"}:
            return ("CARD_CLOSURE_REQUIRED_CHECK_MISSING",)
        return ()
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ("CARD_CLOSURE_HOSTED_EVIDENCE_UNAVAILABLE",)


def card_integration_issues(control: str, evidence: str, repo: Path, branch: str,
                            *, prospective_source: str | None = None, prospective_correction: str | None = None,
                            verify_external: bool = False, prospective_branch: str | None = None) -> tuple[bool, tuple[str, ...]]:
    """Recognize only a bound Card anchor; never promote verification to COMPLETE.

    Prospective mode is exclusively a simulation result, not external delivery
    proof. It cannot authorize closure and is labelled in the caller output.
    """
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()

    try:
        values = _integration_record(control)
        if not values:
            return False, ()
        correction_branch = values.get("Correction Branch", "NONE")
        if correction_branch != "NONE" and not re.fullmatch(r"fix/card-integration-[a-z0-9-]+", correction_branch):
            raise ValueError("CARD_INTEGRATION_CORRECTION_BRANCH_INVALID")
        if branch not in {"main", correction_branch}:
            return False, ()  # Source-branch checks continue unchanged.
        required = {"Card ID", "Source Branch", "Base SHA", "Source Commit", "Merge Anchor", "PR",
                    "Protected Paths", "Integrated Paths", "Human Merge Approval", "Post-Merge Verification",
                    "Closure Approval", "Correction Branch", "Correction Base SHA", "Correction Paths",
                    "Correction Authorization", "Correction Diff SHA-256"}
        if set(values) != required:
            raise ValueError("CARD_INTEGRATION_SCHEMA_INVALID")
        state = resolve_card_state(control)
        card = values["Card ID"]
        record = next((r for r in state.cards if r.card_id == card), None)
        if state.errors:
            return False, state.errors
        if record is None or (record.state != "COMPLETE" and state.active_card != card):
            raise ValueError("CARD_INTEGRATION_CARD_STATE_MISMATCH")
        if record.state not in {"READY_FOR_HUMAN_REVIEW", "COMPLETE"}:
            raise ValueError("CARD_INTEGRATION_PREMATURE_COMPLETE")
        source_branch = values["Source Branch"]
        if not re.fullmatch(rf"card/{card.lower()}-[a-z0-9-]+", source_branch):
            raise ValueError("CARD_INTEGRATION_SOURCE_BRANCH_INVALID")
        declared = re.search(r"^Git Branch: ([^\n]+)$", _current_repository_section(control), re.M)
        if not declared or declared.group(1) not in {source_branch, correction_branch}:
            raise ValueError("CARD_INTEGRATION_OPERATIONAL_BRANCH_CONFLICT")
        prospective = bool(prospective_source or prospective_correction)
        if (prospective and branch != "main") or (prospective_source and prospective_correction) or (prospective and verify_external):
            raise ValueError("CARD_INTEGRATION_PROSPECTIVE_CONTEXT_INVALID")
        if prospective and prospective_branch != (correction_branch if prospective_correction else source_branch):
            raise ValueError("CARD_INTEGRATION_PROSPECTIVE_BRANCH_MISMATCH")
        if values["Human Merge Approval"] != "NOT_GRANTED" and not re.fullmatch(r"GRANTED — \S.+", values["Human Merge Approval"]):
            raise ValueError("CARD_INTEGRATION_APPROVAL_INVALID")
        if verify_external and (not values["Human Merge Approval"].startswith("GRANTED — ") or not state.delivery_approval):
            raise ValueError("CARD_INTEGRATION_APPROVAL_MISSING")
        if record.state == "READY_FOR_HUMAN_REVIEW" and (values["Post-Merge Verification"] != "NOT_VERIFIED" or values["Closure Approval"] != "NOT_GRANTED"):
            raise ValueError("CARD_INTEGRATION_CLOSURE_REQUIRES_RECORDED_TRANSITION")
        if record.state == "COMPLETE" and (prospective or not values["Closure Approval"].startswith("GRANTED — ")):
            raise ValueError("CARD_INTEGRATION_PREMATURE_COMPLETE")
        base = values["Base SHA"]
        if not FULL_GIT_SHA.fullmatch(base):
            raise ValueError("CARD_INTEGRATION_BASE_INVALID")
        source = values["Source Commit"]
        if source == "DISCOVER":
            source = prospective_source or git("rev-parse", f"refs/remotes/origin/{source_branch}^{{commit}}")
        if not FULL_GIT_SHA.fullmatch(source) or (prospective_source and source != prospective_source):
            raise ValueError("CARD_INTEGRATION_SOURCE_INVALID")
        if subprocess.run(["git", "merge-base", "--is-ancestor", base, source], cwd=repo, capture_output=True).returncode or source == base:
            raise ValueError("CARD_INTEGRATION_SOURCE_ANCESTRY_INVALID")
        source_evidence = git("show", f"{source}:TRAID_CARD_EVIDENCE_MAP.md")
        section = card_evidence_section(source_evidence, card)
        current_section = card_evidence_section(evidence, card)
        pattern = r"^### Independent Audit\n(.*?)(?=^### |\Z)"
        original_audit = re.search(pattern, section, re.M | re.S)
        current_audit = re.search(pattern, current_section, re.M | re.S)
        if not original_audit or not current_audit or original_audit.group(1).strip() != current_audit.group(1).strip():
            raise ValueError("CARD_INTEGRATION_HISTORICAL_AUDIT_CHANGED")
        audit_issues = independent_audit_issues(section, CardRecord(card, record.title, "COMPLETE", True))
        if audit_issues:
            return False, audit_issues
        audit = dict(re.findall(r"^[ \t-]*([^:\n]+):[ \t]*([^\n]*)$", original_audit.group(1), re.M))
        if audit.get("Status") not in {"PASS", "PASS_WITH_GAPS"} or not affirmative_audit_verdict(audit.get("Verdict", "")):
            raise ValueError("CARD_INTEGRATION_AUDIT_NOT_ACCEPTED")
        if audit.get("Branch") != source_branch or audit.get("Base SHA") != base:
            raise ValueError("CARD_INTEGRATION_AUDIT_CONTEXT_MISMATCH")
        if audit.get("Candidate Type") != "WORKTREE" or committed_candidate_digest(repo, source, base, source_branch) != audit.get("Candidate Diff SHA-256"):
            raise ValueError("CARD_INTEGRATION_SOURCE_DIGEST_MISMATCH")
        head = git("rev-parse", "HEAD")
        anchor = values["Merge Anchor"]
        if anchor == "DISCOVER":
            matches = [c for c in git("rev-list", "--first-parent", f"{base}..{head}").splitlines()
                       if git("show", "-s", "--format=%P", c) == base and git("rev-parse", f"{c}^{{tree}}") == git("rev-parse", f"{source}^{{tree}}")]
            if len(matches) != 1:
                raise ValueError("CARD_INTEGRATION_ANCHOR_AMBIGUOUS")
            anchor = matches[0]
        if not FULL_GIT_SHA.fullmatch(anchor) or git("show", "-s", "--format=%P", anchor) != base:
            raise ValueError("CARD_INTEGRATION_ANCHOR_INVALID")
        if subprocess.run(["git", "merge-base", "--is-ancestor", anchor, head], cwd=repo, capture_output=True).returncode:
            raise ValueError("CARD_INTEGRATION_ANCHOR_NOT_ANCESTOR")
        if git("rev-parse", f"{source}^{{tree}}") != git("rev-parse", f"{anchor}^{{tree}}"):
            raise ValueError("CARD_INTEGRATION_TREE_MISMATCH")
        def paths(field):
            raw = values[field]
            result = set() if raw == "NONE" else set(raw.split(", "))
            if any(not p or p.startswith("/") or any(part in {"", ".", ".."} for part in p.split("/")) or "\\" in p for p in result):
                raise ValueError("CARD_INTEGRATION_PATH_INVALID")
            return result
        protected, integrated_paths, allowed = paths("Protected Paths"), paths("Integrated Paths"), paths("Correction Paths")
        actual_paths = set(git("diff", "--name-only", "--no-renames", base, source).splitlines())
        if (actual_paths != integrated_paths or not protected or not protected <= actual_paths or protected & allowed
                or not {p for p in actual_paths if p.startswith("src/")} <= protected):
            raise ValueError("CARD_INTEGRATION_SCOPE_INVALID")
        if verify_external:
            issues = github_card_merge_issues(values["PR"], source, base, anchor, source_branch)
            if issues:
                return False, issues
        changed = set(git("diff", "--name-only", "--no-renames", anchor).splitlines())
        changed |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
        if changed & protected:
            raise ValueError("CARD_INTEGRATION_PROTECTED_CONTENT_CHANGED")
        for path in protected:
            mode, _, oid = git("ls-tree", anchor, "--", path).split("\t")[0].split()
            target = repo / path
            actual_mode = "120000" if target.is_symlink() else "100755" if target.stat().st_mode & 0o111 else "100644"
            content = os.readlink(target).encode() if target.is_symlink() else target.read_bytes()
            if actual_mode != mode or content != subprocess.check_output(["git", "cat-file", "blob", oid], cwd=repo):
                raise ValueError("CARD_INTEGRATION_PROTECTED_CONTENT_CHANGED")
        dirty = bool(git("status", "--porcelain", "--untracked-files=all"))
        if branch == "main" and dirty:
            raise ValueError("CARD_INTEGRATION_DIRTY_MAIN")
        if not prospective:
            target = git("rev-parse", "refs/remotes/origin/main")
            expected_target = head if branch == "main" else anchor
            if (target != expected_target or subprocess.run(
                    ["git", "merge-base", "--is-ancestor", expected_target, head], cwd=repo, capture_output=True).returncode):
                raise ValueError("CARD_INTEGRATION_DIVERGENT_MAIN")
        closure_only = (record.state == "COMPLETE" and correction_branch == "NONE"
                        and changed <= {"PROJECT_CONTROL.md", "TRAID_CARD_EVIDENCE_MAP.md"})
        if (changed or head != anchor) and not closure_only:
            if not changed <= allowed or not values["Correction Authorization"].startswith("GRANTED — "):
                raise ValueError("CARD_INTEGRATION_UNAUTHORIZED_SUBSEQUENT_CHANGE")
            correction_base = values["Correction Base SHA"]
            if correction_base != anchor or correction_branch == "NONE":
                raise ValueError("CARD_INTEGRATION_CORRECTION_CONTEXT_INVALID")
            expected = values["Correction Diff SHA-256"]
            if record.state == "COMPLETE":
                verification = re.fullmatch(r"PASS — run:([1-9][0-9]*) sha:([0-9a-f]{40}) local:(\S.+)", values["Post-Merge Verification"])
                if not verification:
                    raise ValueError("CARD_CLOSURE_VERIFICATION_MISSING")
                actual = committed_candidate_digest(repo, verification.group(2), correction_base, correction_branch)
            else:
                actual = worktree_candidate_identity(repo, correction_base, recorded_branch=correction_branch)["Candidate Diff SHA-256"]
            if not SHA256.fullmatch(expected) or expected != actual:
                raise ValueError("CARD_INTEGRATION_CORRECTION_DIGEST_MISMATCH")
            if prospective_correction:
                if (not FULL_GIT_SHA.fullmatch(prospective_correction)
                        or git("rev-parse", f"{prospective_correction}^{{tree}}") != git("rev-parse", f"{head}^{{tree}}")
                        or git("show", "-s", "--format=%P", head) != correction_base
                        or subprocess.run(["git", "merge-base", "--is-ancestor", correction_base, prospective_correction], cwd=repo, capture_output=True).returncode
                        or committed_candidate_digest(repo, prospective_correction, correction_base, correction_branch) != expected):
                    raise ValueError("CARD_INTEGRATION_PROSPECTIVE_CORRECTION_INVALID")
            if branch == "main":
                correction = re.search(r"^## 26\. Card Integration Lifecycle Correction\n(.*?)(?=^## |^# |\Z)", evidence, re.M | re.S)
                body = correction.group(1) if correction else ""
                matches = re.findall(r"^### Independent Audit\n(.*?)(?=^### |\Z)", body, re.M | re.S)
                if len(matches) != 1:
                    raise ValueError("CARD_INTEGRATION_CORRECTION_AUDIT_MISSING")
                fields = dict(re.findall(r"^[ \t-]*([^:\n]+):[ \t]*([^\n]*)$", matches[0], re.M))
                if fields.get("Status") not in {"PASS", "PASS_WITH_GAPS"} or not affirmative_audit_verdict(fields.get("Verdict", "")):
                    raise ValueError("CARD_INTEGRATION_CORRECTION_AUDIT_UNRESOLVED")
                if verify_external and not re.match(r"^GRANTED / (?:NOT_PERFORMED|COMPLETED) — MERGE_GRANTED; \S", fields.get("Delivery authorization/performance", "")):
                    raise ValueError("CARD_INTEGRATION_CORRECTION_DELIVERY_NOT_GRANTED")
                if (fields.get("Candidate Type") != "WORKTREE" or fields.get("Branch") != correction_branch
                        or fields.get("Base SHA") != correction_base or fields.get("Candidate Diff SHA-256") != expected):
                    raise ValueError("CARD_INTEGRATION_CORRECTION_AUDIT_IDENTITY_MISMATCH")
                issues = independent_audit_issues("### Independent Audit\n" + matches[0], CardRecord(card, record.title, "COMPLETE", True), correction_branch=correction_branch)
                if issues:
                    return False, issues
                if verify_external:
                    correction_source = git("rev-parse", f"refs/remotes/origin/{correction_branch}^{{commit}}")
                    if subprocess.run(["git", "merge-base", "--is-ancestor", correction_base, correction_source], cwd=repo, capture_output=True).returncode:
                        raise ValueError("CARD_INTEGRATION_CORRECTION_SOURCE_ANCESTRY_INVALID")
                    if committed_candidate_digest(repo, correction_source, correction_base, correction_branch) != expected:
                        raise ValueError("CARD_INTEGRATION_CORRECTION_SOURCE_MISMATCH")
                    anchors = [commit for commit in git("rev-list", "--first-parent", f"{correction_base}..{head}").splitlines()
                               if git("show", "-s", "--format=%P", commit) == correction_base
                               and git("rev-parse", f"{commit}^{{tree}}") == git("rev-parse", f"{correction_source}^{{tree}}")]
                    if len(anchors) != 1:
                        raise ValueError("CARD_INTEGRATION_CORRECTION_ANCHOR_INVALID")
                    issues = github_card_merge_issues("DISCOVER", correction_source, correction_base, anchors[0], correction_branch)
                    if issues:
                        return False, issues
        if prospective_correction and not (changed or head != anchor):
            raise ValueError("CARD_INTEGRATION_PROSPECTIVE_CORRECTION_INVALID")
        if record.state == "COMPLETE":
            if not verify_external:
                raise ValueError("CARD_CLOSURE_EXTERNAL_VERIFICATION_REQUIRED")
            receipt = re.search(r"^### Delivery Verification\n(.*?)(?=^### |\Z)", current_section, re.M | re.S)
            fields = dict(re.findall(r"^([^:\n]+): ([^\n]+)$", receipt.group(1), re.M)) if receipt else {}
            verification = re.fullmatch(r"PASS — run:([1-9][0-9]*) sha:([0-9a-f]{40}) local:(\S.+)", values["Post-Merge Verification"])
            if not verification:
                raise ValueError("CARD_CLOSURE_VERIFICATION_MISSING")
            run_id, validated_sha, local = verification.groups()
            expected_receipt = {"State": "POST_MERGE_VERIFIED", "Source Branch": source_branch, "Base SHA": base,
                                "Audit Digest": audit["Candidate Diff SHA-256"], "Source Commit": source,
                                "Merge Anchor": anchor, "Validated Main": validated_sha, "Hosted Run": run_id,
                                "Local Validation Evidence": local, "Closure Approval": values["Closure Approval"]}
            if fields != expected_receipt:
                raise ValueError("CARD_CLOSURE_RECEIPT_MISMATCH")
            issues = github_card_closure_issues(values["Post-Merge Verification"], repo, head)
            if issues:
                return False, issues
        return True, ()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "CARD_INTEGRATION_GIT_EVIDENCE_UNAVAILABLE"
        return False, (reason,)


def historical_card_delivery_issues(control: str, evidence: str, repo: Path) -> tuple[str, ...]:
    """Attest archived delivery receipts too; local prose cannot forge history."""
    live = _integration_record(control).get("Card ID")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    for record in parse_card_table(control):
        if record.state != "COMPLETE" or int(record.card_id[-2:]) < 7 or record.card_id == live:
            continue
        section = card_evidence_section(evidence, record.card_id)
        issues = card_documentation_issues(section, record)
        if issues:
            return issues
        receipt = re.search(r"^### Delivery Verification\n(.*?)(?=^### |\Z)", section, re.M | re.S)
        fields = dict(re.findall(r"^([^:\n]+): ([^\n]+)$", receipt.group(1), re.M))
        source, base, anchor, validated = (fields[key] for key in ("Source Commit", "Base SHA", "Merge Anchor", "Validated Main"))
        try:
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()
            source_section = card_evidence_section(git("show", f"{source}:TRAID_CARD_EVIDENCE_MAP.md"), record.card_id)
            pattern = r"^### Independent Audit\n(.*?)(?=^### |\Z)"
            source_audit, current_audit = re.search(pattern, source_section, re.M | re.S), re.search(pattern, section, re.M | re.S)
            if (not source_audit or not current_audit or source_audit[1].strip() != current_audit[1].strip()
                    or committed_candidate_digest(repo, source, base, fields["Source Branch"]) != fields["Audit Digest"]
                    or git("show", "-s", "--format=%P", anchor) != base
                    or git("rev-parse", f"{source}^{{tree}}") != git("rev-parse", f"{anchor}^{{tree}}")
                    or subprocess.run(["git", "merge-base", "--is-ancestor", base, source], cwd=repo, capture_output=True).returncode
                    or subprocess.run(["git", "merge-base", "--is-ancestor", anchor, validated], cwd=repo, capture_output=True).returncode
                    or subprocess.run(["git", "merge-base", "--is-ancestor", validated, head], cwd=repo, capture_output=True).returncode):
                return (f"{record.card_id}:HISTORICAL_DELIVERY_IDENTITY_MISMATCH",)
            issues = github_card_merge_issues("DISCOVER", source, base, anchor, fields["Source Branch"])
            if not issues:
                # Later independently authorized Cards may follow this historical
                # validated commit; their changes do not rewrite its result.
                issues = github_card_closure_issues("PASS — run:" + fields["Hosted Run"] + " sha:" + validated
                                                   + " local:" + fields["Local Validation Evidence"], repo, validated)
            if issues:
                return tuple(f"{record.card_id}:{issue}" for issue in issues)
        except (OSError, ValueError, subprocess.CalledProcessError):
            return (f"{record.card_id}:HISTORICAL_DELIVERY_EVIDENCE_UNAVAILABLE",)
    return ()


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
    *,
    recorded_branch: str | None = None,
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
    if values.get("Branch") != (recorded_branch if recorded_branch is not None else branch):
        issues.append("MAINTENANCE_CANDIDATE_BRANCH_MISMATCH")
    if not FULL_GIT_SHA.fullmatch(values.get("Base SHA", "")):
        issues.append("MAINTENANCE_CANDIDATE_BASE_INVALID")
    if not SHA256.fullmatch(values.get("Candidate Diff SHA-256", "")):
        issues.append("MAINTENANCE_CANDIDATE_DIFF_INVALID")
    if not _valid_untracked_manifest(values.get("Untracked Files", "")):
        issues.append("MAINTENANCE_CANDIDATE_UNTRACKED_INVALID")
    if issues:
        return tuple(issues)
    actual = worktree_candidate_identity(repo, values["Base SHA"], recorded_branch=recorded_branch)
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


def integrated_maintenance_issues(
    control: str, evidence: str, branch: str, repo: Path,
) -> tuple[bool, tuple[str, ...]]:
    """Validate an immutable branch snapshot on main; never infer review from ancestry alone.

    This is an accidental-drift check, not authentication of in-repo attestations
    or proof of GitHub delivery. A malicious main writer can forge those inputs.
    """
    current = [body for classification, body in _maintenance_audit_records(evidence)
               if classification == "CURRENT"]
    if branch != "main" or not current:
        return False, ()
    if len(current) != 1:
        return False, ("MAINTENANCE_MULTIPLE_CURRENT_AUDIT_RECORDS",)
    if len(re.findall(r"^### Current Maintenance Record$", control, re.MULTILINE)) != 1:
        return False, ("INTEGRATED_MAINTENANCE_RECORD_INVALID",)
    record = _maintenance_record(control)
    body = current[0]

    def value(text: str, field: str) -> str:
        matches = re.findall(rf"^{re.escape(field)}:[ \t]*([^\n]*)$", text, re.MULTILINE)
        return matches[0].strip() if len(matches) == 1 else ""

    if any(not value(record, field) for field in MAINTENANCE_FIELDS):
        return False, ("INTEGRATED_MAINTENANCE_RECORD_INVALID",)
    # Normalized audit fields remain mutable result recording, so validate their
    # structure and meaning as well as reproducing the content-bound digest.
    audit_fields = ("Record Classification", "Maintenance Task ID", "Status", "Candidate Type",
                    "Branch", "Base SHA", "Candidate Diff SHA-256", "Untracked Files",
                    "Verifier context", "Canonical inputs reviewed", "Evidence reviewed",
                    "Findings", "Unresolved blockers", "Gap dispositions", "Limitations",
                    "Verdict", "Delivery authorization/performance")
    if any(not value(body, field) for field in audit_fields):
        return False, ("INTEGRATED_MAINTENANCE_AUDIT_INVALID",)
    recorded = value(record, "Branch")
    if not MAINTENANCE_BRANCH.fullmatch(recorded) or value(_current_repository_section(control), "Git Branch") != recorded:
        return False, ("INTEGRATED_MAINTENANCE_BRANCH_MISMATCH",)
    if value(body, "Branch") != recorded:
        return False, ("MAINTENANCE_CANDIDATE_BRANCH_MISMATCH",)
    if value(body, "Maintenance Task ID") != value(record, "Maintenance Task ID"):
        return False, ("MAINTENANCE_AUDIT_TASK_ID_MISMATCH",)
    status = value(record, "Status").split(" —", 1)[0]
    if status not in {"READY_FOR_HUMAN_REVIEW", "READY_TO_DELIVER", "PUSHED", "CI_VERIFIED"}:
        return False, ("INTEGRATED_MAINTENANCE_STAGE_INVALID",)
    if not affirmative_audit_verdict(value(body, "Verdict")):
        return False, ("MAINTENANCE_AUDIT_VERDICT_UNRESOLVED",)
    authorization = value(body, "Delivery authorization/performance")
    if not re.match(r"^(?:GRANTED|AUTHORIZED) / (?:NOT_PERFORMED|COMPLETED) — \S", authorization):
        return False, ("MAINTENANCE_DELIVERY_AUTHORIZATION_MISSING",)
    base = value(record, "Base Commit").split(" —", 1)[0]
    if not FULL_GIT_SHA.fullmatch(base) or value(body, "Base SHA") != base:
        return False, ("MAINTENANCE_CANDIDATE_BASE_MISMATCH",)
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo):
        return False, ("UNAUTHORIZED_DIRTY_WORKTREE",)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if head == base or subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, head], cwd=repo,
        capture_output=True, check=False,
    ).returncode != 0:
        return False, ("MAINTENANCE_BASE_NOT_ANCESTOR",)
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "--no-renames", base, head], cwd=repo, text=True,
    ).splitlines()
    allowed = {path.strip().removeprefix("./") for path in value(record, "Allowed Paths").split(",")}
    if not changed or any(path not in allowed for path in changed):
        return False, ("INTEGRATED_MAINTENANCE_OUT_OF_SCOPE",)
    issues = maintenance_audit_record_lifecycle_issues(control, evidence, recorded)
    issues += current_maintenance_candidate_issues(
        evidence, branch, repo, value(record, "Maintenance Task ID"), recorded_branch=recorded,
    )
    # Apply the existing resolved-audit gate even when the frozen record was
    # reviewed at READY_FOR_HUMAN_REVIEW. No document is rewritten here.
    delivery_record = re.sub(r"^Status:.*$", "Status: READY_TO_DELIVER", record, count=1, flags=re.MULTILINE)
    issues += maintenance_delivery_audit_issues(control.replace(record, delivery_record, 1), evidence)
    return not issues, tuple(dict.fromkeys(issues))


def affirmative_audit_verdict(verdict: str) -> bool:
    """Only explicit affirmative tokens can resolve a current audit."""
    return re.match(r"^PASS(?:_WITH_GAPS)?(?:$|[ \t])", verdict) is not None


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
    if not historical_post_merge and values.get("Status") in {"PASS", "PASS_WITH_GAPS"} and not affirmative_audit_verdict(values.get("Verdict", "")):
        return ("MAINTENANCE_AUDIT_VERDICT_UNRESOLVED",)
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
    allowed = {path.strip().removeprefix("./") for path in values["Allowed Paths"].split(",") if path.strip()}
    unexpected = sorted(path for path in changed_paths if path.removeprefix("./") not in allowed)
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

    current = control_section(control, "2. Current Project State")
    active_values = _line_values(r"^Active Card:\s*(.+)$", current)
    active_state_values = _line_values(r"^Active Card State:\s*(.+)$", current)
    next_values = _line_values(r"^Next Roadmap Card:\s*(.+)$", current)
    next_auth_values = _line_values(r"^Next Card Authorized:\s*(.+)$", current)
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
        if not active_state_values or set(active_state_values) != {"NONE"}:
            errors.append("IDLE_ACTIVE_CARD_STATE_MISMATCH")
        active_count = sum(record.state in ACTIVE_STATES for record in cards)
        if active_count:
            errors.append("ACTIVE_CARD_NONE_WITH_ACTIVE_STATE")
    else:
        active_count = sum(record.state in ACTIVE_STATES for record in cards)
        if active_count != 1:
            errors.append("MULTIPLE_ACTIVE_CARDS" if active_count > 1 else "ACTIVE_CARD_ROW_MISSING")

    active_record = records.get(active_card)
    ledger = control_section(control, "7. Authorization Ledger")
    auth_lines: dict[str, str] = {}
    for match in re.finditer(r"^(V1-C\d{2}) Authorization:[ \t]*(.+)$", ledger, re.MULTILINE):
        card_id, authorization = match.group(1), match.group(2).strip()
        if card_id in auth_lines and auth_lines[card_id] != authorization:
            errors.append(f"AUTHORIZATION_DECLARATIONS_CONFLICT:{card_id}")
        auth_lines[card_id] = authorization
    active_section = control_section(control, "6. Active Card Record")
    current_blocks = re.findall(r"^Current active-Card record:[ \t]*\n\s*```text\n(.*?)(?=^```)", active_section, re.MULTILINE | re.DOTALL)
    if len(current_blocks) > 1:
        errors.append("ACTIVE_CARD_RECORD_AMBIGUOUS")
    # Flat structured records remain supported; delivered records are history.
    active_block_text = current_blocks[0] if len(current_blocks) == 1 else (
        active_section if not re.search(r"delivered-Card record:|completed-Card record:", active_section) else ""
    )
    active_record_state_values = _line_values(r"^State:\s*(.+)$", active_block_text)
    if active_card != "NONE" and active_record_state_values:
        active_record_states = {
            value.split(" —", 1)[0].strip() for value in active_record_state_values
        }
        if len(active_record_states) != 1 or next(iter(active_record_states)) != active_state:
            errors.append("ACTIVE_CARD_RECORD_STATE_MISMATCH")
    start_values = _line_values(r"^Human Start Approval:\s*(.+)$", active_block_text)
    active_start = bool(active_record and active_record.start_approved)
    if active_record:
        active_start = active_start and bool(start_values and len(set(start_values)) == 1 and start_values[0].startswith("GRANTED"))
    if active_card in auth_lines:
        active_start = active_start and "START_GRANTED" in auth_lines[active_card]
    if active_card != "NONE" and not active_start:
        errors.append("ACTIVE_CARD_START_APPROVAL_MISSING")

    delivery_values = _line_values(r"^Human Delivery Approval:\s*(.+)$", active_block_text)
    verified_values = _line_values(r"^Delivery Verified:\s*(.+)$", active_block_text)
    if active_record and any(len(set(values)) > 1 for values in (start_values, delivery_values, verified_values)):
        errors.append("ACTIVE_CARD_AUTHORIZATION_DECLARATIONS_CONFLICT")
    approval = bool(delivery_values and len(set(delivery_values)) == 1 and delivery_values[0].startswith("GRANTED"))
    # A later explicit merge receipt may supersede the frozen source approval.
    # Source identity remains bound; delivery still requires the resolved audit.
    try:
        integration = _integration_record(control)
    except ValueError as exc:
        errors.append(str(exc))
        integration = {}
    if active_record and integration.get("Card ID") == active_card and integration.get("Human Merge Approval", "").startswith("GRANTED — "):
        approval = True
    verified = bool(verified_values and len(set(verified_values)) == 1 and verified_values[0].startswith("YES"))
    if active_card == "NONE":
        completed = [record for record in cards if record.state == "COMPLETE"]
        approval = bool(completed) and all("DELIVERY_GRANTED" in auth_lines.get(record.card_id, "") or "DELIVERY_COMPLETED" in auth_lines.get(record.card_id, "") for record in completed)
        verified = bool(completed) and all("DELIVERY_COMPLETED" in auth_lines.get(record.card_id, "") for record in completed)

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


def main(*, prospective_source: str | None = None, prospective_correction: str | None = None,
         verify_external: bool = False, prospective_branch: str | None = None) -> int:
    control = Path("PROJECT_CONTROL.md").read_text()
    evidence = Path("TRAID_CARD_EVIDENCE_MAP.md").read_text()
    state = resolve_card_state(control)
    if state.errors:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(state.errors)}")
        return 1

    repository = _current_repository_section(control)
    quality_state = control_section(control, "21. Card Quality Gate State")
    required_fields = {
        "Git Branch": re.search(r"^Git Branch:\s*.+$", repository, re.MULTILINE),
        "Git Checkpoint": re.search(r"^Git Checkpoint:\s*[0-9a-f]+", repository, re.MULTILINE),
        "Working Tree": re.search(r"^Working Tree:\s*.+$", repository, re.MULTILINE),
        "CARD_QUALITY_GATE": re.search(r"^CARD_QUALITY_GATE:[ \t]*(PASS|BLOCKED|NOT_RUN)(?:$| —)", quality_state, re.MULTILINE),
    }
    missing_fields = tuple(name for name, match in required_fields.items() if match is None)
    if missing_fields:
        print(f"HARNESS_CONSISTENCY: BLOCKED: MISSING_REQUIRED_LIFECYCLE_FIELD:{','.join(missing_fields)}")
        return 1
    for field in ("Git Branch", "Git Checkpoint", "Working Tree"):
        if len(set(_line_values(rf"^{re.escape(field)}:[ \t]*(.+)$", repository))) != 1:
            print(f"HARNESS_CONSISTENCY: BLOCKED: CURRENT_FIELD_DECLARATIONS_CONFLICT:{field}")
            return 1
    quality_values = _line_values(r"^CARD_QUALITY_GATE:[ \t]*(PASS|BLOCKED|NOT_RUN)(?:$| —.*$)", quality_state)
    if len(set(quality_values)) != 1:
        print("HARNESS_CONSISTENCY: BLOCKED: CURRENT_FIELD_DECLARATIONS_CONFLICT:CARD_QUALITY_GATE")
        return 1

    active_card = state.active_card
    current_card_id = active_card if active_card != "NONE" else next((record.card_id for record in reversed(state.cards) if record.state == "COMPLETE"), "")
    current_record = next((record for record in state.cards if record.card_id == current_card_id), None)
    evidence_section = re.search(rf"## {re.escape(current_card_id)} .*?(?=\n## V1-C\d{{2}} |\Z)", evidence, re.DOTALL)
    evidence_current = evidence_section.group(0) if evidence_section else ""
    evidence_state = re.search(r"^\*\*Status:\*\* (.+)$", evidence_current, re.MULTILINE)
    evidence_state_value = evidence_state.group(1).split(" —", 1)[0].strip() if evidence_state else ""
    quality = re.search(r"^Status: (PASS|BLOCKED)$", evidence_current, re.MULTILINE)
    control_quality = required_fields["CARD_QUALITY_GATE"]
    test_state = re.search(r"^TraID repository test state: (.+)$", control_section(control, "20. Test / Evaluation State"), re.MULTILINE)
    expected_branch = re.search(r"^Git Branch: (.+)$", repository, re.MULTILINE)
    expected_head = re.search(r"^Git Checkpoint: ([0-9a-f]+)", repository, re.MULTILINE)
    expected_tree = re.search(r"^Working Tree: (.+)$", repository, re.MULTILINE)
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
    clean = not changed_paths
    working_tree_policy = expected_tree.group(1).split(" —", 1)[0].strip() if expected_tree else ""
    card_integrated, card_integration_errors = card_integration_issues(
        control, evidence, Path.cwd(), branch, prospective_source=prospective_source,
        prospective_correction=prospective_correction, verify_external=verify_external, prospective_branch=prospective_branch)
    if card_integration_errors:
        print("HARNESS_CONSISTENCY: BLOCKED: " + ", ".join(card_integration_errors))
        return 1
    if verify_external:
        historical_issues = historical_card_delivery_issues(control, evidence, Path.cwd())
        if historical_issues:
            print("HARNESS_CONSISTENCY: BLOCKED: " + ", ".join(historical_issues))
            return 1
    maintenance_issues = maintenance_consistency_issues(control, branch, head, changed_paths)
    integrated, integration_issues = integrated_maintenance_issues(control, evidence, branch, Path.cwd())
    if integration_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(integration_issues)}")
        return 1
    maintenance_record = _maintenance_record(control)
    task_match = re.search(r"^Maintenance Task ID:[ \t]*([^\n]+)$", maintenance_record, re.MULTILINE)
    maintenance_task_id = task_match.group(1).strip() if task_match else None
    if not integrated:
        maintenance_issues += maintenance_audit_record_lifecycle_issues(control, evidence, branch)
        maintenance_issues += current_maintenance_candidate_issues(evidence, branch, Path.cwd(), maintenance_task_id)
        maintenance_issues += maintenance_delivery_audit_issues(control, evidence)
    if maintenance_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(maintenance_issues)}")
        return 1
    if not clean and active_card == "NONE" and not (branch.startswith("maintenance/") or branch.startswith("hotfix/")):
        print("HARNESS_CONSISTENCY: BLOCKED: UNAUTHORIZED_DIRTY_WORKTREE")
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
    documentation_issues = tuple(
        issue for record in state.cards for issue in card_documentation_issues(evidence, record)
    )
    if not card_integrated:
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
        evidence_state=evidence_state_value,
        expected_branch=branch if integrated or card_integrated else (expected_branch.group(1).strip() if expected_branch else ""),
        actual_branch=branch, expected_head=expected_head.group(1) if expected_head else "", actual_head=head,
        head_checkpoint_verified=checkpoint, test_state_verified=bool(test_state and test_state.group(1).startswith("VERIFIED")),
        quality_gate_state=control_quality.group(1) if control_quality else "", evidence_status=evidence_state_value,
        learning_status="COMPLETE" if complete else "", safe_resume_valid=safe_resume_valid, delivery_recorded=state.delivery_verified,
        evidence_delivery_recorded=state.delivery_verified if complete else True, learning_record_complete=not learning_issues,
        stale_completion_rationale="implementation has not started under this redesigned Evidence Map" in evidence,
        working_tree_policy=working_tree_policy,
        actual_working_tree_clean=clean, active_card_exists=active_card == "NONE" or current_record is not None,
        active_card_start_authorized=state.active_start_authorized,
        active_card_state_valid=active_card == "NONE" or (current_record is not None and current_record.state in ACTIVE_STATES),
        current_state_unambiguous=state.current_state_unambiguous,
        active_execution_count=sum(record.state in ACTIVE_STATES for record in state.cards),
        declared_next_card=state.declared_next_card, derived_next_card=state.derived_next_card,
    )
    result = evaluate_state_consistency(facts)
    if result.passed and not documentation_issues:
        if card_integrated:
            label = "VERIFIED_COMPLETE" if complete else "PROSPECTIVE_INTEGRATION" if prospective_source or prospective_correction else "INTEGRATED_PENDING_VERIFICATION"
            print(f"CARD_RUNTIME: {label}; CARD_COMPLETE: {'YES' if complete else 'NO'}; HISTORICAL_AUDIT_IDENTITY: PRESERVED")
            print("EXTERNAL_ATTESTATION: " + ("VERIFIED_MERGE_RELATIONSHIP" if verify_external else "NOT_RUN; DELIVERY_NOT_VERIFIED"))
            if branch != "main":
                print("CORRECTION_RUNTIME: AUTHORIZED_LOCAL_ONLY; CORRECTION_DELIVERY: NOT_GRANTED")
        if integrated:
            print("MAINTENANCE_RUNTIME: INTEGRATED / NO_ACTIVE_MAINTENANCE; AUDIT_RUNTIME: HISTORICAL")
        print("COMPLETED_CARDS: " + (", ".join(completed_card_ids(control)) or "NONE"))
        print("HARNESS_CONSISTENCY: PASS")
        return 0
    reasons = list(result.reason_codes) + list(documentation_issues)
    print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(dict.fromkeys(reasons))}")
    return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-external", action="store_true",
                        help="Verify live GitHub merge/closure evidence; required for completion")
    sys.exit(main(verify_external=parser.parse_args().verify_external))
