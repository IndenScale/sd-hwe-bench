"""Tests for the SD-HWE-Bench scoring framework."""

import tempfile
from pathlib import Path

import pytest

from sd_hwe_bench.scorer import (
    LAYER_WEIGHTS,
    LayerScore,
    TaskScore,
    _check_deliverable,
    _layer_scores_from_static,
    _static_check_yaml,
    compute_partial_credit,
    compute_pass_at_k,
    score_task,
)


class TestLayerWeights:
    def test_all_layers_present(self):
        assert "L0" in LAYER_WEIGHTS
        assert "L1" in LAYER_WEIGHTS
        assert "L2" in LAYER_WEIGHTS
        assert "L3" in LAYER_WEIGHTS
        assert "L4" in LAYER_WEIGHTS

    def test_weights_sum_to_less_than_one(self):
        non_gate = sum(w for k, w in LAYER_WEIGHTS.items() if k != "L0")
        assert non_gate < 1.0

    def test_gate_is_zero(self):
        assert LAYER_WEIGHTS["L0"] == 0.0


class TestStaticCheckYaml:
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as td:
            result = _static_check_yaml(Path(td))
            assert result["errors"]["L0"]  # should have "No YAML files found"

    def test_valid_device_instance(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "srv.yaml").write_text("id: SRV-01\nmodel: generic-server\n")
            result = _static_check_yaml(Path(td))
            assert result["errors"]["L0"] == []
            assert result["errors"]["L1"] == []
            assert result["errors"]["L2"] == []
            assert result["declared_count"] == 1

    def test_missing_id_field(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "bad.yaml").write_text("model: generic-server\nname: BAD\n")
            result = _static_check_yaml(Path(td))
            assert len(result["errors"]["L1"]) >= 1
            assert "missing 'id'" in result["errors"]["L1"][0].lower()

    def test_undefined_reference(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "layout.yaml").write_text(
                "- instance: GHOST\n  position_u: 10\n  rack_id: RACK-MISSING\n"
            )
            result = _static_check_yaml(Path(td))
            l2_errors = result["errors"]["L2"]
            assert any("GHOST" in e for e in l2_errors)
            assert any("RACK-MISSING" in e for e in l2_errors)

    def test_valid_reference(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "srv.yaml").write_text("id: SRV-01\nmodel: generic-server\n")
            (Path(td) / "rack.yaml").write_text("id: RACK-A01\nfamily: RackFamily\n")
            (Path(td) / "layout.yaml").write_text(
                "- instance: SRV-01\n  position_u: 10\n  rack_id: RACK-A01\n"
            )
            result = _static_check_yaml(Path(td))
            assert result["errors"]["L2"] == []
            assert result["declared_count"] == 2

    def test_model_file_skipped(self):
        """Model definition files (no 'id' field, in models/ dir) should be skipped."""
        with tempfile.TemporaryDirectory() as td:
            models_dir = Path(td) / "models"
            models_dir.mkdir()
            (models_dir / "server.yaml").write_text(
                "model: generic-server\nfamily: ServerFamily\nheight_u: 2\n"
            )
            result = _static_check_yaml(Path(td))
            assert result["errors"]["L1"] == []
            assert "models/server.yaml" in result.get("model_files", [])

    def test_yaml_parse_error(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "bad.yaml").write_text(":: not valid yaml :: <<< >>>")
            result = _static_check_yaml(Path(td))
            assert len(result["errors"]["L0"]) >= 1

    def test_nested_source_target_references(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "srv.yaml").write_text("id: SRV-01\nmodel: generic-server\n")
            (Path(td) / "sw.yaml").write_text("id: SW-01\nmodel: access-switch\n")
            (Path(td) / "conn.yaml").write_text(
                "id: CONN-1\nsource: {instance: SRV-01, port: eth0}\n"
                "target: {instance: SW-01, port: Gi1/0/1}\n"
            )
            result = _static_check_yaml(Path(td))
            assert result["errors"]["L2"] == []

    def test_port_reference_slash_format(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "srv.yaml").write_text("id: SRV-01\nmodel: generic-server\n")
            (Path(td) / "conn.yaml").write_text(
                "id: CONN-1\nfrom_port: SRV-01/eth0\nto_port: GHOST/Gi1/0/1\n"
            )
            result = _static_check_yaml(Path(td))
            # SRV-01 exists, GHOST does not
            l2 = result["errors"]["L2"]
            assert any("GHOST" in e for e in l2)
            assert not any("SRV-01" in e for e in l2)


class TestLayerScoresFromStatic:
    def test_all_clean(self):
        score = TaskScore(task_id="test", success=False)
        static = {"errors": {"L0": [], "L1": [], "L2": []}}
        _layer_scores_from_static(score, static)
        assert score.layers["L0"].passed == 1
        assert score.layers["L1"].passed == 1
        assert score.layers["L2"].passed == 1
        # All layers pass when static checks are clean
        expected = (
            LAYER_WEIGHTS["L1"] + LAYER_WEIGHTS["L2"]
            + LAYER_WEIGHTS["L3"] + LAYER_WEIGHTS["L4"]
        )
        assert score.overall_score == expected

    def test_l1_has_error(self):
        score = TaskScore(task_id="test", success=False)
        static = {"errors": {"L0": [], "L1": ["missing id"], "L2": []}}
        _layer_scores_from_static(score, static)
        assert score.layers["L1"].passed == 0
        assert score.layers["L1"].failed == 1

    def test_preserves_l3_l4_untested_note(self):
        score = TaskScore(task_id="test", success=False)
        static = {"errors": {"L0": [], "L1": [], "L2": []}}
        _layer_scores_from_static(score, static)
        # L3/L4 pass when static checks are clean (no errors)
        assert score.layers["L3"].passed == 1
        assert score.layers["L4"].passed == 1


class TestScoreTask:
    def test_scores_reference_solution(self, tasks_dir):
        """Reference solutions should pass all static checks."""
        score = score_task(
            "telecom/comprehensive-001",
            tasks_dir / "telecom/comprehensive-001/solution",
            expected_deliverables=["bom-csv", "power-budget", "port-map",
                                   "rack-face-panel-svg", "cable-list"],
        )
        assert score.layers["L0"].passed == 1
        assert score.layers["L1"].passed == 1
        assert score.layers["L2"].passed == 1

    def test_scores_all_reference_solutions(self, tasks_dir):
        """Every task's reference solution should pass L0-L2."""
        task_ids = [
            "telecom/comprehensive-001",
            "telecom/connection-design-001",
            "telecom/instance-declare-001",
            "telecom/layout-design-001",
            "telecom/mating-design-001",
        ]
        for tid in task_ids:
            task_dir = tasks_dir / tid / "solution"
            score = score_task(tid, task_dir)
            assert score.layers["L0"].passed == 1, f"{tid}: L0 failed"
            assert score.layers["L1"].passed == 1, f"{tid}: L1 failed"
            assert score.layers["L2"].passed == 1, f"{tid}: L2 failed"

    def test_empty_output_scores_zero(self):
        with tempfile.TemporaryDirectory() as td:
            score = score_task("empty-test", Path(td))
            assert score.layers["L0"].failed == 1

    def test_task_loads_rubrics(self, tasks_dir):
        """Verify tasks with rubrics in task.yaml load correctly."""
        from sd_hwe_bench.task import TaskInstance
        task = TaskInstance(tasks_dir / "telecom/comprehensive-001")
        assert len(task.metadata.rubrics) >= 1
        rubric = task.metadata.rubrics[0]
        assert rubric.name == "completeness"
        assert len(rubric.criteria) >= 4
        assert rubric.threshold == 0.6

    def test_score_task_without_rubrics(self, tasks_dir):
        """Scoring without rubrics enabled should not populate rubric fields."""
        score = score_task(
            "telecom/comprehensive-001",
            tasks_dir / "telecom/comprehensive-001/solution",
            rubric_sets=None,  # rubrics not enabled
        )
        assert score.rubric_results == []
        assert score.rubric_score is None


class TestComputePassAtK:
    def test_all_pass(self):
        scores = [[TaskScore(task_id="a", success=True)]]
        assert compute_pass_at_k(scores, 1) == 1.0

    def test_all_fail(self):
        scores = [[TaskScore(task_id="a", success=False)]]
        assert compute_pass_at_k(scores, 1) == 0.0

    def test_mixed(self):
        scores = [
            [TaskScore(task_id="a", success=True)],
            [TaskScore(task_id="b", success=False)],
        ]
        assert compute_pass_at_k(scores, 1) == 0.5

    def test_pass_at_3(self):
        scores = [[
            TaskScore(task_id="a", success=False),
            TaskScore(task_id="a", success=False),
            TaskScore(task_id="a", success=True),
        ]]
        assert compute_pass_at_k(scores, 3) == 1.0
        assert compute_pass_at_k(scores, 1) == 0.0

    def test_empty(self):
        assert compute_pass_at_k([], 1) == 0.0


class TestComputePartialCredit:
    def test_basic(self):
        scores = [
            TaskScore(task_id="a", success=True, overall_score=0.85,
                      layers={
                          "L0": LayerScore("L0", 1, 1, 0),
                          "L1": LayerScore("L1", 1, 1, 0),
                          "L2": LayerScore("L2", 1, 0, 1),
                      }),
        ]
        result = compute_partial_credit(scores)
        l2 = next(r for r in result if r["layer"] == "L2")
        assert l2["pass_rate"] == 0.0
        l1 = next(r for r in result if r["layer"] == "L1")
        assert l1["pass_rate"] == 1.0


class TestCheckDeliverable:
    def test_no_dist_dir(self):
        with tempfile.TemporaryDirectory() as td:
            assert _check_deliverable(Path(td), "bom-csv") is False

    def test_bom_found_by_recursive_search(self):
        with tempfile.TemporaryDirectory() as td:
            dist = Path(td) / "dist" / "采购清单"
            dist.mkdir(parents=True)
            (dist / "bom.csv").write_text("item,qty\nserver,8\n")
            assert _check_deliverable(Path(td), "bom-csv") is True

    def test_unknown_deliverable(self):
        with tempfile.TemporaryDirectory() as td:
            assert _check_deliverable(Path(td), "nonexistent") is False

    def test_piki_toml_dist_config(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "piki.toml").write_text(
                "[generators.dist]\nroot = \"output\"\n\n"
                "[generators.dist.targets]\nbom-csv = \"bom\"\n"
            )
            target = Path(td) / "output" / "bom" / "bom.csv"
            target.parent.mkdir(parents=True)
            target.write_text("item,qty\n")
            assert _check_deliverable(Path(td), "bom-csv") is True


@pytest.fixture
def tasks_dir():
    return Path(__file__).parent.parent / "tasks"
