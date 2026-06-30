# AIDC v7 baseline rerun memo

Date: 2026-06-30

## Current goal

Stabilize the AIDC v7 baseline workflow before using results in the paper.

We decided not to continue expanding AIDC yet. Current priority is:

1. Make AIDC v7 benchmark runs trustworthy.
2. Rerun valid baseline data.
3. Then sync paper/methodology/leaderboard.

## UPDATE 2026-06-30 (post-rerun, validated)

Status of the three goals:

1. Harness trustworthy — DONE and validated. Full suite `uv run pytest -q`
   => 154 passed, 2 skipped. New `actor_success`/`score_success`/changed-YAML
   counting all populate correctly in the rerun manifests (no more `None`,
   no more files=0 false PASS).

2. Valid Kimi baseline — DONE. Reran the Kimi-only matrix in an isolated
   `/tmp` workspace; results persisted to `runs/aidc-v7-kimi-pass1-20260630/`.
   Trajectories scanned: no reference to the repo path or any `solution/` dir,
   so the contamination path (#6) did not trigger this time.

   | Task | success | actor/score | overall (corrected) | files_written | elapsed |
   |---|---|---|---|---|---|
   | edge-dc-design-001 | PASS | T/T | 1.00 | 25 | 1111s |
   | aidc-60mw-001 | PASS | T/T | 1.00 | 2 | 1791s |
   | aidc-60mw-002 | PASS | T/T | 1.00 | 417 | 1153s |
   | aidc-60mw-003 | PASS | T/T | 1.00 | 3 | 445s |

   Pass@1 = 4/4 = 100%. The runs first reported avg 115%, which an audit traced
   to a SCORING BUG (see below), not a performance bonus. Corrected avg = 100%
   (every task tops out at the real 1.0 ceiling). Manifests in
   `runs/aidc-v7-kimi-pass1-20260630/` were rewritten with the corrected
   `overall_score` (1.0) plus `overall_score_pre_l4fix` for traceability.
   Caveats:
   - The AIDC v7 set does NOT discriminate Kimi — every task tops out at the
     ceiling. Before publishing, decide whether these tasks need harder
     constraints / stricter critics to produce score spread.
   - `aidc-60mw-001` finished at 1791s, ~9s under the 1800s timeout. Bump
     `timeout` for the 60MW tasks before any multi-pass / multi-model run.
   - Isolation is CWD-only: the Kimi CLI is not sandboxed and could still read
     the repo by absolute path if it chose to. Clean this run, but the
     container/external-dataset isolation (below) is still the durable fix.

### SCORING BUG found + fixed: L4 weight double-counted (the spurious 1.15)

Root cause: `PikiCritic` builds `layer_scores` for ALL of L1-L5 and awards a
layer its full weight whenever no piki rule failed it. But `config/rule_layers.yaml`
maps NO rule to L4 (L4 is the dynamic-model layer owned by the analysis critics),
so piki ALWAYS "passes" L4 vacuously and adds `LAYER_WEIGHTS["L4"]=0.15`. Then the
L4 analysis critic (`aidc-performance`/`epc`/`decision`, `mode="replace"`) adds
the same 0.15 again in `_apply_analysis_result`. Result: every passing L4 task =
1.0 + 0.15 = exactly 1.15. (`test_weights_sum_to_one` already asserts the intended
max is 1.0.) Verified empirically by re-scoring: piki loop contributed
`{L1:.1,L2:.15,L3:.4,L4:.15,L5:.2}` AND the L4-Simulation critic added another .15.

Scope: affects ANY task scored with a replace-mode L4 critic (AIDC design /
co-design / conceptual-design / EPC). The PASS/FAIL verdict was never affected
(only `overall_score` arithmetic), so pass@k numbers stand; avg-score numbers
that include L4 tasks are inflated by +0.15 and must be recomputed before the
paper/leaderboard use them.

Fix (`src/sd_hwe_bench/scorer.py`): resolve analysis specs before the piki loop;
for any layer owned by a `replace`-mode analysis critic, skip piki's weight
contribution (the analysis critic is authoritative and adds it once). Merge-mode
layers (L5 constructability) keep piki's weight, since merge only subtracts on
failure. Re-score after fix => all four = 1.0, success unchanged.

Regression test: `tests/test_aidc_simulation_60mw.py` — the four
`*_solution_passes` tests now assert `overall_score == pytest.approx(1.0)`.
Full suite: 154 passed, 2 skipped.

1. Paper/leaderboard sync — NOT done. Still blocked on a DeepSeek baseline
   (now viable via the Claude->DeepSeek path, see below) before the main
   multi-model leaderboard/paper can be updated. Do NOT overwrite
   `leaderboard/results.json` with this kimi-only pass@1. NOTE: the existing
   published leaderboard avg-scores are inflated by the L4 double-count for any
   L4 tasks — recompute them with the fixed scorer before publishing.

DeepSeek baseline path is now viable (was blocked in original memo #5):
`claude` CLI present, `CLAUDE_BASE_URL` defaults to DeepSeek's Anthropic
endpoint, `DEEPSEEK_API_KEY` is set. Matrix ready:
`scripts/batch/aidc-v7-deepseek-flash-pass1.yaml` (claude:deepseek-v4-flash).
Not yet executed.

## What was run

Created initial matrix:

- `scripts/batch/aidc-v7-pass1.yaml`
- Run dir: `runs/aidc-v7-pass1-20260630`
- Matrix: Kimi + DeepSeek-v4-Pro + DeepSeek-v4-Flash over:
  - `telecom/edge-dc-design-001`
  - `telecom/aidc-60mw-001`
  - `telecom/aidc-60mw-002`
  - `telecom/aidc-60mw-003`

Initial raw leaderboard from that run:

| Model | Tasks | Pass@1 | Avg Score |
|---|---:|---:|---:|
| kimi | 4 | 50% | 106% |
| codex:deepseek-v4-pro | 4 | 25% | 102% |
| codex:deepseek-v4-flash | 4 | 25% | 102% |

Do not use this table in the paper yet. It exposed harness/task issues.

## Problems found

1. `expected_files` missing did not fail L0.
   - Example: `aidc-60mw-001` scaffold passed without `strategy.yaml`.
   - This allowed empty/no-diff rollouts to pass if scaffold already satisfied analysis critics.

2. `files_written` only counted newly added YAML files.
   - It missed modified existing YAML files.
   - AIDC lineage tasks often require editing existing files, so `files_written=0` was ambiguous.

3. Actor success ignored process exit code.
   - Codex CLI unsupported-model/auth failures were treated as actor success if the process returned output.
   - Kimi auth/login failure text could also be recorded as success.

4. `success` in manifest only reflected score success.
   - Actor failure plus scaffold passing could become a false PASS.

5. The initial Codex DeepSeek actor specs are not valid in the current Codex CLI context.
   - `codex exec -m deepseek-chat` and `deepseek-reasoner` both returned:
     "model is not supported when using Codex with a ChatGPT account."
   - Therefore `codex:deepseek-v4-pro` / `codex:deepseek-v4-flash` baseline is invalid unless provider config is fixed or an API actor is used.

6. Kimi can currently access repository context.
   - In `edge-dc-design-001`, trajectory shows it read reference solution files from the repo.
   - This contaminates baseline if runs occur inside the repo with full repository visibility.

## Code changes already made

Harness fixes:

- `src/sd_hwe_bench/critics/syntax.py`
  - Missing `expected_files` now fails L0.

- `src/sd_hwe_bench/actors/base.py`
  - Added YAML content snapshots and changed-file counting.

- `src/sd_hwe_bench/actors/codex.py`
  - Counts changed YAML files, not just new files.
  - Marks nonzero exit code as actor failure.
  - Detects auth failure and unsupported model text.

- `src/sd_hwe_bench/actors/kimi.py`
  - Counts changed YAML files, not just new files.
  - Marks nonzero exit code as actor failure.
  - Detects auth failure text.

- `src/sd_hwe_bench/commands/run.py`
  - Manifest `success` is now `actor_success and score_success`.
  - Manifest also stores `actor_success` and `score_success`.

Validation/script sync:

- `scripts/verify_aidc_benchmark.py`
  - Updated old `aidc-operation-002` / `aidc-co-design-002` references to new v7 tasks.

Tests added:

- `tests/test_critics.py`
  - Missing expected file fails L0.

- `tests/test_actors.py`
  - YAML modification is counted.
  - Codex nonzero exit is actor failure.
  - Kimi auth failure is actor failure.

- `tests/test_aidc_simulation_60mw.py`
  - `aidc-60mw-001` scaffold must fail.

New matrix prepared:

- `scripts/batch/aidc-v7-kimi-pass1.yaml`
  - Kimi-only rerun.
  - Run dir is outside repo: `/tmp/sd-hwe-bench-runs/aidc-v7-kimi-pass1-20260630`
  - `max_workers: 1`
  - `timeout: 1800`

## Commands already verified

Targeted tests passed:

```bash
uv run pytest tests/test_critics.py tests/test_actors.py tests/test_aidc_simulation_60mw.py -q
```

Result:

```text
22 passed
```

Scaffold scoring after L0 fix:

- `edge-dc-design-001`: FAIL
- `aidc-60mw-001`: FAIL due to missing `strategy.yaml`
- `aidc-60mw-002`: FAIL due to missing expected detailed-design files
- `aidc-60mw-003`: FAIL due to missing EPC files

Kimi availability probe:

```bash
kimi -m kimi-code/kimi-for-coding --output-format text -p 'Respond with OK only.'
```

It returned OK and exit code 0.

Codex DeepSeek probes failed:

```bash
codex exec -m deepseek-chat ...
codex exec -m deepseek-reasoner ...
```

Both are unsupported with the current ChatGPT-account Codex CLI configuration.

## Next recommended steps

1. Run the full test suite before rerun:

```bash
uv run pytest -q
```

1. Rerun Kimi-only AIDC baseline:

```bash
uv run sd-hwe-bench batch --matrix scripts/batch/aidc-v7-kimi-pass1.yaml
```

1. Inspect rerun manifests:

```bash
python - <<'PY'
import json, pathlib
root = pathlib.Path('/tmp/sd-hwe-bench-runs/aidc-v7-kimi-pass1-20260630')
for p in sorted(root.glob('*/manifest.json')):
    m = json.loads(p.read_text())
    print(p.parent.name, m.get('task_id'), m.get('success'), m.get('actor_success'),
          m.get('score_success'), m.get('overall_score'), m.get('files_written'),
          m.get('actor_elapsed_s'), m.get('error'))
PY
```

1. For DeepSeek baselines, do not use current Codex specs until fixed.
   Options:
   - Add/use a real OpenAI-compatible API actor with DeepSeek base URL and API key.
   - Or fix Codex CLI provider/model config so DeepSeek is not routed through ChatGPT-account OpenAI provider.

2. Longer-term isolation fix:
   - CLI actor workspaces should not expose repo `tasks/*/solution`.
   - Prefer an external temp dataset copy with solutions omitted, or a containerized actor workspace.

## Files changed in this session

Modified:

- `scripts/verify_aidc_benchmark.py`
- `src/sd_hwe_bench/actors/base.py`
- `src/sd_hwe_bench/actors/codex.py`
- `src/sd_hwe_bench/actors/kimi.py`
- `src/sd_hwe_bench/commands/run.py`
- `src/sd_hwe_bench/critics/syntax.py`
- `tests/test_actors.py`
- `tests/test_aidc_simulation_60mw.py`
- `tests/test_critics.py`

Added:

- `scripts/batch/aidc-v7-pass1.yaml`
- `scripts/batch/aidc-v7-kimi-pass1.yaml`
- `TEMP_MEMO_AIDC_V7_RERUN_20260630.md`
