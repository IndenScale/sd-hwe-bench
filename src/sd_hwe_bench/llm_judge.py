"""LLM-as-Judge evaluation using DeepEval GEval with rubric criteria."""

import dataclasses
import logging
import os
from pathlib import Path
from typing import Optional

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase
from deepeval.test_case.llm_test_case import SingleTurnParams

from sd_hwe_bench.task import RubricCriterion, RubricSet

logger = logging.getLogger(__name__)

# Default model: prefer DEEPSEEK_API_KEY env, then OPENAI_API_KEY
_DEFAULT_MODEL = "deepseek-chat" if os.getenv("DEEPSEEK_API_KEY") else "gpt-4.1-mini"


@dataclasses.dataclass
class RubricScore:
    """Score for a single rubric criterion."""

    criterion_id: str
    name: str
    score: float
    reason: str
    weight: float


@dataclasses.dataclass
class LLMJudgeResult:
    """Complete LLM-as-Judge evaluation result."""

    rubric_name: str
    overall_score: float
    passed: bool
    threshold: float
    criteria_scores: list[RubricScore]
    raw_errors: list[str] = dataclasses.field(default_factory=list)


def evaluate_single_criterion(
    criterion: RubricCriterion,
    requirement: str,
    actual_output: str,
    model: str = _DEFAULT_MODEL,
    timeout: int = 120,
) -> RubricScore:
    """Evaluate a single rubric criterion against the agent's output.

    Args:
        criterion: The rubric criterion to evaluate.
        requirement: The original task requirement (natural language).
        actual_output: The agent's YAML output as a string.
        model: LLM model name for judging.
        timeout: Timeout in seconds for the LLM call.

    Returns:
        RubricScore with score, reason, and weight.
    """
    metric = GEval(
        name=criterion.name,
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        criteria=_build_criteria(requirement, criterion),
        evaluation_steps=criterion.evaluation_steps or _default_steps(criterion),
        model=model,
        threshold=0.0,
        async_mode=False,
    )

    test_case = LLMTestCase(
        input=f"Requirement:\n{requirement}",
        actual_output=actual_output,
    )

    try:
        metric.measure(test_case)
        score = metric.score if metric.score is not None else 0.0
        reason = metric.reason or "No reason provided"
    except Exception as e:
        logger.warning("LLM judge failed for criterion %s: %s", criterion.id, e)
        score = 0.0
        reason = f"Evaluation error: {e}"

    return RubricScore(
        criterion_id=criterion.id,
        name=criterion.name,
        score=score,
        reason=reason,
        weight=criterion.weight,
    )


def evaluate_rubric_set(
    rubric_set: RubricSet,
    requirement: str,
    actual_output: str,
    model: str = _DEFAULT_MODEL,
    timeout: int = 120,
) -> LLMJudgeResult:
    """Evaluate an entire rubric set against the agent's output.

    Args:
        rubric_set: The rubric set to evaluate.
        requirement: The original task requirement.
        actual_output: The agent's YAML output as a string.
        model: LLM model name for judging.
        timeout: Timeout per criterion call.

    Returns:
        LLMJudgeResult with overall score and per-criterion breakdown.
    """
    criteria_scores: list[RubricScore] = []
    errors: list[str] = []

    for criterion in rubric_set.criteria:
        try:
            rs = evaluate_single_criterion(
                criterion, requirement, actual_output, model=model, timeout=timeout
            )
            criteria_scores.append(rs)
        except Exception as e:
            logger.exception("Criterion %s failed", criterion.id)
            errors.append(f"{criterion.id}: {e}")
            criteria_scores.append(
                RubricScore(
                    criterion_id=criterion.id,
                    name=criterion.name,
                    score=0.0,
                    reason=f"Evaluation failed: {e}",
                    weight=criterion.weight,
                )
            )

    # Weighted average
    total_weight = sum(rs.weight for rs in criteria_scores)
    if total_weight > 0:
        overall = sum(rs.score * rs.weight for rs in criteria_scores) / total_weight
    else:
        overall = 0.0

    return LLMJudgeResult(
        rubric_name=rubric_set.name,
        overall_score=overall,
        passed=overall >= rubric_set.threshold,
        threshold=rubric_set.threshold,
        criteria_scores=criteria_scores,
        raw_errors=errors,
    )


def collect_agent_output(project_dir: Path) -> str:
    """Collect all YAML files from an agent's output directory into a single string.

    Args:
        project_dir: Path to the agent's output directory (containing YAML instances, etc.)

    Returns:
        Concatenated YAML content as a string, with file paths as headers.
    """
    parts: list[str] = []
    yaml_files = sorted(project_dir.rglob("*.yaml")) + sorted(project_dir.rglob("*.yml"))

    for fpath in yaml_files:
        try:
            content = fpath.read_text()
            # Skip files that look like model definitions
            rel = str(fpath.relative_to(project_dir))
            if "models/" in rel:
                continue
            parts.append(f"# {rel}\n{content}")
        except Exception:
            continue

    if not parts:
        parts.append("(no YAML output files found)")

    return "\n\n".join(parts)


def _build_criteria(requirement: str, criterion: RubricCriterion) -> str:
    """Build the criteria string for GEval from requirement and rubric criterion."""
    return (
        f"You are evaluating a hardware engineering design output against this requirement:\n"
        f"---\n{requirement}\n---\n\n"
        f"Evaluate criterion: {criterion.name}\n"
        f"Description: {criterion.description}\n\n"
        f"Score on a scale of 0.0 to 1.0 where:\n"
        f"- 1.0: Fully compliant, all aspects correct\n"
        f"- 0.7: Mostly compliant, minor issues only\n"
        f"- 0.5: Partially compliant, significant gaps\n"
        f"- 0.3: Major issues, barely addresses requirement\n"
        f"- 0.0: Non-compliant or completely missing\n\n"
        f"Return ONLY a JSON object: {{\"score\": <float>, \"reason\": \"<explanation>\"}}"
    )


def _default_steps(criterion: RubricCriterion) -> list[str]:
    """Generate default evaluation steps for a criterion."""
    return [
        f"Carefully read the requirement and the agent's output",
        f"Identify whether the output addresses: {criterion.description}",
        f"Check for correctness, completeness, and consistency",
        f"Assign a score from 0.0 to 1.0 based on compliance level",
    ]
