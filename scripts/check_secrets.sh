#!/usr/bin/env bash
set -euo pipefail

# C01 baseline: deterministic checks for obvious tracked secret hazards.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd -- "$PROJECT_ROOT"

"$SCRIPT_DIR/check_tracked_secret_filenames.sh"

if rg -n --hidden -g '!.git/**' -g '!docs/**' -g '!*.md' \
  'AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{20,}' .; then
  echo "obvious credential material detected" >&2
  exit 1
fi

echo "secret scan passed: no obvious tracked secret or credential pattern"
