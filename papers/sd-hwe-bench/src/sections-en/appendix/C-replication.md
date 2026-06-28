# Appendix C: Replication Guide

## C.1 Environment Setup

### Dependencies

- Python 3.11+
- Docker (for containerized piki check execution)
- Use `uv` for Python dependency management

```bash
git clone <repo-url> sd-hwe-bench
cd sd-hwe-bench
uv sync
```

### Build piki Container Image

```bash
docker build -t sd-hwe-bench-piki:latest -f docker/Dockerfile.piki .
```

Verify:

```bash
uv run sd-hwe-bench list
```

## C.2 Scoring a Single Task

```bash
# List all tasks
uv run sd-hwe-bench list

# Score an existing solution directly
uv run sd-hwe-bench score telecom/comprehensive-001 tasks/telecom/comprehensive-001/solution/

# Run an agent to generate and score
uv run sd-hwe-bench run telecom/comprehensive-001 --actor codex
```

## C.3 Batch Baseline Experiments

```bash
# All tasks, pass@1, no repair
uv run sd-hwe-bench run --all --actor codex --passes 1

# With parallelism
uv run sd-hwe-bench run --all --actor codex --passes 1 --jobs 4

# Repair loop ablation
uv run sd-hwe-bench run-repair telecom/comprehensive-001 --actor codex --max-repair 5
```

Results are written to `runs/`.

## C.4 Leaderboard Generation

```bash
# Archive results from runs/ and update leaderboard
uv run sd-hwe-bench leaderboard --update

# View current leaderboard
uv run sd-hwe-bench leaderboard
```

## C.5 Data and Code

- Task dataset: `tasks/telecom/` (33 tasks)
- Canonical engineering source: `canonical/` (3 projects)
- Evaluation framework: `src/sd_hwe_bench/`
- DTS rule configuration: `src/sd_hwe_bench/config/rule_layers.yaml`
