"""Tests for critics."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from sd_hwe_bench.critics import DeliverableCritic, PikiCritic, SyntaxCritic
from sd_hwe_bench.critics.constructability import ConstructabilityCritic
from sd_hwe_bench.critics.epc import EPCCritic
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.sandbox.runner import SandboxRunner


@pytest.fixture
def dataset():
    return Dataset(Path(__file__).parent.parent)


class TestSyntaxCritic:
    def test_reference_solution_passes(self, dataset):
        task = dataset.load_task("telecom/comprehensive-001")
        critic = SyntaxCritic()
        result = critic.evaluate(task.solution_dir, task)
        assert result.passed
        assert result.score == 1.0

    def test_missing_expected_file_fails_l0(self, tmp_path):
        (tmp_path / "present.yaml").write_text(yaml.safe_dump({"id": "X"}), encoding="utf-8")
        task = SimpleNamespace(metadata=SimpleNamespace(expected_files=["missing.yaml"]))

        result = SyntaxCritic().evaluate(tmp_path, task)

        assert not result.passed
        assert any("Missing expected files" in c for c in result.comments)


class TestPikiCritic:
    def test_reference_solution_passes(self, dataset):
        task = dataset.load_task("telecom/comprehensive-001")
        critic = PikiCritic(runner=SandboxRunner(backend="none"))
        result = critic.evaluate(task.solution_dir, task)
        assert result.passed
        assert result.score > 0


class TestDeliverableCritic:
    def test_missing_deliverables(self, dataset):
        task = dataset.load_task("telecom/comprehensive-001")
        critic = DeliverableCritic()
        result = critic.evaluate(task.solution_dir, task)
        # Reference solution likely does not contain generated deliverables
        assert not result.passed
        assert result.score < 1.0


class TestAIDCSchemaDiagnostics:
    def test_epc_reports_cpml_field_contract_mismatches(self, tmp_path):
        (tmp_path / "schedule.yaml").write_text(
            yaml.safe_dump(
                {
                    "activities": [
                        {
                            "id": "A01",
                            "duration_days": 1,
                            "prerequisites": [],
                            "resource_requirements": {"crew": 1},
                            "weather_sensitive": True,
                            "max_wind_speed_m_s": 12,
                        }
                    ]
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        (tmp_path / "resource-plan.yaml").write_text(
            yaml.safe_dump(
                {"resources": [{"id": "crew", "capacity": 1, "daily_cost_cny": 1}]},
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        (tmp_path / "contingency-policy.yaml").write_text(
            yaml.safe_dump(
                {
                    "contingency_policy": [
                        {"activity_id": "A01", "type": "wait", "params": {}}
                    ]
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        task = SimpleNamespace(metadata=SimpleNamespace(l7_config={"deadline_days": 10}))

        result = EPCCritic(deadline_days=10, n_scenarios=1).evaluate(tmp_path, task)

        assert not result.passed
        comments = "\n".join(result.comments)
        assert "expected field 'predecessors'; found 'prerequisites' in activities A01" in comments
        assert "expected field 'resources'; found 'resource_requirements' in activities A01" in comments
        assert "expected field 'weather_limits'" in comments
        assert "expected root key 'decisions' as a list; found 'contingency_policy'" in comments

    def test_constructability_reports_construction_schema_contract_mismatches(self, tmp_path):
        facilities = tmp_path / "facilities"
        models = tmp_path / "models" / "facilities"
        construction = tmp_path / "construction"
        facilities.mkdir()
        models.mkdir(parents=True)
        construction.mkdir()
        (facilities / "CHILLER-01.yaml").write_text(
            yaml.safe_dump({"id": "CHILLER-01", "model": "chiller-10mw-facility"}),
            encoding="utf-8",
        )
        (models / "chiller-10mw-facility.yaml").write_text(
            yaml.safe_dump({"weight_kg": 15000}),
            encoding="utf-8",
        )
        (construction / "hoisting-plan.yaml").write_text(
            yaml.safe_dump(
                {
                    "hoisting_plan": {
                        "CHILLER-01": {
                            "day": 1,
                            "crane_ton": 30,
                            "radius_m": 12,
                            "clearance_mm": 1500,
                            "hoist_point": {"x_mm": 0, "y_mm": 0, "z_mm": 0},
                        }
                    }
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        (construction / "equipment-rental.yaml").write_text(
            yaml.safe_dump({"equipment_rental": {"main-crane": {"start_day": 0, "end_day": 1}}}),
            encoding="utf-8",
        )
        (construction / "vdc-workface.yaml").write_text(
            yaml.safe_dump(
                {
                    "vdc_workfaces": {
                        "WF-1": {
                            "zone": "north",
                            "access_gate": "GATE",
                            "max_wind_speed_m_s": 10,
                            "isolation_distance_mm": 1000,
                        }
                    }
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

        result = ConstructabilityCritic().evaluate(tmp_path, SimpleNamespace())

        assert not result.passed
        comments = "\n".join(result.comments)
        assert "expected root key 'hoists' as a list; found 'hoisting_plan'" in comments
        assert "expected root key 'equipment' as a list; found 'equipment_rental'" in comments
        assert "expected root key 'workfaces' as a list; found 'vdc_workfaces'" in comments

    def test_constructability_reports_facility_file_list_without_crashing(self, tmp_path):
        facilities = tmp_path / "facilities"
        models = tmp_path / "models" / "facilities"
        construction = tmp_path / "construction"
        facilities.mkdir()
        models.mkdir(parents=True)
        construction.mkdir()
        (facilities / "FACILITIES.yaml").write_text(
            yaml.safe_dump(
                [
                    {"id": "CHILLER-01", "model": "chiller-10mw-facility"},
                    {"id": "TR-A", "model": "transformer-40mva-facility"},
                ]
            ),
            encoding="utf-8",
        )
        (models / "chiller-10mw-facility.yaml").write_text(
            yaml.safe_dump({"weight_kg": 15000}),
            encoding="utf-8",
        )
        (models / "transformer-40mva-facility.yaml").write_text(
            yaml.safe_dump({"weight_kg": 20000}),
            encoding="utf-8",
        )
        (construction / "hoisting-plan.yaml").write_text(
            yaml.safe_dump({"hoists": []}),
            encoding="utf-8",
        )
        (construction / "equipment-rental.yaml").write_text(
            yaml.safe_dump(
                {"equipment": [{"type": "main-crane", "start_day": 1, "end_day": 2}]}
            ),
            encoding="utf-8",
        )
        (construction / "vdc-workface.yaml").write_text(
            yaml.safe_dump(
                {
                    "workfaces": [
                        {
                            "id": "WF-1",
                            "zone": "north",
                            "access_gate": "G1",
                            "max_wind_speed_m_s": 12,
                            "isolation_distance_mm": 1000,
                        },
                        {
                            "id": "WF-2",
                            "zone": "south",
                            "access_gate": "G2",
                            "max_wind_speed_m_s": 12,
                            "isolation_distance_mm": 1000,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = ConstructabilityCritic().evaluate(tmp_path, SimpleNamespace())

        assert not result.passed
        comments = "\n".join(result.comments)
        assert "FACILITIES.yaml: expected mapping at root; found list" in comments
        assert "Facility CHILLER-01: missing hoisting-plan entry" in comments

    def test_epc_reports_malformed_resource_shape_without_crashing(self, tmp_path):
        (tmp_path / "schedule.yaml").write_text(
            yaml.safe_dump(
                {
                    "activities": [
                        {
                            "id": "A01",
                            "duration_days": 1,
                            "resources": ["crew-main"],
                            "predecessors": [],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "resource-plan.yaml").write_text(
            yaml.safe_dump(
                {"resources": [{"id": "crew-main", "capacity": 1, "daily_cost_cny": 1}]}
            ),
            encoding="utf-8",
        )
        (tmp_path / "contingency-policy.yaml").write_text(
            yaml.safe_dump({"decisions": []}),
            encoding="utf-8",
        )
        task = SimpleNamespace(metadata=SimpleNamespace(l7_config={"deadline_days": 10}))

        result = EPCCritic(deadline_days=10, n_scenarios=1).evaluate(tmp_path, task)

        assert not result.passed
        assert any(
            "CPML parse error: schedule.yaml: 'activities[A01].resources' must be a mapping"
            in comment
            for comment in result.comments
        )
