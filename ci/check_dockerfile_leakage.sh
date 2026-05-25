#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORBIDDEN_RE='COPY[[:space:]]+(\./)?(tests|solution|instruction\.md)'
EXIT=0

for f in "${REPO_ROOT}"/shared/Dockerfile "${REPO_ROOT}"/tier*/environment/Dockerfile; do
    [ -f "$f" ] || continue
    if grep -E "${FORBIDDEN_RE}" "$f" >/dev/null; then
        echo "FAIL: $f contains forbidden COPY of tests/solution/instruction" >&2
        grep -nE "${FORBIDDEN_RE}" "$f" >&2
        EXIT=1
    fi
done

if [ ${EXIT} -eq 0 ]; then
    echo "OK: no Dockerfile leaks tests/solution/instruction"
fi
exit ${EXIT}
