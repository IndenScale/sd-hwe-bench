#!/bin/bash
# Baseline runner: test gpt-5.1-codex and gemini-2.5-flash on comprehensive-001
set -e

export PIPKIPATH=/Users/indenscale/workspace/piki/.venv/bin/python
cd /Users/indenscale/workspace/sd-hwe-bench

echo "=== SD-HWE-Bench Baseline ==="
echo "Task: telecom/comprehensive-001"
echo ""

# Model 1: gpt-5.1-codex via codex CLI
echo "--- Running: gpt-5.1-codex ---"
.venv/bin/python -m sd_hwe_bench.cli run-agent \
  telecom/comprehensive-001 \
  --driver codex --model gpt-5.1-codex \
  --format markdown \
  --run-dir work/baseline-runs \
  2>&1

echo ""
echo "--- Running: claude-sonnet-4-20250514 ---"
# Model 2: Claude via codex CLI (using anthropic model name)
.venv/bin/python -m sd_hwe_bench.cli run-agent \
  telecom/comprehensive-001 \
  --driver codex --model claude-sonnet-4-20250514 \
  --format markdown \
  --run-dir work/baseline-runs \
  2>&1

echo ""
echo "=== Done ==="
