"""Tests for DecisionCritic (ADR 0006 conceptual-design multi-scheme selection)."""

from __future__ import annotations

import types
from pathlib import Path

import yaml

from sd_hwe_bench.critics.decision import (
    DecisionCritic,
    pareto_front,
    rank_of,
    weighted_scores,
)
from sd_hwe_bench.task import TaskInstance, TaskMetadata

TASKS = Path(__file__).parent.parent / "tasks" / "telecom"

# A self-contained synthetic library: A and B are Pareto-optimal, C is
# dominated by A (higher cost AND lower quality), D is infeasible.
SYNTH_LIBRARY = {
    "tolerance": 0.05,
    "criteria_directions": {"cost": "min", "quality": "max"},
    "schemes": {
        "A": {"feasible": True, "criteria": {"cost": 100, "quality": 0.9}},
        "B": {"feasible": True, "criteria": {"cost": 80, "quality": 0.7}},
        "C": {"feasible": True, "criteria": {"cost": 120, "quality": 0.5}},
        "D": {"feasible": False, "criteria": {"cost": 50, "quality": 0.95}},
    },
}
SYNTH_SCENARIO = {"criteria_weights": {"cost": 0.4, "quality": 0.6}}

# Correct comparison matrix covering every feasible scheme.
GOOD_COMPARISON = {
    "schemes": {
        "A": {"cost": 100, "quality": 0.9},
        "B": {"cost": 80, "quality": 0.7},
        "C": {"cost": 120, "quality": 0.5},
    }
}


def _make_task(scenario=SYNTH_SCENARIO, library=SYNTH_LIBRARY):
    meta = TaskMetadata(
        task_id="synthetic",
        domain="telecom",
        task_type="conceptual-design",
        difficulty="medium",
        requirement="",
        scenario=scenario,
        l7_config={"scheme_library": library},
    )
    return types.SimpleNamespace(metadata=meta)


def _write_ws(tmp_path: Path, comparison: dict, recommendation: dict) -> Path:
    (tmp_path / "comparison.yaml").write_text(yaml.safe_dump(comparison), encoding="utf-8")
    (tmp_path / "recommendation.yaml").write_text(
        yaml.safe_dump(recommendation), encoding="utf-8"
    )
    return tmp_path


# ── Pure helper functions ─────────────────────────────────────────────────


def test_weighted_scores_ranks_by_scenario_weights():
    feasible = {
        sid: s["criteria"]
        for sid, s in SYNTH_LIBRARY["schemes"].items()
        if s["feasible"]
    }
    scores = weighted_scores(
        feasible, SYNTH_SCENARIO["criteria_weights"], SYNTH_LIBRARY["criteria_directions"]
    )
    ranked = sorted(scores, key=lambda k: -scores[k])
    assert ranked[0] == "A"
    assert rank_of(scores, "A") == 1
    assert rank_of(scores, "B") == 2
    assert rank_of(scores, "C") == 3


def test_pareto_front_excludes_dominated_scheme():
    feasible = {
        sid: s["criteria"]
        for sid, s in SYNTH_LIBRARY["schemes"].items()
        if s["feasible"]
    }
    front = pareto_front(
        feasible, SYNTH_SCENARIO["criteria_weights"], SYNTH_LIBRARY["criteria_directions"]
    )
    assert front == {"A", "B"}  # C is dominated by A


# ── Critic tiers ──────────────────────────────────────────────────────────


def test_optimal_recommendation_passes_with_full_score(tmp_path):
    ws = _write_ws(tmp_path, GOOD_COMPARISON, {"recommended": "A", "rationale": "best"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is True
    assert res.score == 1.0
    assert res.artifacts["rank_of_recommended"] == 1


def test_suboptimal_but_pareto_recommendation_passes_with_lower_score(tmp_path):
    ws = _write_ws(tmp_path, GOOD_COMPARISON, {"recommended": "B"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is True  # B is Pareto-optimal, just not weighted-optimal
    assert res.score < 1.0
    assert res.artifacts["rank_of_recommended"] == 2


def test_pareto_dominated_recommendation_fails_tier3(tmp_path):
    ws = _write_ws(tmp_path, GOOD_COMPARISON, {"recommended": "C"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is False
    assert any("Pareto-dominated" in c for c in res.comments)


def test_infeasible_recommendation_fails_tier1(tmp_path):
    ws = _write_ws(tmp_path, GOOD_COMPARISON, {"recommended": "D"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is False
    assert any("infeasible" in c for c in res.comments)


def test_unknown_recommendation_fails_tier1(tmp_path):
    ws = _write_ws(tmp_path, GOOD_COMPARISON, {"recommended": "Z"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is False
    assert any("not part of the design space" in c for c in res.comments)


def test_fabricated_matrix_value_fails_tier2(tmp_path):
    bad = {"schemes": {**GOOD_COMPARISON["schemes"], "B": {"cost": 999, "quality": 0.7}}}
    ws = _write_ws(tmp_path, bad, {"recommended": "A"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is False
    assert any("differs from bench" in c for c in res.comments)


def test_missing_feasible_scheme_in_matrix_fails_tier2(tmp_path):
    incomplete = {"schemes": {"A": {"cost": 100, "quality": 0.9}}}
    ws = _write_ws(tmp_path, incomplete, {"recommended": "A"})
    res = DecisionCritic().evaluate(ws, _make_task())
    assert res.passed is False
    assert any("missing feasible scheme" in c for c in res.comments)


def test_missing_deliverable_fails(tmp_path):
    (tmp_path / "recommendation.yaml").write_text("recommended: A\n", encoding="utf-8")
    res = DecisionCritic().evaluate(tmp_path, _make_task())
    assert res.passed is False
    assert any("comparison.yaml" in c for c in res.comments)


def test_scoring_is_reproducible(tmp_path):
    ws = _write_ws(tmp_path, GOOD_COMPARISON, {"recommended": "A"})
    task = _make_task()
    first = DecisionCritic().evaluate(ws, task)
    second = DecisionCritic().evaluate(ws, task)
    assert first == second  # dataclass equality over passed/score/comments/artifacts


# ── Shipped MVP task ──────────────────────────────────────────────────────


def test_shipped_reference_solution_is_optimal_and_reproducible():
    task = TaskInstance(TASKS / "aidc-scheme-selection-001")
    critic = DecisionCritic()
    first = critic.evaluate(task.solution_dir, task)
    second = critic.evaluate(task.solution_dir, task)
    assert first.passed is True
    assert first.score == 1.0
    assert first.artifacts["recommended"] == "liquid-container"
    assert first.artifacts["rank_of_recommended"] == 1
    assert first == second
