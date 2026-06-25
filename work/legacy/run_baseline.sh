#!/usr/bin/env bash
# Legacy baseline runner: run a small set of CLI actors against a single task.
#
# NOTE: This script predates the current `sd-hwe-bench run` CLI. It is kept for
# quick manual smoke tests only. New experiments should use the CLI directly.
#
# Environment variables (all optional):
#   TASK          Task ID to run (default: telecom/comprehensive-001)
#   MODELS        Space-separated actor specs (default: codex:gpt-5.1-codex codex:claude-sonnet-4-20250514)
#   PASSES        Number of independent passes (default: 1)
#   SANDBOX       Sandbox backend: auto|none|docker|podman (default: auto)
#   RUN_DIR       Directory for rollout archives (default: work/baseline-runs)
#
# Example:
#   TASK=telecom/layout-design-001 PASSES=3 ./work/legacy/run_baseline.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TASK="${TASK:-telecom/comprehensive-001}"
MODELS="${MODELS:-codex:gpt-5.1-codex codex:claude-sonnet-4-20250514}"
PASSES="${PASSES:-1}"
SANDBOX="${SANDBOX:-auto}"
RUN_DIR="${RUN_DIR:-work/baseline-runs}"

cd "${REPO_ROOT}"

echo "=== SD-HWE-Bench Baseline ==="
echo "Task: ${TASK}"
echo "Sandbox: ${SANDBOX}"
echo "Passes: ${PASSES}"
echo "Run dir: ${RUN_DIR}"
echo ""

for actor_spec in ${MODELS}; do
    echo "--- Running: ${actor_spec} ---"
    ./.venv/bin/python -m sd_hwe_bench.cli run "${TASK}" \
        --actor "${actor_spec}" \
        --passes "${PASSES}" \
        --sandbox "${SANDBOX}" \
        --run-dir "${RUN_DIR}" \
        2>&1
    echo ""
done

echo "=== Done ==="
echo "Archives: ${RUN_DIR}"
