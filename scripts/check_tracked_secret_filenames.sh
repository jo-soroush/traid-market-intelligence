#!/usr/bin/env bash
set -euo pipefail

# Permit the safe committed template .env.example while rejecting real secret
# files and private-key material by filename.
tracked_files="$(git ls-files)"
if printf '%s\n' "$tracked_files" | grep -Eq '(^|/)(\.env|.*\.(pem|key))$'; then
  echo "tracked secret-bearing filename detected" >&2
  exit 1
fi
