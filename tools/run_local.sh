#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIER="${1:-tier1}"

cd "${REPO_ROOT}"

if ! docker image inspect aws-cli-s3-shared:0.3.0 >/dev/null 2>&1; then
    tools/build_shared_image.sh
fi

docker build -f "${TIER}/environment/Dockerfile" -t "aws-cli-s3-${TIER}:local" "${TIER}/"

docker run --rm -it \
    -v "${REPO_ROOT}/${TIER}/tests:/tests:ro" \
    -v "${REPO_ROOT}/${TIER}/solution:/solution:ro" \
    -v "${REPO_ROOT}/${TIER}/instruction.md:/app/instruction.md:ro" \
    -v "/tmp/${TIER}-logs:/logs" \
    "aws-cli-s3-${TIER}:local" \
    bash
