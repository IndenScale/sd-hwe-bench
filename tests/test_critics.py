"""Tests for critics."""

from pathlib import Path

import pytest

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
