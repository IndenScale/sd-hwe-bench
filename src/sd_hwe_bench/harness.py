"""Evaluation harness — legacy scoring and reporting utilities.

The active CLI now lives in ``sd_hwe_bench.cli`` and uses the actor/critic
pipeline directly. This module is retained for backward-compatible report
formatting and the legacy ``run`` helper.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.scorer import TaskScore, compute_pass_at_k, score_task

logger = logging.getLogger(__name__)


class Harness:
    """Benchmark evaluation harness."""

    def __init__(self, dataset_root: Path):
        self.dataset = Dataset(dataset_root)

    # ── Legacy interface (compatible with current CLI) ──────────────────

    def run(
        self,
        task_ids: list[str],
        agent_cmd: str | None = None,
        agent_output_dir: Path | None = None,
        rubrics_enabled: bool = False,
        rubrics_model: str | None = None,
    ) -> list[list[TaskScore]]:
        """Run benchmark — legacy mode (single pass, pre-output or shell agent)."""
        results: list[list[TaskScore]] = []

        for task_id in task_ids:
            task = self.dataset.load_task(task_id)
            task_scores: list[TaskScore] = []

            rubric_sets = task.metadata.rubrics if rubrics_enabled else None
            requirement = task.metadata.requirement

            if agent_output_dir:
                score = score_task(
                    task_id=task_id,
                    agent_output_dir=Path(agent_output_dir),
                    expected_deliverables=task.metadata.expected_deliverables,
                    rubric_sets=rubric_sets,
                    requirement=requirement,
                    rubrics_model=rubrics_model,
                    task=task,
                )
                task_scores.append(score)
            elif agent_cmd:
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_dir = Path(tmpdir) / "output"
                    if task.scaffold_dir.exists():
                        shutil.copytree(task.scaffold_dir, output_dir)
                    else:
                        output_dir.mkdir(parents=True)

                    try:
                        subprocess.run(
                            agent_cmd,
                            shell=True,
                            env={
                                "TASK_DIR": str(task.task_dir),
                                "OUTPUT_DIR": str(output_dir),
                                "REQUIREMENT": task.requirement,
                            },
                            timeout=300,
                            capture_output=True,
                        )
                    except subprocess.TimeoutExpired:
                        pass

                    score = score_task(
                        task_id=task_id,
                        agent_output_dir=output_dir,
                        expected_deliverables=task.metadata.expected_deliverables,
                        rubric_sets=rubric_sets,
                        requirement=requirement,
                        rubrics_model=rubrics_model,
                        task=task,
                    )
                    task_scores.append(score)
            else:
                score = score_task(
                    task_id=task_id,
                    agent_output_dir=task.solution_dir,
                    expected_deliverables=task.metadata.expected_deliverables,
                    rubric_sets=rubric_sets,
                    requirement=requirement,
                    rubrics_model=rubrics_model,
                    task=task,
                )
                task_scores.append(score)

            results.append(task_scores)

        return results

    # ── Reporting ───────────────────────────────────────────────────────

    def report(self, results: list[list[TaskScore]], format: str = "text") -> str:
        if format == "json":
            return self._report_json(results)
        elif format == "markdown":
            return self._report_markdown(results)
        else:
            return self._report_text(results)

    def report_multi_model(
        self,
        all_results: dict[str, list[list[TaskScore]]],
        format: str = "markdown",
    ) -> str:
        """Generate a multi-model comparison report."""
        lines: list[str] = ["# SD-HWE-Bench Multi-Model Results\n"]

        # Per-model summary
        lines.append("## Model Comparison\n")
        lines.append("| Model | Pass@1 | Avg Score | Avg Rubric |")
        lines.append("|-------|--------|-----------|------------|")

        for model_id, task_results in all_results.items():
            pass1 = compute_pass_at_k(task_results, k=1)
            all_scores = [s for scores in task_results for s in scores[:1]]
            avg_score = (
                sum(s.overall_score for s in all_scores) / len(all_scores)
                if all_scores else 0.0
            )
            rubric_scores = [s.rubric_score for s in all_scores if s.rubric_score is not None]
            avg_rubric = sum(rubric_scores) / len(rubric_scores) if rubric_scores else 0.0
            lines.append(
                f"| {model_id} | {pass1:.0%} | {avg_score:.0%} | {avg_rubric:.0%} |"
            )
        lines.append("")

        # Per-task detail per model
        task_ids: list[str] = []
        for task_results in all_results.values():
            for scores in task_results:
                if scores:
                    task_ids.append(scores[0].task_id)
        task_ids = sorted(set(task_ids))

        for tid in task_ids:
            lines.append(f"## {tid}\n")
            lines.append("| Model | Pass | Score | L1 | L2 | L3 | L4 | Rubric |")
            lines.append("|-------|------|-------|----|----|----|----|--------|")

            for model_id, task_results in all_results.items():
                for scores in task_results:
                    if not scores:
                        continue
                    s = scores[0]
                    if s.task_id != tid:
                        continue
                    status = "✅" if s.success else "❌"
                    l1 = "✅" if s.layers.get("L1") and s.layers["L1"].passed else "❌"
                    l2 = "✅" if s.layers.get("L2") and s.layers["L2"].passed else "❌"
                    l3 = "✅" if s.layers.get("L3") and s.layers["L3"].passed else "❌"
                    l4 = "✅" if s.layers.get("L4") and s.layers["L4"].passed else "❌"
                    rubric = f"{s.rubric_score:.0%}" if s.rubric_score is not None else "—"
                    lines.append(
                        f"| {model_id} | {status} | {s.overall_score:.0%} | {l1} | {l2} | {l3} | {l4} | {rubric} |"
                    )
            lines.append("")

        return "\n".join(lines)

    def _report_text(self, results: list[list[TaskScore]]) -> str:
        lines = ["=== SD-HWE-Bench Results ===\n"]
        total_tasks = len(results)
        passed_tasks = sum(
            1 for scores in results if scores and scores[0].success
        )
        avg_score = (
            sum(scores[0].overall_score for scores in results if scores) / total_tasks
            if total_tasks > 0
            else 0.0
        )

        lines.append(f"Tasks evaluated: {total_tasks}")
        lines.append(f"Passed (Pass@1): {passed_tasks}/{total_tasks} ({passed_tasks/total_tasks:.1%})")
        lines.append(f"Average score: {avg_score:.2%}")
        lines.append("")

        layer_totals = {"L0": 0, "L1": 0, "L2": 0, "L3": 0, "L4": 0}
        layer_passed = {"L0": 0, "L1": 0, "L2": 0, "L3": 0, "L4": 0}
        for scores in results:
            if not scores:
                continue
            for layer_name, layer_score in scores[0].layers.items():
                if layer_name in layer_totals:
                    layer_totals[layer_name] += layer_score.total
                    layer_passed[layer_name] += layer_score.passed

        lines.append("Layer Breakdown:")
        for layer in ["L0", "L1", "L2", "L3", "L4"]:
            t, p = layer_totals[layer], layer_passed[layer]
            rate = p / t if t > 0 else 0.0
            lines.append(f"  {layer}: {p}/{t} ({rate:.1%})")

        rubric_scores: list[float] = []
        for scores in results:
            if scores and scores[0].rubric_score is not None:
                rubric_scores.append(scores[0].rubric_score)
        if rubric_scores:
            avg_rubric = sum(rubric_scores) / len(rubric_scores)
            lines.append(f"\nLLM-as-Judge Rubric Score (avg): {avg_rubric:.2%}")

        lines.append("")
        lines.append("Per-Task Results:")
        for scores in results:
            if not scores:
                continue
            s = scores[0]
            status = "PASS" if s.success else "FAIL"
            rubric_info = ""
            if s.rubric_score is not None:
                rubric_info = f" | Rubric: {s.rubric_score:.2%}"
            lines.append(f"  [{status}] {s.task_id} — score: {s.overall_score:.2%}{rubric_info}")

        return "\n".join(lines)

    def _report_json(self, results: list[list[TaskScore]]) -> str:
        output = []
        for scores in results:
            if not scores:
                continue
            s = scores[0]
            entry = {
                "task_id": s.task_id,
                "success": s.success,
                "overall_score": s.overall_score,
                "layers": {
                    name: {
                        "passed": ls.passed,
                        "total": ls.total,
                        "failed": ls.failed,
                    }
                    for name, ls in s.layers.items()
                },
                "deliverables": s.deliverable_scores,
            }
            if s.rubric_score is not None:
                entry["rubric_score"] = s.rubric_score
                entry["rubric_results"] = [
                    {
                        "rubric_name": rr.rubric_name,
                        "overall_score": rr.overall_score,
                        "passed": rr.passed,
                        "threshold": rr.threshold,
                        "criteria": [
                            {
                                "id": rs.criterion_id,
                                "name": rs.name,
                                "score": rs.score,
                                "weight": rs.weight,
                                "reason": rs.reason,
                            }
                            for rs in rr.criteria_scores
                        ],
                    }
                    for rr in s.rubric_results
                ]
            output.append(entry)
        return json.dumps(output, indent=2)

    def _report_markdown(self, results: list[list[TaskScore]]) -> str:
        lines = ["# SD-HWE-Bench Results\n"]
        total = len(results)
        passed = sum(1 for s in results if s and s[0].success)
        lines.append(f"**Pass@1**: {passed}/{total} ({passed/total:.1%})\n")
        lines.append("| Task ID | Status | Score | L1 | L2 | L3 | L4 | Rubric |")
        lines.append("|---------|--------|-------|----|----|----|----|--------|")
        for scores in results:
            if not scores:
                continue
            s = scores[0]
            status = "✅" if s.success else "❌"
            l1 = "✅" if s.layers.get("L1") and s.layers["L1"].passed else "❌"
            l2 = "✅" if s.layers.get("L2") and s.layers["L2"].passed else "❌"
            l3 = "✅" if s.layers.get("L3") and s.layers["L3"].passed else "❌"
            l4 = "✅" if s.layers.get("L4") and s.layers["L4"].passed else "❌"
            rubric = f"{s.rubric_score:.0%}" if s.rubric_score is not None else "—"
            lines.append(
                f"| {s.task_id} | {status} | {s.overall_score:.0%} | {l1} | {l2} | {l3} | {l4} | {rubric} |"
            )
        return "\n".join(lines)


def _task_metadata_to_dict(task: object) -> dict:
    """Extract task metadata as a plain dict for prompt building."""
    if hasattr(task, "metadata"):
        meta = task.metadata
        if hasattr(meta, "model_dump"):
            return meta.model_dump()
        if hasattr(meta, "to_dict"):
            return meta.to_dict()
    return {
        "task_id": getattr(task, "task_id", "unknown"),
        "name": getattr(task, "name", ""),
        "requirement": getattr(task, "requirement", ""),
    }
