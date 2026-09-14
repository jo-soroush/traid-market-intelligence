from __future__ import annotations

import subprocess
from pathlib import Path


HELPER = Path(__file__).parents[1] / "scripts" / "check_tracked_secret_filenames.sh"
CHECK_SECRETS = Path(__file__).parents[1] / "scripts" / "check_secrets.sh"


def run_filename_check(tmp_path: Path, filename: str) -> subprocess.CompletedProcess[str]:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("placeholder\n")
    subprocess.run(["git", "add", filename], cwd=tmp_path, check=True)
    return subprocess.run([str(HELPER)], cwd=tmp_path, text=True, capture_output=True, check=False)


def test_env_example_is_allowed(tmp_path: Path) -> None:
    result = run_filename_check(tmp_path, ".env.example")
    assert result.returncode == 0


def test_real_env_file_is_blocked(tmp_path: Path) -> None:
    result = run_filename_check(tmp_path, ".env")
    assert result.returncode != 0


def test_private_key_file_is_blocked(tmp_path: Path) -> None:
    result = run_filename_check(tmp_path, "secrets/private.key")
    assert result.returncode != 0


def test_secret_scan_resolves_repository_when_called_outside_root(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS)], cwd=tmp_path, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0
