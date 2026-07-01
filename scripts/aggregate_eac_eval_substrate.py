#!/usr/bin/env python3
"""Aggregate EaC evaluation-substrate experiment runs into paper data.

Usage:
  uv run scripts/aggregate_eac_eval_substrate.py --run-dir /tmp/sd-hwe-bench-runs/constraint-gap-p0-20260630
  uv run scripts/aggregate_eac_eval_substrate.py --run-dir /tmp/... --update-paper-data
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPER_DATA = REPO_ROOT / "papers/engineering-as-code-eval-substrate/src/data/eval-substrate.yaml"


def _pct(value: float) -> str:
    return f"{value:.0%}"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _condition_from_path(run_root: Path, manifest_path: Path, manifest: dict[str, Any]) -> str:
    rel = manifest_path.parent.relative_to(run_root)
    if len(rel.parts) >= 2:
        return rel.parts[0]
    return str(manifest.get("condition") or manifest.get("context_mode") or "default")


def _initial_success(manifest: dict[str, Any]) -> bool:
    turn_scores = manifest.get("turn_scores") or []
    if turn_scores:
        return bool(turn_scores[0].get("success", False))
    return bool(manifest.get("success", False))


def _final_turn(manifest: dict[str, Any]) -> dict[str, Any]:
    turn_scores = manifest.get("turn_scores") or []
    return turn_scores[-1] if turn_scores else manifest


def _failed_layers(score_like: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    for name, layer in (score_like.get("layers") or {}).items():
        total = int(layer.get("total", 0) or 0)
        passed = int(layer.get("passed", 0) or 0)
        explicit_failed = int(layer.get("failed", max(0, total - passed)) or 0)
        if explicit_failed > 0 or (total and passed < total):
            failed.append(name)
    deliverables = score_like.get("deliverables") or {}
    if any(not ok for ok in deliverables.values()):
        failed.append("Deliverable")
    return failed


def _omission_density(manifest: dict[str, Any]) -> float:
    final = _final_turn(manifest)
    diagnostics = final.get("diagnostics") or {}
    if "omission_density" in diagnostics:
        return float(diagnostics["omission_density"])

    layers = final.get("layers") or manifest.get("layers") or {}
    failed = 0
    total = 0
    for layer in layers.values():
        layer_total = int(layer.get("total", 0) or 0)
        layer_passed = int(layer.get("passed", 0) or 0)
        total += layer_total
        failed += int(layer.get("failed", max(0, layer_total - layer_passed)) or 0)
    return failed / total if total else 0.0


def load_manifests(run_root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    manifests: list[tuple[str, Path, dict[str, Any]]] = []
    for path in sorted(run_root.rglob("manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        condition = _condition_from_path(run_root, path, manifest)
        manifests.append((condition, path, manifest))
    return manifests


def aggregate_constraint_rows(run_root: Path) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for condition, _path, manifest in load_manifests(run_root):
        grouped[condition].append(manifest)

    rows: list[dict[str, str]] = []
    for condition, manifests in sorted(grouped.items()):
        if not manifests:
            continue
        initial_pass = sum(1 for m in manifests if _initial_success(m))
        final_pass = sum(1 for m in manifests if m.get("success", False))
        repair_rounds = [
            int(m.get("repair_rounds_used", 0) or 0)
            for m in manifests
            if m.get("success", False)
        ]
        layer_counts: Counter[str] = Counter()
        for manifest in manifests:
            layer_counts.update(_failed_layers(_final_turn(manifest)))
        top_layers = "/".join(layer for layer, _count in layer_counts.most_common(2)) or "--"
        rows.append(
            {
                "condition": condition,
                "pass_at_1": _pct(initial_pass / len(manifests)),
                "pass_after_repair": _pct(final_pass / len(manifests)),
                "pseudo_correctness": "manual-label-required",
                "omission_density": f"{_mean([_omission_density(m) for m in manifests]):.2f}",
                "median_repair_rounds": (
                    str(int(statistics.median(repair_rounds))) if repair_rounds else "--"
                ),
                "top_failed_layer": top_layers,
            }
        )
    return rows


def build_payload(run_root: Path) -> dict[str, Any]:
    manifests = load_manifests(run_root)
    tasks = sorted({m.get("task_id", "unknown") for _c, _p, m in manifests})
    models = sorted({m.get("model") or m.get("actor", "unknown") for _c, _p, m in manifests})
    conditions = sorted({c for c, _p, _m in manifests})
    return {
        "artifact": {
            "result_status": "partial_real_constraint_p0",
            "result_label": "P0 constraint-gap run artifacts",
            "result_note": (
                "约束实验表由隔离 run manifest 自动聚合；pseudo-correctness 仍需人工标注。"
                "表征与知识实验若未重跑，仍不得视为正式结果。"
            ),
            "assumptions": {
                "models": len(models),
                "tasks": len(tasks),
                "conditions": len(conditions),
                "attempts": len(manifests),
                "run_dir": str(run_root),
            },
        },
        "experiments": {
            "constraint": {
                "summary_rows": aggregate_constraint_rows(run_root),
            }
        },
    }


def update_paper_data(payload: dict[str, Any], data_path: Path = PAPER_DATA) -> None:
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    data["artifact"] = payload["artifact"]
    data.setdefault("experiments", {})
    data["experiments"].setdefault("constraint", {})
    data["experiments"]["constraint"]["summary_rows"] = payload["experiments"]["constraint"]["summary_rows"]
    data_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--update-paper-data", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args.run_dir)
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.update_paper_data:
        update_paper_data(payload)


if __name__ == "__main__":
    main()
