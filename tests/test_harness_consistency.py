from __future__ import annotations

import os
import subprocess
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "harness_consistency_check.py"
CONTROL = ROOT / "PROJECT_CONTROL.md"
EVIDENCE = ROOT / "TRAID_CARD_EVIDENCE_MAP.md"
SPEC = importlib.util.spec_from_file_location("harness_consistency_check", CHECKER)
assert SPEC and SPEC.loader
consistency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consistency)


def c01_evidence_section() -> str:
    text = EVIDENCE.read_text()
    start = text.index("## V1-C01 —")
    end = text.index("\n## V1-C02 —", start)
    return text[start:end]


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
    control = """Active Card: V1-C01 — Repository Baseline & Engineering Harness
Next Card Authorized: NO
V1-C01: READY_FOR_HUMAN_REVIEW
Git Branch: test-branch
Git HEAD: PLACEHOLDER
Working Tree: DIRTY_ALLOWED
TraID repository test state: VERIFIED
CARD_QUALITY_GATE: PASS
Learning Record Status: COMPLETE
V1-C01 Authorization: START_GRANTED; DELIVERY_NOT_GRANTED
| V1-C02 | Canonical Domain Models | NOT_STARTED | NO | NOT_RUN | PENDING |
"""
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
    return subprocess.run([str(ROOT / ".venv" / "bin" / "python"), str(CHECKER)], cwd=tmp_path, text=True, capture_output=True, env=env)


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
    assert "READY_CARD_NOT_ACTIVE" in result.stdout


def test_actual_checker_detects_stale_recorded_head(tmp_path: Path) -> None:
    tmp_path, control, _ = _fixture(tmp_path)
    stale = control.replace("Git HEAD:", "Git HEAD: 0000000 #")
    (tmp_path / "PROJECT_CONTROL.md").write_text(stale)
    result = _run_checker(tmp_path)
    assert result.returncode != 0
    assert "GIT_HEAD_STATE_MISMATCH" in result.stdout
