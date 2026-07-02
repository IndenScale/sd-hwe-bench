from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
AGGREGATE_PATH = REPO_ROOT / "scripts/aggregate_representation_gap.py"


def _load_aggregate_module():
    spec = importlib.util.spec_from_file_location("aggregate_representation_gap", AGGREGATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_manifest(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_representation_aggregate_groups_summary_and_capabilities(tmp_path: Path):
    mod = _load_aggregate_module()
    run_dir = tmp_path / "representation"
    _write_manifest(
        run_dir / "mcp" / "attempt-000" / "manifest.json",
        {
            "experiment": "representation-gap",
            "condition": "mcp",
            "representation_path": "mcp",
            "actor": "no-model",
            "status": "passed",
            "success": True,
            "score": 1.0,
            "metrics": {
                "semantic_source": True,
                "tool_call_log": True,
                "localized_feedback": True,
                "archive_rescore": True,
                "invalid_submission": False,
                "feedback_latency_ms": 12.5,
            },
        },
    )
    _write_manifest(
        run_dir / "cua-deepseek" / "attempt-000" / "manifest.json",
        {
            "experiment": "representation-gap",
            "condition": "cua-deepseek",
            "representation_path": "cua-actor",
            "actor": "claude:deepseek-v4-flash",
            "status": "skipped",
            "success": False,
            "metrics": {},
        },
    )

    payload = mod.build_payload(run_dir)

    rows = payload["experiments"]["representation"]["summary_rows"]
    assert rows[0]["condition"] == "cua-deepseek"
    assert rows[0]["artifact_success_rate"] == "--"
    assert rows[1]["condition"] == "mcp"
    assert rows[1]["artifact_success_rate"] == "100%"
    assert rows[1]["median_feedback_latency_ms"] == "12.5"

    capability_rows = payload["experiments"]["representation"]["capability_rows"]
    assert capability_rows == [
        {
            "condition": "mcp",
            "representation_path": "mcp",
            "deterministic_artifact": "0%",
            "semantic_source": "100%",
            "tool_call_log": "100%",
            "localized_feedback": "100%",
            "archive_rescore": "100%",
            "visual_gui_process": "0%",
            "ui_element_interaction": "0%",
            "actor_triggered": "0%",
            "invalid_submission_rate": "0%",
        }
    ]
