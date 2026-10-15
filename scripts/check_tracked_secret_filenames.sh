#!/usr/bin/env bash
set -euo pipefail

# Permit the safe committed template .env.example while rejecting real secret
# files and private-key material by filename.
tracked_files="$(git ls-files)"
scan_status=0
printf '%s\n' "$tracked_files" | grep -Eq '(^|/)(\.env|.*\.(pem|key))$' || scan_status=$?
case "$scan_status" in
  0)
    echo "tracked secret-bearing filename detected" >&2
    exit 1
    ;;
  1) ;; # Filename scanning completed without a forbidden name.
  *)
    echo "tracked filename scan failed: scan command exited with status $scan_status" >&2
    exit 1
    ;;
esac
