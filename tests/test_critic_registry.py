"""Tests for the declarative critic registry (analysis-critic resolution)."""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from sd_hwe_bench.critics.registry import (
    AnalysisSpec,
    CriticContext,
    build_critic,
    resolve_analysis_critics,
)
from sd_hwe_bench.task import EvaluationSpec, TaskInstance, TaskMetadata

TASKS = Path(__file__).parent.parent / "tasks" / "telecom"


def _specs(task_id: str) -> list[AnalysisSpec]:
    task = TaskInstance(TASKS / task_id)
    return resolve_analysis_critics(task)


def test_epc_task_resolves_to_epc_critic():
    specs = _specs("aidc-60mw-003")
    assert len(specs) == 1
    assert specs[0].critic == "epc"
    assert specs[0].layer == "L4"
    assert specs[0].mode == "replace"
    assert specs[0].provides_performance is True


def test_detailed_design_resolves_perf_plus_constructability():
    specs = _specs("aidc-60mw-002")
    by_critic = {s.critic: s for s in specs}
    assert set(by_critic) == {"aidc-performance", "constructability"}
    # L4 performance must precede L5 constructability.
    assert [s.critic for s in specs] == ["aidc-performance", "constructability"]
    assert by_critic["aidc-performance"].layer == "L4"
    assert by_critic["aidc-performance"].provides_performance is True
    assert by_critic["constructability"].layer == "L5"
    assert by_critic["constructability"].mode == "merge"
    assert by_critic["constructability"].provides_performance is False


def test_co_design_resolves_to_performance_only():
    specs = _specs("aidc-60mw-001")
    assert [s.critic for s in specs] == ["aidc-performance"]
    assert specs[0].layer == "L4"


def test_conceptual_design_resolves_to_decision_critic():
    # Shipped task declares an explicit `evaluation:` block binding the decision critic.
    specs = _specs("aidc-scheme-selection-001")
    assert [s.critic for s in specs] == ["decision"]
    assert specs[0].layer == "L4"
    assert specs[0].provides_performance is True


def test_conceptual_design_default_derivation_without_explicit_evaluation():
    # task_type=conceptual-design with L4 in scoring_layers derives the decision
    # critic even when no explicit `evaluation:` block is present.
    meta = TaskMetadata(
        task_id="x",
        domain="telecom",
        task_type="conceptual-design",
        difficulty="medium",
        requirement="",
        scoring_layers=["L0", "L1", "L2", "L3", "L4"],
    )
    task = types.SimpleNamespace(metadata=meta)
    specs = resolve_analysis_critics(task)
    assert [s.critic for s in specs] == ["decision"]
    assert specs[0].provides_performance is True


def test_staged_task_without_l4_resolves_to_no_analysis_critics():
    # comprehensive staged task: scoring_layers has no L4 and no construction/.
    specs = _specs("rack-stage1-init-deploy-connect-verify")
    assert specs == []


def test_explicit_evaluation_overrides_task_type():
    # task_type=comprehensive without L4 would derive []; explicit evaluation wins.
    meta = TaskMetadata(
        task_id="x",
        domain="telecom",
        task_type="comprehensive",
        difficulty="easy",
        requirement="",
        scoring_layers=["L0", "L1"],
        evaluation=[EvaluationSpec(critic="epc", layer="L4", provides_performance=True)],
    )
    task = types.SimpleNamespace(metadata=meta)
    specs = resolve_analysis_critics(task)
    assert len(specs) == 1
    assert specs[0].critic == "epc"
    assert specs[0].provides_performance is True


def test_build_critic_unknown_name_raises():
    ctx = CriticContext(project_dir=Path("."), l7_config={}, repo_root=Path("."))
    with pytest.raises(ValueError, match="Unknown analysis critic"):
        build_critic(AnalysisSpec(critic="does-not-exist"), ctx)


def test_build_critic_known_names():
    ctx = CriticContext(project_dir=Path("."), l7_config={"deadline_days": 99}, repo_root=Path("."))
    epc = build_critic(AnalysisSpec(critic="epc"), ctx)
    assert epc.deadline_days == 99
    constr = build_critic(AnalysisSpec(critic="constructability", layer="L5", mode="merge"), ctx)
    assert constr.name == "Constructability"
    decision = build_critic(AnalysisSpec(critic="decision"), ctx)
    assert decision.name == "Decision"
