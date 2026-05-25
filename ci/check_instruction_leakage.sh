#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORBIDDEN='moto|/tests/|/solution/|pytest|conftest|test_mb|test_rb|test_cp|test_ls|test_mv|test_rm|reward\.json|reward_compute'
EXIT=0

for f in "${REPO_ROOT}"/tier*/instruction.md; do
    [ -f "$f" ] || continue
    if grep -iE "${FORBIDDEN}" "$f" >/dev/null; then
        echo "FAIL: $f leaks test internals" >&2
        grep -niE "${FORBIDDEN}" "$f" >&2
        EXIT=1
    fi
done

if [ ${EXIT} -eq 0 ]; then
    echo "OK: no instruction.md leaks test internals"
fi
exit ${EXIT}
