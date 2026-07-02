#!/usr/bin/env python3
"""Aggregate representation-gap manifests into analysis tables."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPER_DATA = REPO_ROOT / "papers/physical-engineering-as-code-eval-substrate/src/data/eval-substrate.yaml"


def _pct(value: float) -> str:
    return f"{value:.0%}"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def load_manifests(run_dir: Path) -> list[dict[str, Any]]:
    manifests = []
    for path in sorted(run_dir.rglob("manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if manifest.get("experiment") == "representation-gap":
            manifest["_manifest_path"] = str(path)
            manifests.append(manifest)
    return manifests


def _status_counts(manifests: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for manifest in manifests:
        counts[manifest.get("status", "unknown")] += 1
    return dict(sorted(counts.items()))


def aggregate_summary_rows(run_dir: Path) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for manifest in load_manifests(run_dir):
        grouped[manifest["condition"]].append(manifest)

    rows = []
    for condition, manifests in sorted(grouped.items()):
        completed = [m for m in manifests if m.get("status") != "skipped"]
        passed = [m for m in completed if m.get("success")]
        latencies = [
            float(m.get("metrics", {}).get("feedback_latency_ms"))
            for m in completed
            if m.get("metrics", {}).get("feedback_latency_ms") is not None
        ]
        scores = [float(m["score"]) for m in completed if m.get("score") is not None]
        rows.append(
            {
                "condition": condition,
                "representation_path": manifests[0].get("representation_path", "unknown"),
                "actor": manifests[0].get("actor", "unknown"),
                "attempts": str(len(manifests)),
                "status_counts": json.dumps(_status_counts(manifests), sort_keys=True),
                "artifact_success_rate": _pct(len(passed) / len(completed)) if completed else "--",
                "mean_score": f"{_mean(scores):.2f}" if scores else "--",
                "median_feedback_latency_ms": (
                    f"{statistics.median(latencies):.1f}" if latencies else "--"
                ),
            }
        )
    return rows


def aggregate_capability_rows(run_dir: Path) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for manifest in load_manifests(run_dir):
        if manifest.get("status") == "skipped":
            continue
        grouped[manifest["condition"]].append(manifest)

    capabilities = [
        "deterministic_artifact",
        "semantic_source",
        "tool_call_log",
        "localized_feedback",
        "archive_rescore",
        "visual_gui_process",
        "ui_element_interaction",
        "actor_triggered",
    ]
    rows = []
    for condition, manifests in sorted(grouped.items()):
        row = {
            "condition": condition,
            "representation_path": manifests[0].get("representation_path", "unknown"),
        }
        for capability in capabilities:
            enabled = sum(1 for m in manifests if m.get("metrics", {}).get(capability) is True)
            row[capability] = _pct(enabled / len(manifests))
        invalid = sum(1 for m in manifests if m.get("metrics", {}).get("invalid_submission") is True)
        row["invalid_submission_rate"] = _pct(invalid / len(manifests))
        rows.append(row)
    return rows


def build_payload(run_dir: Path) -> dict[str, Any]:
    manifests = load_manifests(run_dir)
    return {
        "artifact": {
            "result_status": "representation_smoke_real_artifacts",
            "result_label": "Representation-gap smoke artifacts",
            "result_note": (
                "表征实验当前为基础设施 smoke：验证各表征路径能产出可归档、可检查工件；"
                "尚不是正式统计显著性实验。"
            ),
            "assumptions": {
                "run_dir": str(run_dir),
                "attempts": len(manifests),
                "conditions": len({m["condition"] for m in manifests}),
                "paths": sorted({m.get("representation_path", "unknown") for m in manifests}),
            },
        },
        "experiments": {
            "representation": {
                "summary_rows": aggregate_summary_rows(run_dir),
                "capability_rows": aggregate_capability_rows(run_dir),
            }
        },
    }


def update_paper_data(payload: dict[str, Any], data_path: Path = PAPER_DATA) -> None:
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    data.setdefault("experiments", {})
    data["experiments"]["representation"] = payload["experiments"]["representation"]
    data.setdefault("artifact", {})
    data["artifact"].setdefault("representation_artifact", {})
    data["artifact"]["representation_artifact"] = payload["artifact"]
    data_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--update-paper-data", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args.run_dir)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    if args.update_paper_data:
        update_paper_data(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
