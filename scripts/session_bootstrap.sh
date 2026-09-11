#!/usr/bin/env bash
set -u

# TraID safe session bootstrap.
# Read-only by design: verifies repository, Harness, state, environment,
# tests, and basic secret hygiene. It does not modify project files.

PASS=0
WARN=0
FAIL=0

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)" || exit 1
cd -- "$PROJECT_ROOT" || exit 1

say()  { printf "%s\n" "$*"; }
ok()   { PASS=$((PASS+1)); say "PASS  $*"; }
warn() { WARN=$((WARN+1)); say "WARN  $*"; }
fail() { FAIL=$((FAIL+1)); say "FAIL  $*"; }

say "TRAID_SESSION_BOOTSTRAP"
say "======================="
say "INFO  project_root=$PROJECT_ROOT"

# 1. Canonical TraID Harness presence
CANONICAL_FILES=(
  "AGENTS.md"
  "PROJECT_PROFILE.md"
  "PROJECT_CONTROL.md"
  "TRAID_V1_ROADMAP.md"
  "TRAID_CARD_SPECIFICATIONS.md"
  "TRAID_CARD_EVIDENCE_MAP.md"
  "GIT_WORKFLOW.md"
  "TRAID_ENGINEERING_HARNESS.md"
  "FINANCIAL_AND_DATA_GUARDRAILS.md"
  ".agents/skills/traid-card-execution/SKILL.md"
)

for f in "${CANONICAL_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    ok "canonical file exists: $f"
  else
    fail "canonical file missing: $f"
  fi
done

# 2. Git repository state
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH="$(git branch --show-current 2>/dev/null || true)"
  HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
  STATUS="$(git status --short 2>/dev/null || true)"

  ok "git repository detected"
  say "INFO  branch=${BRANCH:-DETACHED_OR_UNKNOWN}"
  say "INFO  head=${HEAD_SHA:-UNKNOWN}"

  if [[ -z "$STATUS" ]]; then
    ok "working tree clean"
  else
    warn "working tree has changes"
    printf "%s\n" "$STATUS"
  fi
else
  fail "not inside a Git work tree"
fi

# 3. Python/runtime availability
if command -v python3 >/dev/null 2>&1; then
  PYVER="$(python3 -c 'import sys; print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || true)"
  ok "python3 available: ${PYVER:-unknown}"
else
  fail "python3 not found"
fi

# 4. Project package/config state
if [[ -f "pyproject.toml" ]]; then
  ok "pyproject.toml present"
else
  warn "pyproject.toml not present yet"
fi

# 5. Tests — collect only; do not execute the suite here
if [[ -d "tests" ]]; then
  ok "tests directory present"

  if command -v pytest >/dev/null 2>&1; then
    TMP_COLLECT="$(mktemp "${TMPDIR:-/tmp}/traid_pytest_collect.XXXXXX")"
    if pytest --collect-only -q >"$TMP_COLLECT" 2>&1; then
      ok "pytest collection succeeds"
    else
      fail "pytest collection failed"
      tail -n 40 "$TMP_COLLECT" || true
    fi
    rm -f "$TMP_COLLECT"
  else
    warn "pytest command not installed in current environment"
  fi
else
  warn "tests directory not present yet"
fi

# 6. Basic secret hygiene signals
if [[ -f ".env" ]]; then
  warn ".env exists locally; verify it is ignored and contains no committed secrets"
fi

if [[ -f ".gitignore" ]]; then
  if grep -Eq '(^|/)\.env($|[[:space:]])|^\.env$|^\.env\*' .gitignore; then
    ok ".gitignore appears to ignore .env"
  else
    warn ".gitignore does not visibly ignore .env"
  fi
else
  warn ".gitignore not present yet"
fi

# 7. Detect obvious tracked secret-file hazards without reading secret contents
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  TRACKED_SECRET_FILES="$(git ls-files 2>/dev/null | grep -E '(^|/)(\.env|\.env\..+|.*\.pem|.*\.key)$' || true)"
  if [[ -n "$TRACKED_SECRET_FILES" ]]; then
    fail "potential secret-bearing files are tracked by Git"
    printf "%s\n" "$TRACKED_SECRET_FILES"
  else
    ok "no obvious secret-bearing filenames detected in tracked files"
  fi
fi

# 8. PROJECT_CONTROL state hints
if [[ -f "PROJECT_CONTROL.md" ]]; then
  ok "PROJECT_CONTROL.md readable"

  ACTIVE_CARD_LINE="$(grep -E -m1 '^[[:space:]]*(\*\*)?Active Card(\*\*)?[[:space:]]*:' PROJECT_CONTROL.md || true)"
  NEXT_AUTH_LINE="$(grep -E -m1 '^[[:space:]]*(\*\*)?Next Card Authorized(\*\*)?[[:space:]]*:' PROJECT_CONTROL.md || true)"
  IMPLEMENT_AUTH_LINE="$(grep -E -m1 '^[[:space:]]*(\*\*)?Implementation Authorization(\*\*)?[[:space:]]*:' PROJECT_CONTROL.md || true)"

  [[ -n "$ACTIVE_CARD_LINE" ]] && say "INFO  ${ACTIVE_CARD_LINE}"
  [[ -n "$NEXT_AUTH_LINE" ]] && say "INFO  ${NEXT_AUTH_LINE}"
  [[ -n "$IMPLEMENT_AUTH_LINE" ]] && say "INFO  ${IMPLEMENT_AUTH_LINE}"

  if grep -Eq 'Active Card(\*\*)?[[:space:]]*:[[:space:]]*NONE' PROJECT_CONTROL.md; then
    say "INFO  PROJECT_CONTROL reports Active Card: NONE"
  fi

  if grep -Eq 'Next Card Authorized(\*\*)?[[:space:]]*:[[:space:]]*NO' PROJECT_CONTROL.md; then
    say "INFO  next Card is not authorized"
  fi
fi

# 9. Guard against accidental implementation start when control says no active Card
if [[ -f "PROJECT_CONTROL.md" ]]; then
  if grep -Eq 'Active Card(\*\*)?[[:space:]]*:[[:space:]]*NONE' PROJECT_CONTROL.md; then
    ok "no Active Card is currently declared"
  else
    warn "PROJECT_CONTROL does not clearly report Active Card: NONE; agent must resolve the exact active Card before writing"
  fi
fi

say
say "SUMMARY"
say "PASS=$PASS WARN=$WARN FAIL=$FAIL"

if [[ "$FAIL" -gt 0 ]]; then
  say "TRAID_SESSION_BOOTSTRAP: BLOCKED"
  exit 1
fi

say "TRAID_SESSION_BOOTSTRAP: PASS_WITH_${WARN}_WARNINGS"
exit 0
