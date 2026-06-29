"""Tests for the batch command's matrix parsing, task expansion, and dry-run."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sd_hwe_bench.cli import app
from sd_hwe_bench.commands.batch import expand_tasks, load_matrix
from sd_hwe_bench.dataset import Dataset

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
    assert f"= {2 * n_tasks} rollouts" in result.output
    # Plan lists each (model, task) line; no actor is invoked.
    assert result.output.count("telecom/aidc-") >= 2 * n_tasks
