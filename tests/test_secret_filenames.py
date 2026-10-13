from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


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


def secret_scan_repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    scripts = repo / "scripts"
    scripts.mkdir()
    for source in (HELPER, CHECK_SECRETS):
        shutil.copy2(source, scripts / source.name)
    (repo / "clean.txt").write_text("ordinary content\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    return repo


def run_secret_scan(repo: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(repo / "scripts" / CHECK_SECRETS.name)],
        cwd=repo.parent, env=env, text=True, capture_output=True, check=False,
    )


def add_scan_content(repo: Path, filename: str, content: str) -> None:
    target = repo / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content + "\n")
    subprocess.run(["git", "add", "--", filename], cwd=repo, check=True)


def test_clean_tracked_content_passes_secret_scan(tmp_path: Path) -> None:
    result = run_secret_scan(secret_scan_repository(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "secret scan passed" in result.stdout


@pytest.mark.parametrize("kind", ["aws", "api", "private", "rsa", "ec", "openssh"])
def test_tracked_secret_content_fails(tmp_path: Path, kind: str) -> None:
    repo = secret_scan_repository(tmp_path)
    if kind == "aws":
        content = "AK" + "IA" + "A" * 16
    elif kind == "api":
        content = "sk" + "-" + "a" * 20
    else:
        prefix = "" if kind == "private" else kind.upper() + " "
        content = "-----BEGIN " + prefix + "PRIVATE KEY" + "-----"
    add_scan_content(repo, "nested/.hidden.txt", content)
    result = run_secret_scan(repo)
    assert result.returncode != 0
    assert "obvious credential material detected" in result.stderr
    assert "secret scan passed" not in result.stdout


@pytest.mark.parametrize("filename", ["docs/sample.txt", "docs/nested/sample.txt", "README.md", "nested/readme.md"])
def test_secret_content_exclusions_are_preserved(tmp_path: Path, filename: str) -> None:
    repo = secret_scan_repository(tmp_path)
    add_scan_content(repo, filename, "sk" + "-" + "a" * 20)
    result = run_secret_scan(repo)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("status", [2, 127, 128])
def test_scan_command_error_never_reports_pass(tmp_path: Path, status: int) -> None:
    repo = secret_scan_repository(tmp_path)
    tools = tmp_path / "tools"
    tools.mkdir()
    real_git = shutil.which("git")
    assert real_git is not None
    wrapper = tools / "git"
    # Keep filename enumeration real; inject a failure specifically at content scanning.
    wrapper.write_text(
        f'#!/bin/bash\nif [ "$1" = grep ]; then exit {status}; fi\n'
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    result = run_secret_scan(repo, env={**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]})
    assert result.returncode != 0
    assert f"git grep exited with status {status}" in result.stderr
    assert "secret scan passed" not in result.stdout


def test_missing_git_never_reports_pass(tmp_path: Path) -> None:
    repo = secret_scan_repository(tmp_path)
    tools = tmp_path / "tools"
    tools.mkdir()
    for command in ("bash", "dirname", "grep"):
        executable = shutil.which(command)
        assert executable is not None
        (tools / command).symlink_to(executable)
    result = run_secret_scan(repo, env={**os.environ, "PATH": str(tools)})
    assert result.returncode != 0
    assert "git: command not found" in result.stderr
    assert "secret scan passed" not in result.stdout


def test_clean_scan_does_not_require_rg(tmp_path: Path) -> None:
    repo = secret_scan_repository(tmp_path)
    tools = tmp_path / "tools"
    tools.mkdir()
    for command in ("bash", "dirname", "grep", "git"):
        executable = shutil.which(command)
        assert executable is not None
        (tools / command).symlink_to(executable)
    result = run_secret_scan(repo, env={**os.environ, "PATH": str(tools)})
    assert result.returncode == 0, result.stderr
    assert "secret scan passed" in result.stdout


def test_modified_tracked_content_is_scanned(tmp_path: Path) -> None:
    repo = secret_scan_repository(tmp_path)
    (repo / "clean.txt").write_text("sk" + "-" + "a" * 20 + "\n")
    result = run_secret_scan(repo)
    assert result.returncode != 0
    assert "obvious credential material detected" in result.stderr
    assert "secret scan passed" not in result.stdout


def test_repository_failure_never_reports_pass(tmp_path: Path) -> None:
    repo = secret_scan_repository(tmp_path)
    shutil.rmtree(repo / ".git")
    result = run_secret_scan(repo, env={**os.environ, "GIT_CEILING_DIRECTORIES": str(repo.parent)})
    assert result.returncode != 0
    assert "not a git repository" in result.stderr.lower()
    assert "secret scan passed" not in result.stdout


@pytest.mark.parametrize("filename", [".env", "docs/private.key", "keys/private.pem"])
def test_filename_check_still_blocks_secret_files(tmp_path: Path, filename: str) -> None:
    repo = secret_scan_repository(tmp_path)
    add_scan_content(repo, filename, "ordinary content")
    result = run_secret_scan(repo)
    assert result.returncode != 0
    assert "tracked secret-bearing filename detected" in result.stderr
    assert "secret scan passed" not in result.stdout
