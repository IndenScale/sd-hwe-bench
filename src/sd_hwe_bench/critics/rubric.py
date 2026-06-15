"""Rubric critic: LLM-as-Judge evaluation."""

from __future__ import annotations

from pathlib import Path

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.llm_judge import collect_agent_output, evaluate_rubric_set
from sd_hwe_bench.task import TaskInstance


class RubricCritic(Critic):
    """Evaluate agent output against task rubrics using an LLM judge."""

    name = "rubric"

    def __init__(self, model: str | None = None):
        self.model = model

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        if not task.metadata.rubrics:
            return CriticResult(
                name=self.name,
                passed=True,
                score=1.0,
                comments=["No rubrics defined for this task"],
            )

        output_text = collect_agent_output(workspace_root)
        comments: list[str] = []
        total_score = 0.0
        all_passed = True

        for rubric_set in task.metadata.rubrics:
            try:
                result = evaluate_rubric_set(
                    rubric_set,
                    requirement=task.metadata.requirement,
                    actual_output=output_text,
                    model=self.model,
                )
            except Exception as exc:
                comments.append(f"Rubric '{rubric_set.name}' evaluation failed: {exc}")
                all_passed = False
                continue

            status = "passed" if result.passed else "failed"
            comments.append(
                f"Rubric '{rubric_set.name}': {result.overall_score:.2f} "
                f"(threshold {result.threshold}) — {status}"
            )
            for cs in result.criteria_scores:
                comments.append(
                    f"  - {cs.name}: {cs.score:.2f} (weight {cs.weight}) — {cs.reason[:120]}"
                )

            total_score += result.overall_score
            if not result.passed:
                all_passed = False

        rubric_count = len(task.metadata.rubrics)
        score = total_score / rubric_count if rubric_count > 0 else 1.0

        return CriticResult(
            name=self.name,
            passed=all_passed,
            score=score,
            comments=comments,
        )
