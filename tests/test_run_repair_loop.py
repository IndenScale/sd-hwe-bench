"""Tests for run-repair submission-loop semantics."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from sd_hwe_bench.cli import app
from sd_hwe_bench.commands.run_repair import _submission_decision
from sd_hwe_bench.prompts import PromptBuilder

runner = CliRunner()


def test_done_marker_does_not_stop_failed_repair_when_budget_remains():
    should_stop, reason = _submission_decision(
        score_success=False,
        marker="done",
        no_repair=False,
        turn=0,
        max_repair=2,
    )

    assert should_stop is False
    assert reason is None


def test_failed_submission_stops_when_budget_is_exhausted():
    should_stop, reason = _submission_decision(
        score_success=False,
        marker="done",
        no_repair=False,
        turn=2,
        max_repair=2,
    )

    assert should_stop is True
    assert reason == "budget_exceeded"


def test_baseline_stops_after_one_scored_submission():
    should_stop, reason = _submission_decision(
        score_success=False,
        marker="done",
        no_repair=True,
        turn=0,
        max_repair=5,
    )

    assert should_stop is True
    assert reason == "baseline"


def test_non_done_markers_still_stop_the_loop():
    should_stop, reason = _submission_decision(
        score_success=False,
        marker="info_gap",
        no_repair=False,
        turn=0,
        max_repair=5,
    )

    assert should_stop is True
    assert reason == "info_gap"


def test_baseline_prompt_hides_executable_constraint_catalog():
    prompt = PromptBuilder().build(
        task_metadata={
            "task_id": "telecom/test",
            "name": "test task",
            "task_type": "comprehensive",
            "difficulty": "medium",
            "plugins": ["telecom"],
            "requirement": "完成自然语言需求。",
            "expected_files": [],
            "expected_deliverables": [],
        },
        scaffold_dir=Path("/tmp/nonexistent-scaffold"),
        repair_mode=False,
        baseline_mode=True,
        context_mode="nl-only",
        visible_constraints=None,
    )

    assert "可见约束目录" not in prompt
    assert "Inferred scoring-layer constraint" not in prompt
    assert "提交后统一验证" in prompt


def test_repair_prompt_can_show_executable_constraint_catalog():
    prompt = PromptBuilder().build(
        task_metadata={
            "task_id": "telecom/test",
            "name": "test task",
            "task_type": "comprehensive",
            "difficulty": "medium",
            "plugins": ["telecom"],
            "requirement": "完成工程需求。",
            "expected_files": [],
            "expected_deliverables": [],
        },
        scaffold_dir=Path("/tmp/nonexistent-scaffold"),
        repair_mode=True,
        baseline_mode=False,
        context_mode="full",
        visible_constraints=[
            {
                "id": "telecom/test:L3",
                "layer": "L3",
                "family": "static",
                "description": "Executable constraint",
            }
        ],
    )

    assert "可见约束目录" in prompt
    assert "telecom/test:L3" in prompt


def test_run_repair_archives_score_error_manifest(tmp_path, monkeypatch):
    class FakeActor:
        def run(self, _prompt, _project_dir):
            return SimpleNamespace(
                success=True,
                raw_output="done",
                files_written=0,
                elapsed_s=0.1,
                error=None,
            )

    monkeypatch.setattr(
        "sd_hwe_bench.commands.run_repair.create_actor",
        lambda _actor, timeout: FakeActor(),
    )

    def boom(**_kwargs):
        raise RuntimeError("synthetic scorer failure")

    monkeypatch.setattr("sd_hwe_bench.commands.run_repair.score_task", boom)

    result = runner.invoke(
        app,
        [
            "run-repair",
            "telecom/comprehensive-001",
            "--actor",
            "fake:model",
            "--passes",
            "1",
            "--run-dir",
            str(tmp_path / "runs"),
            "--sandbox",
            "none",
            "--max-repair",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    manifests = list((tmp_path / "runs").rglob("manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["termination_reason"] == "score_error"
    assert manifest["success"] is False
    assert manifest["turn_scores"][0]["score_error"] == "RuntimeError: synthetic scorer failure"
    assert (manifests[0].parent / "workspace").exists()
