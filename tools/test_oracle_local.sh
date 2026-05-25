#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIER="${1:-tier1}"
VARIANT="${S3RL_IMAGE_VARIANT:-standard}"
VERSION="${VERSION:-0.3.0}"
WORK_DIR="$(mktemp -d -t s3rl-oracle-XXXXXX)"

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

echo "==> variant=${VARIANT}  base=${BASE_TAG}  tier=${TIER}"

if ! docker image inspect "$BASE_TAG" >/dev/null 2>&1; then
    echo "==> Base image $BASE_TAG missing — building"
    if [[ "$VARIANT" == "mitm" ]]; then
        bash tools/build_shared_image.sh --mitm
    else
        bash tools/build_shared_image.sh
    fi
fi

echo "==> Building ${TIER} image (BASE_IMAGE=$BASE_TAG)"
docker build \
    --build-arg "BASE_IMAGE=$BASE_TAG" \
    -f "${TIER}/environment/Dockerfile" \
    -t "$TIER_TAG" \
    "${TIER}/"

mkdir -p "${WORK_DIR}/logs/verifier" "${WORK_DIR}/logs/agent"
chmod 777 "${WORK_DIR}/logs/verifier" "${WORK_DIR}/logs/agent"

CONTAINER="s3rl-oracle-${TIER}-${VARIANT}-$$"

echo "==> Starting container"
docker run -d --rm \
    --name "${CONTAINER}" \
    -v "${REPO_ROOT}/${TIER}/tests:/tests:ro" \
    -v "${REPO_ROOT}/${TIER}/solution:/solution:ro" \
    -v "${WORK_DIR}/logs:/logs" \
    "$TIER_TAG" \
    bash -c "${ENTRYPOINT_BIN} sleep 600"

trap "docker rm -f ${CONTAINER} >/dev/null 2>&1 || true; rm -rf ${WORK_DIR}" EXIT

echo "==> Waiting for ${VARIANT} services (moto $( [[ $VARIANT == mitm ]] && echo '+ mitmdump'))"
for _ in $(seq 1 40); do
    if docker exec "${CONTAINER}" "$HEALTHCHECK_BIN" 2>/dev/null; then
        break
    fi
    sleep 0.5
done

if ! docker exec "${CONTAINER}" "$HEALTHCHECK_BIN" 2>/dev/null; then
    echo "FAIL: services never became healthy" >&2
    docker exec "${CONTAINER}" cat /var/log/moto.log     2>/dev/null || true
    docker exec "${CONTAINER}" cat /var/log/mitmdump.log 2>/dev/null || true
    exit 1
fi

echo "==> Running oracle solve.sh"
docker exec "${CONTAINER}" bash /solution/solve.sh

echo "==> Verifying /app/awscli"
docker exec "${CONTAINER}" ls -la /app/awscli

echo "==> Running test.sh"
docker exec "${CONTAINER}" bash /tests/test.sh

echo "==> Reading reward.json"
if [ ! -f "${WORK_DIR}/logs/verifier/reward.json" ]; then
    echo "FAIL: reward.json not produced" >&2
    docker exec "${CONTAINER}" cat /var/log/moto.log     2>/dev/null || true
    docker exec "${CONTAINER}" cat /var/log/mitmdump.log 2>/dev/null || true
    exit 1
fi

cat "${WORK_DIR}/logs/verifier/reward.json"

echo ""
echo "==> Asserting reward >= 0.98"
python3 -c "
import json
data = json.load(open('${WORK_DIR}/logs/verifier/reward.json'))
reward = data.get('reward', 0.0)
if reward < 0.98:
    print(f'FAIL: oracle reward {reward:.4f} < 0.98  (variant=${VARIANT})')
    raise SystemExit(1)
print(f'PASS: oracle reward {reward:.4f}  (variant=${VARIANT})')
"
