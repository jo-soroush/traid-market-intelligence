#!/usr/bin/env python3
"""Validate the current Project Control/Evidence/Git lifecycle state."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from traid.harness.lifecycle import LifecycleFacts, evaluate_state_consistency


def extract(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else default


def main() -> int:
    control = Path("PROJECT_CONTROL.md").read_text()
    evidence = Path("TRAID_CARD_EVIDENCE_MAP.md").read_text()
    card_state = extract(r"^V1-C01: (.+)$", control)
    active_card = extract(r"^Active Card: (.+)$", control)
    if active_card.startswith("V1-C01"):
        active_card = "V1-C01"
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    expected_branch = extract(r"^Git Branch: (.+)$", control)
    evidence_section = re.search(r"## V1-C01 .*?(?=\n## V1-C02)", evidence, re.DOTALL)
    evidence_c01 = evidence_section.group(0) if evidence_section else ""
    evidence_state = extract(r"^\*\*Status:\*\* (.+)$", evidence_c01)
    quality_gate = extract(r"^Status: (PASS|BLOCKED)$", evidence_c01)
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
            pending_not_applicable=pending_not_applicable,
        )
    )
    if result.passed:
        print("HARNESS_CONSISTENCY: PASS")
        return 0
    print(f"HARNESS_CONSISTENCY: BLOCKED: {', '.join(result.reason_codes)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
