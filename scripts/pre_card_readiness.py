#!/usr/bin/env python3
"""Run a deterministic prerequisite check before a Card starts implementation."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from traid.harness.lifecycle import ReadinessFacts, evaluate_pre_card_readiness


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


def command_available(command: list[str], cwd: Path) -> bool:
    return subprocess.run(command, cwd=cwd, capture_output=True, check=False).returncode == 0


def dependency_is_complete(control_path: Path, card_id: str) -> bool:
    text = control_path.read_text() if control_path.is_file() else ""
    match = re.search(rf"^\| {re.escape(card_id)} \|.*?\| COMPLETE \|", text, re.MULTILINE)
    return match is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card-id", required=True)
    parser.add_argument("--docker-required", action="store_true")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-branch")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--dependency-card", action="append", default=[])
    parser.add_argument("--config-file", action="append", default=[])
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    repository_available = command_available(["git", "rev-parse", "--is-inside-work-tree"], root)
    branch = ""
    if repository_available:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
    branch_condition_met = not args.expected_branch or branch == args.expected_branch
    working_tree_condition_met = not args.require_clean or not subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip()
    project_environment_available = (root / "pyproject.toml").is_file() and sys.version_info[:2] == (3, 13)
    project_pytest = root / ".venv" / "bin" / "pytest"
    test_tools_available = project_pytest.is_file() and command_available([str(project_pytest), "--version"], root)
    dependencies_complete = all(
        dependency_is_complete(root / "PROJECT_CONTROL.md", card_id) for card_id in args.dependency_card
    )
    required_config_present = all((root / path).is_file() for path in args.config_file)
    result = evaluate_pre_card_readiness(
        ReadinessFacts(
            args.card_id,
            docker_required=args.docker_required,
            docker_available=docker_available(),
            python_available=sys.version_info[:2] == (3, 13),
            test_tools_available=test_tools_available,
            repository_available=repository_available,
            branch_condition_met=branch_condition_met,
            working_tree_condition_met=working_tree_condition_met,
            project_environment_available=project_environment_available,
            dependencies_complete=dependencies_complete,
            required_config_present=required_config_present,
        )
    )
    print("READINESS_FACT: repository=PROBED")
    print(f"READINESS_FACT: branch={'PROBED' if args.expected_branch else 'NOT_REQUESTED'}")
    print(f"READINESS_FACT: working_tree={'PROBED' if args.require_clean else 'NOT_REQUESTED'}")
    print("READINESS_FACT: python_environment=PROBED")
    print("READINESS_FACT: project_pytest_runner=PROBED")
    print(
        "READINESS_FACT: dependencies="
        + ("DERIVED_FROM_PROJECT_CONTROL" if args.dependency_card else "NOT_REQUESTED")
    )
    print(
        "READINESS_FACT: required_config="
        + ("PROBED" if args.config_file else "NOT_REQUESTED")
    )
    print(f"READINESS_FACT: docker={'PROBED' if args.docker_required else 'NOT_REQUESTED'}")
    print("READINESS_FACT: external_services=CALLER_SUPPLIED/NOT_INDEPENDENTLY_VERIFIED")
    print("READINESS_FACT: credentials=CALLER_SUPPLIED/NOT_INDEPENDENTLY_VERIFIED")
    print("READINESS_FACT: source_verification=CALLER_SUPPLIED/NOT_INDEPENDENTLY_VERIFIED")
    print("READINESS_FACT: datasets=CALLER_SUPPLIED/NOT_INDEPENDENTLY_VERIFIED")
    if result.passed:
        print(f"READINESS_GATE: PASS ({args.card_id})")
        return 0
    print(f"READINESS_GATE: BLOCKED ({args.card_id}): {', '.join(result.reason_codes)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
