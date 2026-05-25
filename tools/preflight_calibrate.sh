#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIER="${1:-tier1}"
TEST_SUBSET="${TEST_SUBSET:-}"
VARIANT="${S3RL_IMAGE_VARIANT:-standard}"
VERSION="${VERSION:-0.3.0}"
WORK_DIR="$(mktemp -d -t s3rl-preflight-XXXXXX)"

cd "${REPO_ROOT}"

if [[ "$VARIANT" == "mitm" ]]; then
    BASE_TAG="aws-cli-s3-shared:mitm-${VERSION}"
    ENTRYPOINT_BIN="/usr/local/bin/entrypoint-mitm.sh"
    HEALTHCHECK_BIN="/usr/local/bin/moto-mitm-check"
    TIER_TAG="aws-cli-s3-${TIER}:mitm-preflight"
else
    BASE_TAG="aws-cli-s3-shared:${VERSION}"
    ENTRYPOINT_BIN="/usr/local/bin/entrypoint.sh"
    HEALTHCHECK_BIN="/usr/local/bin/moto-check"
    TIER_TAG="aws-cli-s3-${TIER}:preflight"
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

if [[ -z "$TEST_SUBSET" ]]; then
    case "$TIER" in
        tier1) TEST_SUBSET="train/test_mb.py::test_mb_stdout_state_happy_path train/test_mb.py::test_mb_invalid_uri_no_prefix train/test_rb.py::test_rb_stdout_state_removes_empty_bucket eval/test_mb_eval.py::test_mb_isomorphic_stdout" ;;
        tier2) TEST_SUBSET="train/test_mb.py train/test_cp_local_s3.py::test_cp_upload_stdout_state train/test_ls.py::test_ls_objects_show_basename train/test_rm.py::test_rm_stdout_state eval/test_cp_eval.py::test_cp_upload_isomorphic_state" ;;
        tier3) TEST_SUBSET="train/test_cp_single.py train/test_mv.py::test_mv_stdout_state train/test_uri_parsing.py train/test_human_readable.py 2>/dev/null || true ; train/test_filters.py" ;;
    esac
fi

mkdir -p "${WORK_DIR}/logs/verifier" "${WORK_DIR}/logs/agent"
chmod 777 "${WORK_DIR}/logs/verifier" "${WORK_DIR}/logs/agent"
CONTAINER="s3rl-preflight-${TIER}-${VARIANT}-$$"

docker run -d --rm \
    --name "${CONTAINER}" \
    -v "${REPO_ROOT}/${TIER}/tests:/tests:ro" \
    -v "${REPO_ROOT}/${TIER}/solution:/solution:ro" \
    -v "${WORK_DIR}/logs:/logs" \
    "$TIER_TAG" \
    bash -c "${ENTRYPOINT_BIN} sleep 300"

trap "docker rm -f ${CONTAINER} >/dev/null 2>&1 || true; rm -rf ${WORK_DIR}" EXIT

for _ in $(seq 1 30); do
    docker exec "${CONTAINER}" "$HEALTHCHECK_BIN" 2>/dev/null && break
    sleep 0.5
done

echo "==> Preflight: solving oracle"
docker exec "${CONTAINER}" bash /solution/solve.sh >/dev/null

echo "==> Preflight: running ${TIER} subset (${VARIANT}): ${TEST_SUBSET}"
docker exec "${CONTAINER}" bash -c "
    PYTHONPATH=/opt/s3rl-verifier:\${PYTHONPATH:-} \
    pytest /tests/${TEST_SUBSET} -v --tb=line 2>&1 | tail -30
"

echo ""
echo "==> Preflight calibration complete (variant=${VARIANT}, tier=${TIER})"
echo "    Expected: ALL listed tests pass against oracle."
echo "    If any failed, the test's assertions are too strict for moto + real aws-cli."
echo "    Fix the test, not the agent."
