#!/usr/bin/env python3
"""Validate the current Project Control/Evidence/Git lifecycle state."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from traid.harness.lifecycle import LifecycleFacts, evaluate_state_consistency


C01_LEARNING_RECORD_FIELDS = (
    "What We Wanted To Build",
    "Why It Matters",
    "System Before This Card",
    "Design Decision",
    "Alternatives Considered",
    "Why We Chose This Approach",
    "What We Implemented",
    "What We Built",
    "Why We Built It",
    "Engineering problem",
    "AI / Data / Financial concept",
    "How it works",
    "Architecture before",
    "Architecture after",
    "Important files and ownership",
    "Source / provenance",
    "Tests / evaluations and actual results",
    "Financial / data / security invariants",
    "Problems We Hit",
    "Root Cause",
    "How We Solved It",
    "Why The Fix Is Correct",
    "What We Rejected",
    "Problem(s) discovered",
    "How we diagnosed / solved them",
    "Known Limitations",
    "Professional engineering lesson",
    "Student takeaway",
    "Exit Gate proof",
    "What this enables next",
)


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


def normalize_active_card(value: str) -> str:
    """Normalize the canonical short Card ID from an optional titled value."""

    match = re.match(r"^(V1-C\d{2})(?:\s+—\s+.*)?$", value.strip())
    return match.group(1) if match else value.strip()


def extract(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else default


def main() -> int:
    control = Path("PROJECT_CONTROL.md").read_text()
    evidence = Path("TRAID_CARD_EVIDENCE_MAP.md").read_text()
    card_state = extract(r"^V1-C01: (.+)$", control)
    active_card = extract(r"^Active Card: (.+)$", control)
    active_card = normalize_active_card(active_card)
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    expected_branch = extract(r"^Git Branch: (.+)$", control)
    expected_head = extract(r"^Git HEAD: ([0-9a-f]+)", control)
    expected_working_tree = extract(r"^Working Tree: (.+)$", control)
    actual_working_tree_clean = not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    evidence_section = re.search(r"## V1-C01 .*?(?=\n## V1-C02)", evidence, re.DOTALL)
    evidence_c01 = evidence_section.group(0) if evidence_section else ""
    evidence_state = extract(r"^\*\*Status:\*\* (.+)$", evidence_c01)
    quality_gate = extract(r"^Status: (PASS|BLOCKED)$", evidence_c01)
    control_quality = extract(r"^CARD_QUALITY_GATE: (PASS|BLOCKED)", control)
    evidence_status = evidence_state.split(" —", 1)[0].strip()
    learning_status = extract(r"^Learning Record Status: (.+)$", control).split(" —", 1)[0].strip()
    test_state_verified = extract(r"^TraID repository test state: (.+)$", control).startswith("VERIFIED")
    safe_resume = re.search(r"## 34\. Current Safe Resume Point(.*?)(?=\n## 35\.)", control, re.DOTALL)
    safe_resume_valid = bool(safe_resume and "Active Card is NONE" in safe_resume.group(1) and "C02 start NOT_GRANTED" in safe_resume.group(1))
    c02_not_started = bool(re.search(r"^\| V1-C02 \|.*\| NOT_STARTED \|", control, re.MULTILINE))
    c02_authorized = bool(re.search(r"^Next Card Authorized: YES$|V1-C02 Authorization:.*START_GRANTED", control, re.MULTILINE))
    stale_completion = "implementation has not started under this redesigned Evidence Map" in evidence
    learning_issues = learning_record_issues(evidence_c01)
    learning_record_complete = not learning_issues
    delivery_recorded = "DELIVERY_COMPLETED" in extract(r"^V1-C01 Authorization: (.+)$", control)
    evidence_delivery_recorded = "**Delivery Approval:** GRANTED" in evidence_c01 and "Post-merge verification: PASS" in evidence_c01
    pending_not_applicable = "Financial invariants: Pending" in evidence_c01 and "Not applicable" in evidence_c01
    result = evaluate_state_consistency(
        LifecycleFacts(
            card_id="V1-C01",
            card_state=card_state,
            active_card=active_card,
            quality_gate=quality_gate,
            delivery_approval="Delivery Approval: GRANTED" in control,
            delivery_verified="Delivery Verified: YES" in control,
            project_control_state=card_state,
            evidence_state=evidence_state,
            expected_branch=expected_branch,
            actual_branch=branch,
            expected_head=expected_head,
            actual_head=head,
            test_state_verified=test_state_verified,
            quality_gate_state=control_quality,
            evidence_status=evidence_status,
            learning_status=learning_status,
            safe_resume_valid=safe_resume_valid,
            delivery_recorded=delivery_recorded,
            evidence_delivery_recorded=evidence_delivery_recorded,
            learning_record_complete=learning_record_complete,
            c02_not_started=c02_not_started,
            c02_authorized=c02_authorized,
            stale_completion_rationale=stale_completion,
            expected_working_tree_clean=not expected_working_tree.startswith("DIRTY_ALLOWED"),
            actual_working_tree_clean=actual_working_tree_clean,
            pending_not_applicable=pending_not_applicable,
        )
    )
    if result.passed and not learning_issues:
        print("HARNESS_CONSISTENCY: PASS")
        return 0
    reasons = list(result.reason_codes) + list(learning_issues)
    print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(reasons)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
