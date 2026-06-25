"""Regression tests: every reference solution must pass full scoring.

This catches canonical-data quality regressions early. If a reference solution
fails any critical layer or expected deliverable, the benchmark's Pass@1 /
leaderboard baselines become invalid.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.sandbox.runner import SandboxRunner
from sd_hwe_bench.scorer import score_task


@pytest.fixture(scope="module")
def dataset() -> Dataset:
    return Dataset(Path(__file__).parent.parent)


@pytest.fixture(scope="module")
def runner() -> SandboxRunner:
    # Use host piki for speed; reference solutions should be deterministic and
    # not depend on container quirks.
    return SandboxRunner(backend="none")


@pytest.mark.parametrize("task_id", sorted(Dataset(Path(__file__).parent.parent).discover()))
def test_reference_solution_passes_full_scoring(
    dataset: Dataset, runner: SandboxRunner, task_id: str
):
    """Reference solution for *task_id* must pass all critical layers + deliverables."""
    task = dataset.load_task(task_id)
    result = score_task(task.task_id, task.solution_dir, task=task, runner=runner)

    if not result.success:
        failures: list[str] = []
        for layer_name, layer in result.layers.items():
            if not layer.passed:
                failures.extend(f"  {layer_name}: {err}" for err in layer.errors)
        for deliverable, delivered in result.deliverable_scores.items():
            if not delivered:
                failures.append(f"  deliverable missing: {deliverable}")
        pytest.fail(f"Reference solution for {task_id} failed full scoring\n" + "\n".join(failures))
