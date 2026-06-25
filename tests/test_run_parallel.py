"""Tests for parallel rollout execution in ``sd-hwe-bench run``."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from sd_hwe_bench.commands.run import (
    RolloutJob,
    _effective_jobs,
    _run_parallel,
    _run_rollout,
)
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.sandbox.workspace import Workspace
from sd_hwe_bench.settings import settings


class TestEffectiveJobs:
    def test_auto_uses_conservative_default(self):
        expected = min(4, (__import__("os").cpu_count() or 1))
        assert _effective_jobs(-1) == expected

    def test_explicit_value_preserved(self):
        assert _effective_jobs(2) == 2
        assert _effective_jobs(8) == 8

    def test_zero_normalized_to_one(self):
        assert _effective_jobs(0) == 1


class TestWorkspaceAttemptUniqueness:
    def test_attempt_suffix_prevents_collision(self):
        with tempfile.TemporaryDirectory() as td:
            run_root = Path(td) / "runs"
            ws_a = Workspace.create(
                run_root=run_root,
                task_id="test/task-001",
                actor_name="kimi",
                attempt=0,
            )
            ws_b = Workspace.create(
                run_root=run_root,
                task_id="test/task-001",
                actor_name="kimi",
                attempt=1,
            )
            assert ws_a.run_dir != ws_b.run_dir
            assert ws_a.run_dir.exists()
            assert ws_b.run_dir.exists()

    def test_manifest_records_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace.create(
                run_root=Path(td) / "runs",
                task_id="test/task-001",
                actor_name="kimi",
                attempt=3,
            )
            assert ws.read_manifest()["attempt"] == 3


def _copy_minimal_task(dst_root: Path, task_id: str) -> Path:
    """Create a self-contained minimal task by copying an existing scaffold."""
    src_task = Path("tasks") / "telecom" / "telecom-rack-001"
    if not src_task.exists():
        pytest.skip("Reference task telecom/telecom-rack-001 not found")

    domain, name = task_id.split("/")
    dst_task = dst_root / "tasks" / domain / name
    dst_task.mkdir(parents=True, exist_ok=True)

    # Copy scaffold.
    shutil.copytree(src_task / "scaffold", dst_task / "scaffold", dirs_exist_ok=True)

    # Copy solution so TaskInstance has it (not used in these tests).
    if (src_task / "solution").exists():
        shutil.copytree(src_task / "solution", dst_task / "solution", dirs_exist_ok=True)

    # Read and patch task metadata.
    task_yaml = src_task / "task.yaml"
    raw = task_yaml.read_text(encoding="utf-8")
    raw = raw.replace("task_id: telecom/telecom-rack-001", f"task_id: {task_id}")
    (dst_task / "task.yaml").write_text(raw, encoding="utf-8")

    return dst_task


class TestRunRollout:
    def test_run_rollout_creates_workspace_even_if_actor_missing(self):
        # The ``kimi`` CLI is not installed in the test environment, so the
        # actor will fail. The scaffold is already valid, so scoring should pass.
        with tempfile.TemporaryDirectory() as td:
            dataset_root = Path(td) / "dataset"
            dataset_root.mkdir()
            (dataset_root / "tasks").mkdir()
            _copy_minimal_task(dataset_root, "test/test-001")

            result = _run_rollout(
                job=RolloutJob(task_id="test/test-001", attempt=0),
                dataset_path=dataset_root,
                run_dir=Path(td) / "runs",
                actor_spec="kimi",
                sandbox="none",
                sandbox_image=settings.DEFAULT_SANDBOX_IMAGE,
                piki_ref=None,
                timeout=60,
                rubrics=False,
                rubrics_model=None,
                verbose=False,
            )

            assert result["task_id"] == "test/test-001"
            assert result["attempt"] == 0
            assert result["success"] is True
            assert Path(result["run_dir"]).exists()
            assert (Path(result["run_dir"]) / "manifest.json").exists()


class TestRunParallel:
    def test_run_parallel_two_attempts(self):
        with tempfile.TemporaryDirectory() as td:
            dataset_root = Path(td) / "dataset"
            dataset_root.mkdir()
            (dataset_root / "tasks").mkdir()
            _copy_minimal_task(dataset_root, "test/test-001")

            ds = Dataset(dataset_root)
            all_scores = _run_parallel(
                task_ids=["test/test-001"],
                passes=2,
                ds=ds,
                run_dir=Path(td) / "runs",
                actor="kimi",
                sandbox="none",
                sandbox_image=settings.DEFAULT_SANDBOX_IMAGE,
                piki_ref=None,
                timeout=60,
                rubrics=False,
                rubrics_model=None,
                jobs=2,
                verbose=False,
            )

            assert len(all_scores) == 1
            assert len(all_scores[0]) == 2
            assert all(s.success for s in all_scores[0])

            run_dirs = list((Path(td) / "runs").iterdir())
            assert len(run_dirs) == 2
            assert all((d / "manifest.json").exists() for d in run_dirs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
