"""Tests for PEaC evaluation-substrate result aggregation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts/aggregate_peac_eval_substrate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("aggregate_peac_eval_substrate", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True)
    (path.parent / "workspace").mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_aggregate_constraint_rows_from_condition_dirs(tmp_path):
    mod = _load_module()
    run_root = tmp_path / "runs"
    base_manifest = {
        "task_id": "telecom/test",
        "model": "claude:test",
        "turn_scores": [
            {
                "success": False,
                "layers": {"L3": {"passed": 0, "total": 1, "failed": 1}},
            },
            {
                "success": True,
                "layers": {"L3": {"passed": 1, "total": 1, "failed": 0}},
                "diagnostics": {"omission_density": 0.25},
            },
        ],
        "success": True,
        "repair_rounds_used": 1,
    }
    _write_manifest(run_root / "executable" / "run-a" / "manifest.json", base_manifest)
    _write_manifest(
        run_root / "executable" / "run-b" / "manifest.json",
        {
            **base_manifest,
            "success": False,
            "repair_rounds_used": 2,
            "turn_scores": [
                base_manifest["turn_scores"][0],
                {
                    "success": False,
                    "layers": {"L5": {"passed": 0, "total": 1, "failed": 1}},
                    "diagnostics": {"omission_density": 0.5},
                },
            ],
        },
    )

    rows = mod.aggregate_constraint_rows(run_root)

    assert rows == [
        {
            "condition": "executable",
            "pass_at_1": "0%",
            "pass_after_repair": "50%",
            "pseudo_correctness": "manual-label-required",
            "omission_density": "0.25",
            "median_repair_rounds": "1",
            "top_failed_layer": "L5",
        }
    ]


def test_build_payload_records_artifact_assumptions(tmp_path):
    mod = _load_module()
    run_root = tmp_path / "runs"
    _write_manifest(
        run_root / "docs-only" / "run-a" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": False,
            "turn_scores": [],
            "layers": {"L2": {"passed": 0, "total": 1}},
        },
    )

    payload = mod.build_payload(run_root)

    assert payload["artifact"]["result_status"] == "partial_real_constraint_p0"
    assert payload["artifact"]["assumptions"]["conditions"] == 1
    assert payload["artifact"]["assumptions"]["attempts"] == 1
    assert payload["experiments"]["constraint"]["summary_rows"][0]["condition"] == "docs-only"


def test_aggregate_skips_incomplete_manifests(tmp_path):
    mod = _load_module()
    run_root = tmp_path / "runs"
    _write_manifest(
        run_root / "nl-only" / "complete" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": True,
            "turn_scores": [{"success": True, "layers": {}}],
        },
    )
    _write_manifest(
        run_root / "nl-only" / "incomplete" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "work_dir": "/tmp/in-flight",
        },
    )

    payload = mod.build_payload(run_root)

    assert payload["artifact"]["assumptions"]["attempts"] == 1
    assert payload["experiments"]["constraint"]["summary_rows"][0]["pass_at_1"] == "100%"


def test_aggregate_skips_actor_error_manifests(tmp_path):
    mod = _load_module()
    run_root = tmp_path / "runs"
    _write_manifest(
        run_root / "executable" / "actor-error" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": False,
            "termination_reason": "actor_error",
            "overall_score": 0.0,
            "layers": {},
            "turn_scores": [],
        },
    )
    _write_manifest(
        run_root / "executable" / "complete" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": False,
            "turn_scores": [{"success": False, "layers": {}}],
        },
    )

    payload = mod.build_payload(run_root)

    assert payload["artifact"]["assumptions"]["attempts"] == 1


def test_successful_final_turn_has_zero_omission_density(tmp_path):
    mod = _load_module()
    run_root = tmp_path / "runs"
    _write_manifest(
        run_root / "executable" / "run-a" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": True,
            "turn_scores": [
                {
                    "success": True,
                    "layers": {"L3": {"passed": 1, "total": 1, "failed": 0}},
                    "diagnostics": {"omission_density": 0.5},
                }
            ],
        },
    )

    rows = mod.aggregate_constraint_rows(run_root)

    assert rows[0]["pass_after_repair"] == "100%"
    assert rows[0]["omission_density"] == "0.00"


def test_submission_budget_rows_sample_single_long_run(tmp_path):
    mod = _load_module()
    run_root = tmp_path / "runs"
    _write_manifest(
        run_root / "executable" / "run-a" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": True,
            "max_submissions": 100,
            "submissions_used": 5,
            "turn_scores": [
                {
                    "submission": 1,
                    "success": False,
                    "layers": {"L3": {"passed": 0, "total": 1, "failed": 1}},
                    "diagnostics": {"omission_density": 0.5},
                },
                {
                    "submission": 5,
                    "success": True,
                    "layers": {"L3": {"passed": 1, "total": 1, "failed": 0}},
                    "diagnostics": {"omission_density": 0.0},
                },
            ],
        },
    )
    _write_manifest(
        run_root / "executable" / "run-b" / "manifest.json",
        {
            "task_id": "telecom/test",
            "model": "claude:test",
            "success": False,
            "max_submissions": 100,
            "submissions_used": 100,
            "turn_scores": [
                {
                    "submission": 1,
                    "success": False,
                    "layers": {"L3": {"passed": 0, "total": 1, "failed": 1}},
                    "diagnostics": {"omission_density": 0.75},
                },
                {
                    "submission": 20,
                    "success": False,
                    "layers": {"L3": {"passed": 0, "total": 1, "failed": 1}},
                    "diagnostics": {"omission_density": 0.25},
                },
                {
                    "submission": 100,
                    "success": False,
                    "layers": {"L3": {"passed": 0, "total": 1, "failed": 1}},
                    "diagnostics": {"omission_density": 0.25},
                },
            ],
        },
    )

    rows = mod.aggregate_submission_budget_rows(run_root, budgets=[1, 5, 20, 100])

    assert rows == [
        {
            "condition": "executable",
            "submission_budget": "1",
            "pass_rate": "0%",
            "omission_density": "0.62",
            "budget_exhausted": "0",
            "attempts": "2",
        },
        {
            "condition": "executable",
            "submission_budget": "5",
            "pass_rate": "50%",
            "omission_density": "0.38",
            "budget_exhausted": "0",
            "attempts": "2",
        },
        {
            "condition": "executable",
            "submission_budget": "20",
            "pass_rate": "50%",
            "omission_density": "0.12",
            "budget_exhausted": "0",
            "attempts": "2",
        },
        {
            "condition": "executable",
            "submission_budget": "100",
            "pass_rate": "50%",
            "omission_density": "0.12",
            "budget_exhausted": "1",
            "attempts": "2",
        },
    ]
