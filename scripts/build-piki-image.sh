#!/usr/bin/env bash
# Build the piki sandbox image used by --sandbox docker/podman.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIKI_ROOT="${PIKI_ROOT:-${REPO_ROOT}/../piki}"
IMAGE_TAG="${IMAGE_TAG:-sd-hwe-bench-piki:latest}"

if [[ ! -d "${PIKI_ROOT}" ]]; then
    echo "Error: piki repo not found at ${PIKI_ROOT}"
    echo "Set PIKI_ROOT to the piki repository root."
    exit 1
fi

echo "Building piki sandbox image from ${PIKI_ROOT} ..."
docker build \
    -f "${REPO_ROOT}/Containerfile" \
    -t "${IMAGE_TAG}" \
    "${PIKI_ROOT}"

echo "Built ${IMAGE_TAG}"
