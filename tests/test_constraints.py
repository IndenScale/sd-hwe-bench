"""Tests for constraint-gap catalog and diagnostic helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sd_hwe_bench.constraints import (
    build_constraint_catalog,
    collect_score_diagnostics,
    parse_constraint_selectors,
    render_diagnostics,
    summarize_diagnostics,
)
from sd_hwe_bench.critics.base import CriticResult
from sd_hwe_bench.scorer import LayerScore, TaskScore
from sd_hwe_bench.task import ConstraintMetadata, Difficulty, Domain, TaskMetadata, TaskType


def _task_with_meta(meta: TaskMetadata):
    return SimpleNamespace(metadata=meta, task_id=meta.task_id, task_dir=Path("/missing"))


def test_catalog_uses_explicit_task_constraints():
    meta = TaskMetadata(
        task_id="telecom/test",
        domain=Domain.TELECOM,
        task_type=TaskType.COMPREHENSIVE,
        difficulty=Difficulty.MEDIUM,
        requirement="Do the task.",
        constraints=[
            ConstraintMetadata(
                id="C-ELEC-001",
                family="electrical",
                layer="L3",
                critic="piki",
                localization="field-level",
            )
        ],
    )

    catalog = build_constraint_catalog(_task_with_meta(meta))

    assert catalog.coverage_summary()["total"] == 1
    assert catalog.by_id["C-ELEC-001"].family == "electrical"


def test_catalog_infers_scoring_layer_constraints():
    meta = TaskMetadata(
        task_id="telecom/test",
        domain=Domain.TELECOM,
        task_type=TaskType.COMPREHENSIVE,
        difficulty=Difficulty.MEDIUM,
        requirement="Do the task.",
        scoring_layers=["L0", "L1", "L2"],
        expected_deliverables=["bom-csv"],
    )

    catalog = build_constraint_catalog(_task_with_meta(meta))

    ids = {spec.id for spec in catalog.constraints}
    assert "telecom/test:L1" in ids
    assert "telecom/test:deliverable:bom-csv" in ids


def test_selector_parsing_and_random_mute_are_stable():
    meta = TaskMetadata(
        task_id="telecom/test",
        domain=Domain.TELECOM,
        task_type=TaskType.COMPREHENSIVE,
        difficulty=Difficulty.MEDIUM,
        requirement="Do the task.",
        scoring_layers=["L1", "L2", "L3", "L4"],
    )
    catalog = build_constraint_catalog(_task_with_meta(meta))

    selectors = parse_constraint_selectors("layer:L3,family:reference")
    selected = {spec.id for spec in catalog.selected(selectors)}
    assert "telecom/test:L2" in selected
    assert "telecom/test:L3" in selected

    first = [spec.id for spec in catalog.randomized(0.5, seed=7)]
    second = [spec.id for spec in catalog.randomized(0.5, seed=7)]
    assert first == second


def test_collect_and_render_diagnostics_respects_verbosity():
    meta = TaskMetadata(
        task_id="telecom/test",
        domain=Domain.TELECOM,
        task_type=TaskType.COMPREHENSIVE,
        difficulty=Difficulty.MEDIUM,
        requirement="Do the task.",
        constraints=[
            ConstraintMetadata(id="TELECOM-FK-001", family="reference", layer="L2", critic="piki")
        ],
    )
    catalog = build_constraint_catalog(_task_with_meta(meta))
    score = TaskScore(
        task_id="telecom/test",
        success=False,
        layers={"L2": LayerScore("L2", 1, 0, 1, ["TELECOM-FK-001: missing reference"])},
        critic_results=[
            CriticResult(
                name="piki",
                passed=False,
                artifacts={
                    "parsed": {
                        "results": [
                            {
                                "rule_id": "TELECOM-FK-001",
                                "passed": False,
                                "message": "RACK-X is referenced but missing",
                                "file": "layouts/layout.yaml",
                            }
                        ],
                        "diagnostics": [],
                    }
                },
            )
        ],
    )

    diagnostics = collect_score_diagnostics(score, catalog)
    assert len(diagnostics) == 1
    assert diagnostics[0].file == "layouts/layout.yaml"

    assert render_diagnostics(diagnostics, verbosity="none") == []
    coarse = render_diagnostics(diagnostics, verbosity="coarse")
    assert "layouts/layout.yaml" not in str(coarse)
    localized = render_diagnostics(diagnostics, verbosity="localized")
    assert localized[0]["file"] == "layouts/layout.yaml"


def test_collect_diagnostics_filters_positive_mixed_comments():
    meta = TaskMetadata(
        task_id="telecom/test",
        domain=Domain.TELECOM,
        task_type=TaskType.COMPREHENSIVE,
        difficulty=Difficulty.MEDIUM,
        requirement="Do the task.",
        constraints=[
            ConstraintMetadata(id="rack-face-panel-svg", family="deliverable", layer="Deliverable"),
            ConstraintMetadata(id="telecom/test:L0", family="syntax", layer="L0", critic="syntax"),
            ConstraintMetadata(id="numeric:file", family="static", layer="L3", critic="numeric"),
        ],
    )
    catalog = build_constraint_catalog(_task_with_meta(meta))
    score = TaskScore(
        task_id="telecom/test",
        success=False,
        layers={"L0": LayerScore("L0", 1, 0, 1, ["L0 passed: 30 YAML files valid"])},
        critic_results=[
            CriticResult(
                name="deliverable",
                passed=False,
                comments=[
                    "✓ power-budget: power-budget.csv found",
                    "rack-face-panel-svg: required deliverable not found",
                ],
            ),
            CriticResult(
                name="syntax",
                passed=False,
                comments=[
                    "L0 passed: 30 YAML files valid",
                    "models/bad.yaml: YAML parse error",
                ],
            ),
            CriticResult(
                name="numeric",
                passed=False,
                comments=[
                    "✓ power.yaml -> capacity_kw: 10 approx 10 (delta=0, tol=1.0%)",
                    "x cooling.yaml -> pue: expected <= 1.3",
                ],
            ),
        ],
    )

    diagnostics = collect_score_diagnostics(score, catalog)
    messages = [diag.message for diag in diagnostics]

    assert "✓ power-budget: power-budget.csv found" not in messages
    assert "L0 passed: 30 YAML files valid" not in messages
    assert "✓ power.yaml -> capacity_kw: 10 approx 10 (delta=0, tol=1.0%)" not in messages
    assert "rack-face-panel-svg: required deliverable not found" in messages
    assert "models/bad.yaml: YAML parse error" in messages
    assert "x cooling.yaml -> pue: expected <= 1.3" in messages


def test_diagnostic_summary_reports_muted_violation_rate():
    meta = TaskMetadata(
        task_id="telecom/test",
        domain=Domain.TELECOM,
        task_type=TaskType.COMPREHENSIVE,
        difficulty=Difficulty.MEDIUM,
        requirement="Do the task.",
        constraints=[
            ConstraintMetadata(id="C1", family="layout", layer="L5"),
            ConstraintMetadata(id="C2", family="thermal", layer="L4"),
        ],
    )
    catalog = build_constraint_catalog(_task_with_meta(meta))
    score = TaskScore(
        task_id="telecom/test",
        success=False,
        layers={"L5": LayerScore("L5", 1, 0, 1, ["C1: collision"])},
    )

    diagnostics = collect_score_diagnostics(score, catalog)
    summary = summarize_diagnostics(diagnostics, catalog, muted_constraint_ids={"C1"})

    assert summary["omission_density"] == 0.5
    assert summary["muted_constraint_violation_rate"] == 1.0
    assert summary["hidden_failed_constraints"] == ["C1"]


def test_collect_diagnostics_keeps_field_level_contract_items_distinct():
    meta = TaskMetadata(
        task_id="telecom/aidc",
        domain=Domain.TELECOM,
        task_type=TaskType.EPC,
        difficulty=Difficulty.HARD,
        requirement="Do the task.",
        evaluation=[{"critic": "epc", "layer": "L4"}],
    )
    catalog = build_constraint_catalog(_task_with_meta(meta))
    score = TaskScore(
        task_id="telecom/aidc",
        success=False,
        critic_results=[
            CriticResult(
                name="epc",
                passed=False,
                comments=[
                    "schedule.yaml activities[A01]: missing required field 'resources' mapping",
                    "resource-plan.yaml resources[crew-main]: missing required field 'daily_cost_cny'",
                    "contingency-policy.yaml decisions[A01]: missing required field 'decision'",
                ],
            )
        ],
    )

    diagnostics = collect_score_diagnostics(score, catalog)
    rendered = render_diagnostics(diagnostics, verbosity="localized")

    assert len(diagnostics) == 3
    keyed = {(item.get("file"), item.get("object_id"), item.get("field")) for item in rendered}
    assert ("schedule.yaml", "A01", "resources") in keyed
    assert ("resource-plan.yaml", "crew-main", "daily_cost_cny") in keyed
    assert ("contingency-policy.yaml", "A01", "decision") in keyed
