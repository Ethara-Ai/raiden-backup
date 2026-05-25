#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VERSION="${VERSION:-0.3.0}"
REPO_NAME="${REPO_NAME:-aws-cli-s3-shared}"

VARIANT=standard
MULTI_ARCH=0
PUSH_REGISTRY=""
PLATFORMS=""
BUILDER_NAME="${BUILDX_BUILDER:-aws-cli-s3-builder}"

usage() {
    cat <<'EOF'
Usage: build_shared_image.sh [options]

Options:
    --mitm                 Build the mitmproxy variant (default: standard)
    --multi-arch           Build linux/amd64 + linux/arm64 manifest list via buildx
                           (cannot --load; image cached locally OR pushed with --push)
    --platform PLATFORMS   Override platforms (default: linux/amd64,linux/arm64).
                           Implies --multi-arch.
    --push REGISTRY        Push to registry (e.g. ghcr.io/your-org).
                           Required for --multi-arch if you want to pull it back.
    -h, --help             This help

Tag scheme:
    standard      ->  aws-cli-s3-shared:<VERSION>
    mitm          ->  aws-cli-s3-shared:mitm-<VERSION>

Env overrides:
    VERSION           default 0.3.0
    REPO_NAME         default aws-cli-s3-shared
    BUILDX_BUILDER    default aws-cli-s3-builder

Examples:
    # Native host arch only (loads into local Docker)
    ./build_shared_image.sh
    ./build_shared_image.sh --mitm

    # Multi-arch verification build (no load, just builds for both platforms)
    ./build_shared_image.sh --multi-arch
    ./build_shared_image.sh --multi-arch --mitm

    # Multi-arch push to your registry
    ./build_shared_image.sh --multi-arch          --push ghcr.io/myorg
    ./build_shared_image.sh --multi-arch --mitm   --push ghcr.io/myorg
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mitm)         VARIANT=mitm; shift ;;
        --multi-arch)   MULTI_ARCH=1; shift ;;
        --platform)     PLATFORMS="$2"; MULTI_ARCH=1; shift 2 ;;
        --push)         PUSH_REGISTRY="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ "$VARIANT" == "mitm" ]]; then
    TAG_SUFFIX="mitm-"
else
    TAG_SUFFIX=""
fi

LOCAL_TAG="${REPO_NAME}:${TAG_SUFFIX}${VERSION}"
if [[ -n "$PUSH_REGISTRY" ]]; then
    REMOTE_TAG="${PUSH_REGISTRY}/${REPO_NAME}:${TAG_SUFFIX}${VERSION}"
else
    REMOTE_TAG=""
fi

if [[ "$MULTI_ARCH" -eq 1 ]]; then
    PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"

    if ! docker buildx inspect "$BUILDER_NAME" >/dev/null 2>&1; then
        echo "==> Creating buildx builder '$BUILDER_NAME' (docker-container driver)"
        docker buildx create --name "$BUILDER_NAME" --driver docker-container --use >/dev/null
        docker buildx inspect --bootstrap "$BUILDER_NAME" >/dev/null
    else
        docker buildx use "$BUILDER_NAME"
    fi

    OUTPUT_FLAGS=()
    TAGS=("--tag" "$LOCAL_TAG")
    if [[ -n "$REMOTE_TAG" ]]; then
        TAGS+=("--tag" "$REMOTE_TAG")
        OUTPUT_FLAGS+=("--push")
    fi

    echo "==> Multi-arch build: variant=${VARIANT}  platforms=${PLATFORMS}"
    echo "    Tags: ${TAGS[*]/--tag /}"
    [[ ${#OUTPUT_FLAGS[@]} -eq 0 ]] && echo "    (no --push; image cached in buildx; cannot be docker pull'd locally)"

    docker buildx build \
        --platform "$PLATFORMS" \
        --target "$VARIANT" \
        -f shared/Dockerfile \
        "${TAGS[@]}" \
        ${OUTPUT_FLAGS[@]+"${OUTPUT_FLAGS[@]}"} \
        .

    echo "==> Multi-arch build OK"
    if [[ -n "$REMOTE_TAG" ]]; then
        echo "==> Pushed: $REMOTE_TAG"
        docker buildx imagetools inspect "$REMOTE_TAG" | head -30 || true
    fi
else
    echo "==> Single-arch build (host-native): variant=${VARIANT}  tag=${LOCAL_TAG}"
    docker build \
        --target "$VARIANT" \
        -f shared/Dockerfile \
        -t "$LOCAL_TAG" \
        .

    if [[ -n "$REMOTE_TAG" ]]; then
        docker tag "$LOCAL_TAG" "$REMOTE_TAG"
        docker push "$REMOTE_TAG"
        echo "==> Pushed: $REMOTE_TAG"
    fi

    echo "==> Built: $LOCAL_TAG"
    docker image ls "$LOCAL_TAG" --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'
fi
