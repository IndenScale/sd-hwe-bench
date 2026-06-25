#!/usr/bin/env bash
# Build the piki sandbox image used by --sandbox docker/podman.
#
# Environment variables:
#   PIKI_ROOT             Path to the piki repository root (default: ../piki)
#   IMAGE_TAG             Image tag to build (default: ${SD_HWE_SANDBOX_IMAGE})
#   SD_HWE_SANDBOX_IMAGE  Fallback image tag if IMAGE_TAG is unset
#   CONTAINER_RUNTIME     docker or podman (default: docker)
#
# Arguments:
#   --tag <tag>           Override IMAGE_TAG
#   --runtime <runtime>   Override CONTAINER_RUNTIME

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIKI_ROOT="${PIKI_ROOT:-${REPO_ROOT}/../piki}"
DEFAULT_IMAGE_TAG="${SD_HWE_SANDBOX_IMAGE:-sd-hwe-bench-piki:latest}"
IMAGE_TAG="${IMAGE_TAG:-${DEFAULT_IMAGE_TAG}}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

# Parse optional arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --runtime)
            CONTAINER_RUNTIME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--tag <image-tag>] [--runtime <docker|podman>]" >&2
            exit 1
            ;;
    esac
done

if [[ ! -d "${PIKI_ROOT}" ]]; then
    echo "Error: piki repo not found at ${PIKI_ROOT}"
    echo "Set PIKI_ROOT to the piki repository root."
    exit 1
fi

if ! command -v "${CONTAINER_RUNTIME}" &>/dev/null; then
    echo "Error: ${CONTAINER_RUNTIME} not found in PATH"
    exit 1
fi

echo "Building piki sandbox image from ${PIKI_ROOT} with ${CONTAINER_RUNTIME} ..."
"${CONTAINER_RUNTIME}" build \
    -f "${REPO_ROOT}/Containerfile" \
    -t "${IMAGE_TAG}" \
    "${PIKI_ROOT}"

echo "Built ${IMAGE_TAG}"
