"""Tests for critics."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from sd_hwe_bench.critics import DeliverableCritic, PikiCritic, SyntaxCritic
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
