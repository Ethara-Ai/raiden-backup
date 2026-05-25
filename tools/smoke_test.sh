#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "==> Repo structure check"
REQUIRED=(
    README.md
    shared/Dockerfile shared/scripts shared/helpers shared/reward_compute.py shared/test_base.sh
    tier1/task.toml tier1/instruction.md tier1/environment/Dockerfile tier1/tests/test.sh tier1/solution/solve.sh
    tier2/task.toml tier2/instruction.md tier2/environment/Dockerfile tier2/tests/test.sh tier2/solution/solve.sh
    tier3/task.toml tier3/instruction.md tier3/environment/Dockerfile tier3/tests/test.sh tier3/solution/solve.sh
    agents/null_agent/agent.py
    ci/github-actions.yml ci/validate_task_toml.py ci/check_dockerfile_leakage.sh
    ci/check_instruction_leakage.sh ci/assert_reward.py ci/walk_jobs_dir.py ci/check_test_split.py
    docs/DESIGN_RATIONALE.md docs/SCALING.md docs/THREAT_MODEL.md
    docs/KNOWN_DIVERGENCES.md docs/TEST_SPLIT.md docs/TRANSFER_MEASUREMENT.md
)
for p in "${REQUIRED[@]}"; do
    if [ ! -e "${p}" ]; then
        echo "MISSING: ${p}"
        exit 1
    fi
done
echo "  OK"

echo "==> task.toml schema validation"
python3 ci/validate_task_toml.py tier1/task.toml
python3 ci/validate_task_toml.py tier2/task.toml
python3 ci/validate_task_toml.py tier3/task.toml

echo "==> Dockerfile leakage check"
bash ci/check_dockerfile_leakage.sh

echo "==> Instruction leakage check"
bash ci/check_instruction_leakage.sh

echo "==> Test split check"
python3 ci/check_test_split.py

echo "==> Python syntax check on all .py files"
find shared tier1 tier2 tier3 agents ci tools -name '*.py' -print0 \
    | xargs -0 -n1 python3 -m py_compile
echo "  OK"

echo "==> Bash syntax check on all .sh files"
find shared tier1 tier2 tier3 tools ci -name '*.sh' -print0 \
    | xargs -0 -n1 bash -n
echo "  OK"

echo "==> Test count summary"
for tier in tier1 tier2 tier3; do
    train=$(find "${tier}/tests/train" -name 'test_*.py' -exec grep -l '^def test_' {} + 2>/dev/null \
            | xargs grep -c '^def test_' 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
    eval_=$(find "${tier}/tests/eval" -name 'test_*.py' -exec grep -l '^def test_' {} + 2>/dev/null \
            | xargs grep -c '^def test_' 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
    echo "  ${tier}: train=${train} eval=${eval_}"
done

echo "==> All smoke checks passed"
