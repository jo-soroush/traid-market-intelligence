#!/usr/bin/env python3
"""Run the production Harness against a disposable maintenance squash merge.

Only the temporary clone is mutated. No branch, commit, or remote is changed
in the source checkout. This verifies integration, not hosted PR provenance.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def simulate(root: Path, base: str, head: str, branch: str) -> int:
    if not re.fullmatch(r"(?:maintenance|hotfix)/[^\s]+", branch):
        print("MAINTENANCE_INTEGRATION: NOT_APPLICABLE — non-maintenance source branch")
        return 0
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (base, head)):
        print("MAINTENANCE_INTEGRATION: BLOCKED — full base/head SHAs required")
        return 1
    env = {**os.environ, "GIT_AUTHOR_NAME": "integration simulation",
           "GIT_AUTHOR_EMAIL": "simulation@example.invalid",
           "GIT_COMMITTER_NAME": "integration simulation",
           "GIT_COMMITTER_EMAIL": "simulation@example.invalid"}
    try:
        actual_branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=root, text=True,
        ).strip()
        actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        if actual_branch != branch or actual_head != head or subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=root,
        ):
            raise ValueError("source must be the clean exact PR branch/head")
        target = subprocess.check_output(
            ["git", "rev-parse", "refs/remotes/origin/main^{commit}"], cwd=root, text=True,
        ).strip()
        if target != base:
            raise ValueError("current fetched main differs from validation base; refresh validation")
        for sha in (base, head):
            subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"], cwd=root, check=True)
        with tempfile.TemporaryDirectory(prefix="traid-integration-") as directory:
            scratch = Path(directory) / "repo"
            subprocess.run(["git", "clone", "--no-hardlinks", "--no-checkout", str(root), str(scratch)],
                           check=True, capture_output=True)
            for args in (("checkout", "-B", "main", base), ("merge", "--squash", head),
                         ("commit", "-m", "disposable maintenance squash simulation")):
                subprocess.run(["git", *args], cwd=scratch, env=env, check=True, capture_output=True)
            if subprocess.check_output(["git", "status", "--porcelain"], cwd=scratch):
                raise ValueError("simulated main is dirty")
            result = subprocess.run(
                [sys.executable, "scripts/harness_consistency_check.py"], cwd=scratch,
                env={**env, "PYTHONPATH": str(scratch / "src")}, check=False,
            )
            print("MAINTENANCE_INTEGRATION: " + ("PASS" if result.returncode == 0 else "BLOCKED"))
            return 0 if result.returncode == 0 else 1
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"MAINTENANCE_INTEGRATION: BLOCKED — {exc}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    sys.exit(simulate(Path.cwd(), args.base, args.head, args.branch))
