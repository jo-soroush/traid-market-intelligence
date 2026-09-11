#!/usr/bin/env bash
set -euo pipefail

# C01 baseline: deterministic checks for obvious tracked secret hazards.
tracked_files="$(git ls-files)"
if printf '%s\n' "$tracked_files" | grep -Eq '(^|/)(\.env|.*\.(pem|key))$'; then
  echo "tracked secret-bearing filename detected" >&2
  exit 1
fi

if rg -n --hidden -g '!.git/**' -g '!docs/**' -g '!*.md' \
  'AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{20,}' .; then
  echo "obvious credential material detected" >&2
  exit 1
fi

echo "secret scan passed: no obvious tracked secret or credential pattern"
