# Legacy experiment runners

> **Status: legacy / deprecated.** These scripts predate the current
> `sd-hwe-bench run` CLI and the centralized `sd_hwe_bench.settings`
> configuration. They are kept as reference / smoke-test examples only.

## Current recommended way

Use the parameterized CLI:

```bash
# Single task, single actor
sd-hwe-bench run telecom/comprehensive-001 --actor kimi:kimi-code/k2.7

# Multiple passes
sd-hwe-bench run telecom/ --actor gemini:gemini-3.1-pro --passes 5

# OpenAI-compatible API actor (DeepSeek, etc.)
sd-hwe-bench run telecom/comprehensive-001 --actor openai:deepseek-chat
```

See `sd-hwe-bench run --help` for all options.

## Files

- `run_baseline.sh` — minimal shell wrapper around `sd-hwe-bench run`. All
  parameters are exposed via environment variables (`TASK`, `MODELS`, `PASSES`,
  `SANDBOX`, `RUN_DIR`).
- `run_cli_baseline.py` and `run_api_baseline.py` — **removed**. They duplicated
  logic already provided by the CLI, contained hardcoded absolute paths, and
  embedded plaintext API credentials. Use the CLI or a thin wrapper around it
  instead.
