#!/usr/bin/env python3
"""Run a deterministic prerequisite check before a Card starts implementation."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

from traid.harness.lifecycle import ReadinessFacts, evaluate_pre_card_readiness


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card-id", required=True)
    parser.add_argument("--docker-required", action="store_true")
    args = parser.parse_args()
    result = evaluate_pre_card_readiness(
        ReadinessFacts(args.card_id, docker_required=args.docker_required, docker_available=docker_available())
    )
    if result.passed:
        print(f"READINESS_GATE: PASS ({args.card_id})")
        return 0
    print(f"READINESS_GATE: BLOCKED ({args.card_id}): {', '.join(result.reason_codes)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
