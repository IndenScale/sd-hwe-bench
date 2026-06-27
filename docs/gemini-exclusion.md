# Gemini CLI Exclusion Note

**Date**: 2026-06-27
**Status**: Excluded from official leaderboard

## Reason

All 46 gemini CLI runs produced `files_written=0` due to OAuth authentication
failure: `Resource has been exhausted (e.g. check quota)`.

The gemini CLI agent never successfully invoked the model API, so the 13.0%
pass@1 result is not a valid measure of model capability.

## Action

Gemini is removed from the test plan until the quota/auth issue is resolved.
The actor implementation (`src/sd_hwe_bench/actors/gemini.py`) is preserved
for future use.

## Evidence

All 47 trajectory files in `runs/*gemini*_a000/trajectory.jsonl` contain:
- `"files_written": 0`
- `"success": true` (false positive: actor "succeeded" at doing nothing)
- OAuth error in `raw_output_preview`
