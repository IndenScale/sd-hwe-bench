"""Tests for the batch command's matrix parsing, task expansion, and dry-run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sd_hwe_bench.cli import app
from sd_hwe_bench.commands.batch import (
    _complete_manifest,
    _interleave_plan_by_provider,
    _load_provider_max_workers,
    _provider_for_actor_spec,
    expand_tasks,
    load_conditions,
    load_matrix,
)
from sd_hwe_bench.commands.batch_status import summarize_batch_status
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.settings import settings

REPO_ROOT = Path(__file__).parent.parent
runner = CliRunner()


def _write_matrix(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "matrix.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_load_matrix_requires_models_and_tasks(tmp_path):
    with pytest.raises(ValueError, match="models"):
        load_matrix(_write_matrix(tmp_path, "tasks: [a]\n"))
    with pytest.raises(ValueError, match="tasks"):
        load_matrix(_write_matrix(tmp_path, "models: {kimi: kimi}\n"))


def test_load_conditions_defaults_and_validates():
    defaults = load_conditions({"models": {"a": "kimi"}, "tasks": ["telecom/*"]})
    assert defaults == [
        {
            "name": "default",
            "command": "run",
            "context_mode": "full",
            "diagnostic_verbosity": "localized",
            "constraint_coverage_mode": "full",
            "prompt_mute": "",
            "feedback_mute": "",
            "mute_ratio": 0.0,
            "mute_seed": None,
            "no_repair": False,
            "max_repair": settings.DEFAULT_MAX_REPAIR,
        }
    ]

    conditions = load_conditions(
        {
            "command": "run-repair",
            "max_repair": 5,
            "conditions": [
                {"name": "nl-only", "context_mode": "nl-only", "no_repair": True},
                {"name": "executable", "context_mode": "full"},
            ],
        }
    )
    assert [c["name"] for c in conditions] == ["nl-only", "executable"]
    assert conditions[0]["command"] == "run-repair"
    assert conditions[0]["no_repair"] is True
    assert conditions[1]["max_repair"] == 5


def test_load_conditions_constraint_gap_fields():
    conditions = load_conditions(
        {
            "command": "run-repair",
            "conditions": [
                {
                    "name": "partial",
                    "constraint_coverage_mode": "explicit-mute",
                    "feedback_mute": ["layer:L3", "family:layout"],
                    "diagnostic_verbosity": "coarse",
                    "mute_ratio": 0.25,
                    "mute_seed": 42,
                }
            ],
        }
    )
    condition = conditions[0]
    assert condition["constraint_coverage_mode"] == "explicit-mute"
    assert condition["feedback_mute"] == ["layer:L3", "family:layout"]
    assert condition["diagnostic_verbosity"] == "coarse"
    assert condition["mute_ratio"] == 0.25
    assert condition["mute_seed"] == 42


def test_provider_helpers_for_cross_provider_scheduling():
    assert _provider_for_actor_spec("claude:deepseek-v4-flash") == "deepseek"
    assert _provider_for_actor_spec("kimi") == "kimi"
    assert _provider_for_actor_spec("codex:gpt-5.5") == "codex"
    assert _load_provider_max_workers({"deepseek": 1, "kimi": "2"}) == {
        "deepseek": 1,
        "kimi": 2,
    }


def test_interleave_plan_by_provider_round_robins_models():
    condition = {"name": "default"}
    plan = [
        (condition, "deepseek", "claude:deepseek-v4-flash", "task-a", 1, 0),
        (condition, "deepseek", "claude:deepseek-v4-flash", "task-b", 1, 0),
        (condition, "kimi", "kimi", "task-a", 1, 0),
        (condition, "kimi", "kimi", "task-b", 1, 0),
        (condition, "codex", "codex:gpt-5.5", "task-a", 1, 0),
        (condition, "codex", "codex:gpt-5.5", "task-b", 1, 0),
    ]

    interleaved = _interleave_plan_by_provider(plan)

    assert [item[1] for item in interleaved] == [
        "deepseek",
        "kimi",
        "codex",
        "deepseek",
        "kimi",
        "codex",
    ]


def test_expand_tasks_glob_and_prefix():
    ds = Dataset(REPO_ROOT)
    ids = expand_tasks(ds, ["telecom/aidc-*"])
    assert ids, "glob should match aidc tasks"
    assert all(tid.startswith("telecom/aidc-") for tid in ids)
    assert "telecom/aidc-60mw-003" in ids
    # Exact id passes through; dedup keeps a single entry.
    ids2 = expand_tasks(ds, ["telecom/aidc-60mw-003", "telecom/aidc-60mw-003"])
    assert ids2 == ["telecom/aidc-60mw-003"]
    # Bare task directory prefixes resolve across domains for CLI ergonomics.
    ids3 = expand_tasks(ds, ["aidc-60mw-003"])
    assert ids3 == ["telecom/aidc-60mw-003"]


def test_dry_run_plan_count(tmp_path):
    matrix = _write_matrix(
        tmp_path,
        "models:\n  a: kimi\n  b: codex:x\n" "tasks:\n  - telecom/aidc-*\n",
    )
    ds = Dataset(REPO_ROOT)
    n_tasks = len(expand_tasks(ds, ["telecom/aidc-*"]))

    result = runner.invoke(
        app,
        ["batch", "--matrix", str(matrix), "--dataset", str(REPO_ROOT), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert f"= {2 * n_tasks} task-model entries" in result.output
    assert f"attempts={2 * n_tasks}" in result.output
    # Plan lists each (model, task) line; no actor is invoked.
    assert result.output.count("telecom/aidc-") >= 2 * n_tasks


def test_dry_run_reports_provider_caps(tmp_path):
    matrix = _write_matrix(
        tmp_path,
        """
max_workers: 3
provider_max_workers:
  deepseek: 1
  kimi: 1
  codex: 1
models:
  deepseek: claude:deepseek-v4-flash
  kimi: kimi
  codex: codex:gpt-5.5
tasks:
  - telecom/aidc-60mw-003
""",
    )

    result = runner.invoke(
        app,
        ["batch", "--matrix", str(matrix), "--dataset", str(REPO_ROOT), "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "provider_max_workers=codex:1, deepseek:1, kimi:1" in result.output
    assert "3 conditions" not in result.output
    assert "1 conditions × 3 models × 1 tasks" in result.output


def test_dry_run_expands_conditions(tmp_path):
    matrix = _write_matrix(
        tmp_path,
        """
passes: 3
models:
  a: kimi
tasks:
  - telecom/aidc-60mw-003
conditions:
  - name: nl-only
    command: run-repair
    context_mode: nl-only
    no_repair: true
    max_repair: 0
  - name: docs-only
    command: run-repair
    context_mode: docs-only
    no_repair: true
    max_repair: 0
  - name: executable
    command: run-repair
    context_mode: full
    max_repair: 5
""",
    )

    result = runner.invoke(
        app,
        ["batch", "--matrix", str(matrix), "--dataset", str(REPO_ROOT), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert "3 conditions × 1 models × 1 tasks" in result.output
    assert "attempts=9" in result.output
    assert "nl-only:run-repair" in result.output
    assert "docs-only:run-repair" in result.output
    assert "executable:run-repair" in result.output


def test_dry_run_resume_counts_remaining_attempts(tmp_path):
    run_dir = tmp_path / "runs"
    existing = run_dir / "nl-only" / "complete-a"
    existing.mkdir(parents=True)
    (existing / "workspace").mkdir()
    (existing / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "telecom/aidc-60mw-003",
                "model": "claude:test",
                "success": False,
                "turn_scores": [{"success": False}],
            }
        ),
        encoding="utf-8",
    )
    incomplete = run_dir / "nl-only" / "incomplete-a"
    incomplete.mkdir(parents=True)
    (incomplete / "workspace").mkdir()
    (incomplete / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "telecom/aidc-60mw-003",
                "model": "claude:test",
                "work_dir": "/tmp/in-flight",
            }
        ),
        encoding="utf-8",
    )
    matrix = _write_matrix(
        tmp_path,
        f"""
run_dir: {run_dir}
passes: 3
models:
  a: claude:test
tasks:
  - telecom/aidc-60mw-003
conditions:
  - name: nl-only
    command: run-repair
    context_mode: nl-only
    no_repair: true
    max_repair: 0
""",
    )

    result = runner.invoke(
        app,
        ["batch", "--matrix", str(matrix), "--dataset", str(REPO_ROOT), "--dry-run", "--resume"],
    )

    assert result.exit_code == 0, result.output
    assert "attempts=2" in result.output
    assert "remaining=2" in result.output
    assert "complete=1/3" in result.output


def test_resume_complete_manifest_excludes_actor_errors():
    assert not _complete_manifest(
        {
            "success": False,
            "termination_reason": "actor_error",
            "overall_score": 0.0,
            "layers": {},
            "turn_scores": [],
        }
    )
    assert not _complete_manifest(
        {
            "success": False,
            "overall_score": 0.0,
            "layers": {},
            "turn_scores": [],
        }
    )
    assert _complete_manifest(
        {
            "success": False,
            "turn_scores": [{"success": False}],
        }
    )


def test_batch_status_summarizes_complete_inflight_and_actor_error(tmp_path, monkeypatch):
    run_dir = tmp_path / "runs"
    condition_dir = run_dir / "executable"

    complete = condition_dir / "complete-a"
    complete.mkdir(parents=True)
    (complete / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "telecom/aidc-60mw-003",
                "model": "claude:test",
                "success": False,
                "turn_scores": [{"success": False}],
            }
        ),
        encoding="utf-8",
    )

    in_flight = condition_dir / "in-flight-a"
    in_flight.mkdir(parents=True)
    (in_flight / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "telecom/aidc-60mw-003",
                "model": "claude:test",
                "work_dir": "/tmp/live",
            }
        ),
        encoding="utf-8",
    )
    (in_flight / "actor_output.log").write_text("\nworking\n", encoding="utf-8")

    actor_error = condition_dir / "actor-error-a"
    actor_error.mkdir(parents=True)
    (actor_error / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "telecom/aidc-60mw-003",
                "model": "claude:test",
                "success": False,
                "termination_reason": "actor_error",
                "turn_scores": [],
            }
        ),
        encoding="utf-8",
    )

    matrix = _write_matrix(
        tmp_path,
        f"""
run_dir: {run_dir}
passes: 3
models:
  a: claude:test
tasks:
  - telecom/aidc-60mw-003
conditions:
  - name: executable
    command: run-repair
""",
    )
    monkeypatch.setattr(
        "sd_hwe_bench.commands.batch_status._live_process_commands",
        lambda: [str(condition_dir)],
    )

    summary = summarize_batch_status(matrix, REPO_ROOT)

    assert summary["totals"]["attempts"] == 3
    assert summary["totals"]["complete"] == 1
    assert summary["totals"]["in_flight"] == 1
    assert summary["totals"]["actor_error"] == 1
    assert summary["totals"]["remaining"] == 2
    assert summary["entries"][0]["status"] == "running"
    assert summary["entries"][0]["latest_log"] == "working"


def test_batch_status_marks_unowned_stub_as_stale(tmp_path, monkeypatch):
    run_dir = tmp_path / "runs"
    condition_dir = run_dir / "executable"
    stale = condition_dir / "stale-a"
    stale.mkdir(parents=True)
    (stale / "manifest.json").write_text(
        json.dumps(
            {
                "task_id": "telecom/aidc-60mw-003",
                "model": "claude:test",
                "work_dir": "/tmp/no-longer-live",
            }
        ),
        encoding="utf-8",
    )
    matrix = _write_matrix(
        tmp_path,
        f"""
run_dir: {run_dir}
passes: 1
models:
  a: claude:test
tasks:
  - telecom/aidc-60mw-003
conditions:
  - name: executable
    command: run-repair
""",
    )
    monkeypatch.setattr("sd_hwe_bench.commands.batch_status._live_process_commands", lambda: [])

    summary = summarize_batch_status(matrix, REPO_ROOT)

    assert summary["totals"]["in_flight"] == 0
    assert summary["totals"]["stale"] == 1
    assert summary["entries"][0]["status"] == "stale"


def test_batch_status_command_json(tmp_path):
    run_dir = tmp_path / "runs"
    matrix = _write_matrix(
        tmp_path,
        f"""
run_dir: {run_dir}
passes: 2
models:
  a: claude:test
tasks:
  - telecom/aidc-60mw-003
""",
    )

    result = runner.invoke(
        app,
        [
            "batch-status",
            "--matrix",
            str(matrix),
            "--dataset",
            str(REPO_ROOT),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"attempts": 2' in result.output
    assert '"remaining": 2' in result.output


def test_batch_status_command_text_default(tmp_path):
    run_dir = tmp_path / "runs"
    matrix = _write_matrix(
        tmp_path,
        f"""
run_dir: {run_dir}
passes: 2
models:
  a: claude:test
tasks:
  - telecom/aidc-60mw-003
""",
    )

    result = runner.invoke(
        app,
        ["batch-status", "--matrix", str(matrix), "--dataset", str(REPO_ROOT)],
    )

    assert result.exit_code == 0, result.output
    assert "Batch status: complete=0/2" in result.output
    assert "telecom/aidc-60mw-003 claude:test: pending" in result.output
