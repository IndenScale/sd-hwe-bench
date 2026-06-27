#!/usr/bin/env python3
"""Audit rollout archives to extract per-trajectory insights.

Usage:
    python tools/audit_runs.py runs/<experiment-dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_manifest(run_dir: Path) -> dict:
    manifest = run_dir / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text(encoding="utf-8"))
    return {}


def load_trajectory(run_dir: Path) -> list[dict]:
    traj = run_dir / "trajectory.jsonl"
    if not traj.exists():
        return []
    entries = []
    with traj.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def summarize_run(run_dir: Path) -> dict:
    manifest = load_manifest(run_dir)
    trajectory = load_trajectory(run_dir)
    actor_rounds = sum(1 for e in trajectory if e.get("event") == "actor_finished")
    self_check_rounds = sum(1 for e in trajectory if e.get("event") == "self_check_finished")
    diagnostics = []
    for e in trajectory:
        if e.get("event") == "self_check_prompt":
            diagnostics.append(e.get("diagnostics_count", 0))
    return {
        "task_id": manifest.get("task_id", "?"),
        "model": manifest.get("model", "?"),
        "attempt": manifest.get("attempt", -1),
        "success": manifest.get("success", False),
        "overall_score": manifest.get("overall_score", 0.0),
        "layers": manifest.get("layers", {}),
        "deliverables": manifest.get("deliverables", {}),
        "files_written": manifest.get("files_written", 0),
        "actor_elapsed_s": manifest.get("actor_elapsed_s", 0.0),
        "actor_rounds": actor_rounds,
        "self_check_rounds": self_check_rounds,
        "self_check_diagnostics": diagnostics,
    }


def collect_errors(manifest: dict) -> list[str]:
    errors: list[str] = []
    layers = manifest.get("layers", {})
    for layer, info in layers.items():
        if info.get("passed", 0) < info.get("total", 1):
            errors.append(f"{layer}: layer failed")
    deliverables = manifest.get("deliverables", {})
    for name, ok in deliverables.items():
        if not ok:
            errors.append(f"deliverable:{name}: missing")
    return errors


def audit_experiment(exp_dir: Path) -> None:
    if not exp_dir.exists():
        print(f"Experiment directory not found: {exp_dir}", file=sys.stderr)
        sys.exit(1)

    runs = [d for d in exp_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()]
    runs.sort()

    summaries = [summarize_run(r) for r in runs]

    # Overall
    total = len(summaries)
    passed = sum(1 for s in summaries if s["success"])
    by_task: dict[str, list[dict]] = defaultdict(list)
    for s in summaries:
        by_task[s["task_id"]].append(s)

    print(f"Experiment: {exp_dir}")
    print(f"Total rollouts: {total}")
    print(f"Successes: {passed}/{total} ({passed / total:.1%})")
    print()

    # Per-task
    print("Per-task summary:")
    for tid in sorted(by_task):
        attempts = by_task[tid]
        n = len(attempts)
        p = sum(1 for a in attempts if a["success"])
        avg_score = sum(a["overall_score"] for a in attempts) / n
        print(f"  {tid}: {p}/{n} pass, avg_score={avg_score:.2f}")

    # Error patterns
    print("\nFailure patterns:")
    error_counter: Counter = Counter()
    for s in summaries:
        if not s["success"]:
            # Re-read manifest to get richer error info if available
            manifest = load_manifest(runs[summaries.index(s)])
            errs = collect_errors(manifest)
            for e in errs:
                error_counter[e] += 1
    for err, count in error_counter.most_common(20):
        print(f"  {count:3d}  {err}")

    # Self-check engagement
    print("\nSelf-check engagement:")
    sc_with_diagnostics = [len(s["self_check_diagnostics"]) for s in summaries]
    if sc_with_diagnostics:
        print(f"  Avg self-check rounds: {sum(sc_with_diagnostics) / len(sc_with_diagnostics):.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit SD-HWE-Bench rollout archives")
    parser.add_argument("exp_dir", type=Path, help="Path to experiment directory (e.g. runs/...)")
    args = parser.parse_args()
    audit_experiment(args.exp_dir)
