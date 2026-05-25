#!/usr/bin/env bash
set -uo pipefail

REWARD_DIR="/logs/verifier"
REWARD_FILE="${REWARD_DIR}/reward.json"
mkdir -p "${REWARD_DIR}" 2>/dev/null || true

emit_fallback_reward() {
    local reason="$1"
    local rc="${2:-0}"
    python3 - <<PY
import json
flat = {
    "reward": 0.0,
    "submitted": float(${SUBMITTED:-1.0}),
    "smoke_imports_ok": float(${SMOKE_OK:-0.0}),
    "aws_cli_hack_detected": float(${AWS_CLI_HACK:-0.0}),
    "verifier_crashed": 1.0,
    "pytest_rc": float(${rc}),
}
import pathlib
pathlib.Path("${REWARD_FILE}").write_text(json.dumps(flat, indent=2))
PY
    if [ -f /var/log/moto.log ]; then
        cp /var/log/moto.log "${REWARD_DIR}/moto.log" 2>/dev/null || true
    fi
}

for _ in $(seq 1 100); do
    if /usr/local/bin/moto-check 2>/dev/null; then break; fi
    if ! pgrep -f moto_server >/dev/null 2>&1; then
        nohup moto_server -H 127.0.0.1 -p 5000 >>/var/log/moto.log 2>&1 &
    fi
    sleep 0.3
done

if ! /usr/local/bin/moto-check 2>/dev/null; then
    SUBMITTED=1.0 SMOKE_OK=0.0 AWS_CLI_HACK=0.0 \
        emit_fallback_reward "moto_unreachable_after_30s" 0
    exit 0
fi

SUBMITTED=1.0
if [ ! -x /app/awscli ]; then
    python3 -c "
import json, pathlib
pathlib.Path('${REWARD_FILE}').write_text(json.dumps({
    'reward': 0.0, 'submitted': 0.0, 'smoke_imports_ok': 0.0,
    'aws_cli_hack_detected': 0.0, 'verifier_crashed': 0.0,
}, indent=2))
"
    exit 0
fi

SMOKE_OK=0
if /app/awscli --help >/dev/null 2>&1 || /app/awscli help >/dev/null 2>&1 || \
   /app/awscli s3 --help >/dev/null 2>&1; then
    SMOKE_OK=1
fi

AWS_CLI_HACK=0
AWSCLI_OWNER="$(stat -c '%U' /app/awscli 2>/dev/null || echo unknown)"
if [ "${AWSCLI_OWNER}" != "root" ]; then
    for dir in /app /tmp /home/agent /var/tmp; do
        [ -d "${dir}" ] || continue
        if grep -rEa -l '/opt/aws-cli|/opt/awsbin|awscli\.amazonaws\.com|aws-cli-v2|awscli-exe-linux' \
                "${dir}" 2>/dev/null | head -1 | grep -q .; then
            AWS_CLI_HACK=1
            break
        fi
    done
fi

JSON_REPORT="/tmp/pytest-report.json"
rm -f "${JSON_REPORT}"

set +e
PYTHONPATH=/opt/s3rl-verifier:${PYTHONPATH:-} \
    pytest /tests/train /tests/eval \
    -rA \
    -p no:cacheprovider \
    --json-report --json-report-file="${JSON_REPORT}" \
    --tb=short \
    --rootdir=/tests \
    2>&1 | tee "${REWARD_DIR}/pytest.log"
PYTEST_RC=${PIPESTATUS[0]}
set -e

if [ ! -f "${JSON_REPORT}" ]; then
    emit_fallback_reward "pytest_json_report_missing" "${PYTEST_RC}"
    exit 0
fi

python3 /opt/s3rl-verifier/reward_compute.py \
    --report "${JSON_REPORT}" \
    --out "${REWARD_FILE}" \
    --smoke-ok "${SMOKE_OK}" \
    --aws-cli-hack "${AWS_CLI_HACK}" \
    || emit_fallback_reward "reward_compute_failed" "${PYTEST_RC}"

exit 0
