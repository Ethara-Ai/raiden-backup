#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIER="${1:-tier1}"
VARIANT="${S3RL_IMAGE_VARIANT:-standard}"
VERSION="${VERSION:-0.3.0}"
WORK_DIR="$(mktemp -d -t s3rl-null-XXXXXX)"

cd "${REPO_ROOT}"

if [[ "$VARIANT" == "mitm" ]]; then
    BASE_TAG="aws-cli-s3-shared:mitm-${VERSION}"
    ENTRYPOINT_BIN="/usr/local/bin/entrypoint-mitm.sh"
    HEALTHCHECK_BIN="/usr/local/bin/moto-mitm-check"
    TIER_TAG="aws-cli-s3-${TIER}:mitm-local"
elif [[ "$VARIANT" == "standard" ]]; then
    BASE_TAG="aws-cli-s3-shared:${VERSION}"
    ENTRYPOINT_BIN="/usr/local/bin/entrypoint.sh"
    HEALTHCHECK_BIN="/usr/local/bin/moto-check"
    TIER_TAG="aws-cli-s3-${TIER}:local"
else
    echo "FAIL: S3RL_IMAGE_VARIANT must be 'standard' or 'mitm' (got: $VARIANT)" >&2
    exit 2
fi

if ! docker image inspect "$BASE_TAG" >/dev/null 2>&1; then
    if [[ "$VARIANT" == "mitm" ]]; then
        bash tools/build_shared_image.sh --mitm
    else
        bash tools/build_shared_image.sh
    fi
fi

docker build \
    --build-arg "BASE_IMAGE=$BASE_TAG" \
    -f "${TIER}/environment/Dockerfile" \
    -t "$TIER_TAG" \
    "${TIER}/" >/dev/null

mkdir -p "${WORK_DIR}/logs/verifier" "${WORK_DIR}/logs/agent"
chmod 777 "${WORK_DIR}/logs/verifier" "${WORK_DIR}/logs/agent"

CONTAINER="s3rl-null-${TIER}-${VARIANT}-$$"

docker run -d --rm \
    --name "${CONTAINER}" \
    -v "${REPO_ROOT}/${TIER}/tests:/tests:ro" \
    -v "${WORK_DIR}/logs:/logs" \
    "$TIER_TAG" \
    bash -c "${ENTRYPOINT_BIN} sleep 600"

trap "docker rm -f ${CONTAINER} >/dev/null 2>&1 || true; rm -rf ${WORK_DIR}" EXIT

for _ in $(seq 1 40); do
    if docker exec "${CONTAINER}" "$HEALTHCHECK_BIN" 2>/dev/null; then break; fi
    sleep 0.5
done

echo "==> Simulating null agent (variant=${VARIANT}): writing empty /app/awscli"
docker exec --user agent "${CONTAINER}" bash -c '
printf "#!/bin/sh\nexit 0\n" > /app/awscli && chmod +x /app/awscli
'

echo "==> Running test.sh"
docker exec "${CONTAINER}" bash /tests/test.sh

cat "${WORK_DIR}/logs/verifier/reward.json"
echo ""

python3 -c "
import json
data = json.load(open('${WORK_DIR}/logs/verifier/reward.json'))
reward = data.get('reward', 0.0)
if reward > 0.05:
    print(f'FAIL: null reward {reward:.4f} > 0.05  (variant=${VARIANT})')
    raise SystemExit(1)
print(f'PASS: null reward {reward:.4f}  (variant=${VARIANT})')
"
