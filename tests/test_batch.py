"""Tests for the batch command's matrix parsing, task expansion, and dry-run."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sd_hwe_bench.cli import app
from sd_hwe_bench.commands.batch import expand_tasks, load_conditions, load_matrix
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


def test_expand_tasks_glob_and_prefix():
    ds = Dataset(REPO_ROOT)
    ids = expand_tasks(ds, ["telecom/aidc-*"])
    assert ids, "glob should match aidc tasks"
    assert all(tid.startswith("telecom/aidc-") for tid in ids)
    assert "telecom/aidc-60mw-003" in ids
    # Exact id passes through; dedup keeps a single entry.
    ids2 = expand_tasks(ds, ["telecom/aidc-60mw-003", "telecom/aidc-60mw-003"])
    assert ids2 == ["telecom/aidc-60mw-003"]


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
