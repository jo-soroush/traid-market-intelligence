#!/usr/bin/env python3
"""Fail-closed, Card-agnostic validation of TraID's canonical lifecycle state."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from traid.harness.lifecycle import LifecycleFacts, evaluate_state_consistency


C01_LEARNING_RECORD_FIELDS = (
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
CARD_STATES = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "READY_FOR_HUMAN_REVIEW", "COMPLETE", "DEFERRED"}
ACTIVE_STATES = {"IN_PROGRESS", "BLOCKED", "READY_FOR_HUMAN_REVIEW"}
CARD_ROW = re.compile(r"^\|\s*(V1-C\d{2})\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|\s*(YES|NO)\s*\|", re.MULTILINE)
CARD_ID = re.compile(r"^(V1-C\d{2})(?:\s+—\s+(.+))?$")
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


def learning_record_issues(evidence_c01: str) -> tuple[str, ...]:
    learning = re.search(r"^### Learning Record\n(.*?)(?=^### Exit Gate Proof$)", evidence_c01, re.MULTILINE | re.DOTALL)
    if not learning:
        return ("LEARNING_RECORD_SECTION_MISSING",)
    body = learning.group(1)
    issues: list[str] = []
    for field in C01_LEARNING_RECORD_FIELDS:
        match = re.search(rf"^{re.escape(field)}:\s*(.*)$", body, re.MULTILINE)
        if not match:
            issues.append(f"LEARNING_FIELD_MISSING:{field}")
        elif not match.group(1).strip():
            issues.append(f"LEARNING_FIELD_EMPTY:{field}")
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
    summary = re.search(r"^Implementation:\s*COMPLETE\s+—\s*(.+)$", current, re.MULTILINE)
    if summary:
        complete_ids = {record.card_id.split("-", 1)[1] for record in parse_card_table(control) if record.state == "COMPLETE"}
        if any(card_id not in summary.group(1) for card_id in sorted(complete_ids)):
            issues.append("COMPLETED_CARD_SUMMARY_INCOMPLETE")
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
    if maintenance_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(maintenance_issues)}")
        return 1
    current_issues = current_state_issues(control, evidence, head)
    if current_issues:
        print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(current_issues)}")
        return 1
    checkpoint = bool(expected_head and subprocess.run(["git", "cat-file", "-e", f"{expected_head.group(1)}^{{commit}}"], check=False).returncode == 0 and subprocess.run(["git", "merge-base", "--is-ancestor", expected_head.group(1), head], check=False).returncode == 0)
    clean = not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    learning_issues = learning_record_issues(evidence_current) if current_card_id == "V1-C01" else ()
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
    if result.passed and not learning_issues:
        print("HARNESS_CONSISTENCY: PASS")
        return 0
    reasons = list(result.reason_codes) + list(learning_issues)
    print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(dict.fromkeys(reasons))}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
