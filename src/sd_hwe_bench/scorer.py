"""Scoring framework — computes Pass@k using deterministic critics and optional rubrics.

Architecture:
- Critics run in sequence: Syntax (L0), Piki (L1-L4), Deliverable (L5/L6), Rubric (LLM judge).
- score_task orchestrates critics and produces a TaskScore.
- Legacy helper functions remain for backward compatibility and tests.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path
from typing import Any

from sd_hwe_bench.critics import (
    CriticResult,
    DeliverableCritic,
    PikiCritic,
    RubricCritic,
    SyntaxCritic,
)
from sd_hwe_bench.sandbox.runner import SandboxRunner
from sd_hwe_bench.task import RubricSet

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LayerScore:
    """Score for one check layer."""

    layer: str
    total: int
    passed: int
    failed: int
    errors: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TaskScore:
    """Complete score for one task attempt."""

    task_id: str
    success: bool
    layers: dict[str, LayerScore] = dataclasses.field(default_factory=dict)
    deliverable_scores: dict[str, bool] = dataclasses.field(default_factory=dict)
    overall_score: float = 0.0
    rubric_results: list[Any] = dataclasses.field(default_factory=list)
    rubric_score: float | None = None
    critic_results: list[CriticResult] = dataclasses.field(default_factory=list)


# Layer weights aligned with initiative doc
LAYER_WEIGHTS = {
    "L0": 0.0,   # Gate: must pass, but no points
    "L1": 0.10,
    "L2": 0.15,
    "L3": 0.40,
    "L4": 0.20,
    "L5": 0.0,
    "L6": 0.0,
}

DELIVERABLE_WEIGHT = 0.15
RUBRIC_WEIGHT = 0.0  # Rubrics are optional diagnostic, not included in overall_score by default


# ── Legacy static YAML checks (fallback when piki is unavailable) ─────────

def _static_check_yaml(project_dir: Path) -> dict[str, Any]:
    """Run static YAML checks (L0-L2) — fallback when piki is unavailable."""
    import yaml as _yaml

    errors: dict[str, list[str]] = {"L0": [], "L1": [], "L2": []}
    yaml_files = sorted(project_dir.rglob("*.yaml")) + sorted(project_dir.rglob("*.yml"))

    if not yaml_files:
        errors["L0"].append("No YAML files found in project directory")
        return {"errors": errors}

    declared_ids: set[str] = set()
    referenced_ids: set[str] = set()
    model_files: set[str] = set()

    for fpath in yaml_files:
        rel = str(fpath.relative_to(project_dir))
        try:
            raw = fpath.read_text()
            doc = _yaml.safe_load(raw)
        except _yaml.YAMLError as e:
            errors["L0"].append(f"{fpath.name}: YAML parse error: {e}")
            continue
        except Exception as e:
            errors["L0"].append(f"{fpath.name}: {e}")
            continue

        if doc is None:
            continue
        if not isinstance(doc, (dict, list)):
            continue

        is_model_file = (
            isinstance(doc, dict)
            and "id" not in doc
            and ("model" in doc or "family" in doc)
            and ("models" in rel or rel.startswith("models/"))
        )
        if is_model_file:
            model_files.add(rel)
            continue

        items = doc if isinstance(doc, list) else [doc]
        for item in items:
            if not isinstance(item, dict):
                continue

            _check_schema(item, fpath.name, errors["L1"])

            if "id" in item and isinstance(item["id"], str):
                declared_ids.add(item["id"])

            _collect_references(item, referenced_ids)

    undefined = referenced_ids - declared_ids
    for uid in sorted(undefined):
        errors["L2"].append(f"FK-UNDEFINED: '{uid}' is referenced but never declared")

    result: dict[str, Any] = {
        "errors": errors,
        "declared_count": len(declared_ids),
        "referenced_count": len(referenced_ids),
        "undefined_count": len(undefined),
        "model_files": list(model_files),
    }
    if declared_ids:
        result["declared_ids"] = sorted(declared_ids)
    if undefined:
        result["undefined_ids"] = sorted(undefined)
    return result


def _check_schema(item: dict, filename: str, errors: list[str]) -> None:
    """Check item-level schema requirements (L1)."""
    item_type = None
    if "id" not in item:
        errors.append(f"{filename}: missing 'id' field")
        return

    if "kind" in item:
        item_type = item["kind"]
    elif "family" in item:
        item_type = item["family"]
    elif "model" in item:
        item_type = item["model"]

    if item_type is None:
        return

    schema_checks = {
        "ServerFamily": ["tdp_w", "height_u", "psu_count"],
        "SwitchFamily": ["tdp_w", "height_u", "psu_count"],
        "RackFamily": ["total_u", "depth_mm", "width_mm"],
        "PDUFamily": ["max_power_watts"],
        "FiberFamily": ["from_port", "to_port"],
    }

    required = schema_checks.get(str(item_type), [])
    for field in required:
        if field not in item:
            errors.append(f"{filename}: {item_type} missing required field '{field}'")


def _collect_references(item: dict, refs: set) -> None:
    """Walk item dict and collect all referenced IDs."""
    for field in ("instance", "device_id", "rack_id", "pdu_id"):
        if field in item and isinstance(item[field], str):
            refs.add(item[field])

    for field in ("source", "target"):
        if field in item:
            val = item[field]
            if isinstance(val, str):
                refs.add(val)
            elif isinstance(val, dict) and "instance" in val:
                refs.add(val["instance"])

    for field in ("from_port", "to_port"):
        if field in item and isinstance(item[field], str):
            port_ref = item[field]
            if "/" in port_ref:
                dev_id = port_ref.split("/")[0]
                refs.add(dev_id)


def _layer_scores_from_static(score: TaskScore, static_result: dict[str, Any]) -> None:
    """Populate layer scores from static YAML check results."""
    errors = static_result.get("errors", {})
    for layer in LAYER_WEIGHTS:
        layer_errors = errors.get(layer, [])
        total = 1
        passed = 0 if layer_errors else 1
        score.layers[layer] = LayerScore(
            layer=layer,
            total=total,
            passed=passed,
            failed=total - passed,
            errors=list(layer_errors),
        )
        if passed and layer in LAYER_WEIGHTS:
            score.overall_score += LAYER_WEIGHTS[layer]


def _check_deliverable(project_dir: Path, deliverable_name: str) -> bool:
    """Check if a generator deliverable was produced successfully."""
    from sd_hwe_bench.critics.deliverable import DELIVERABLE_PATHS

    dist_root = _read_dist_root(project_dir)

    info = DELIVERABLE_PATHS.get(deliverable_name)
    if not info:
        return False

    config_key, filename, category = info

    toml_config = _read_piki_toml_targets(project_dir)
    if config_key in toml_config:
        cat = toml_config[config_key]
    else:
        cat = category

    target = dist_root / cat / filename
    if target.exists():
        return True

    if dist_root.exists():
        for f in dist_root.rglob(filename):
            return True

    return False


def _read_dist_root(project_dir: Path) -> Path:
    """Read dist root from piki.toml or return default 'dist'."""
    piki_toml = project_dir / "piki.toml"
    if piki_toml.exists():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        try:
            data = tomllib.loads(piki_toml.read_text())
            return project_dir / data.get("generators", {}).get("dist", {}).get("root", "dist")
        except Exception:
            pass
    return project_dir / "dist"


def _read_piki_toml_targets(project_dir: Path) -> dict[str, str]:
    """Read generator dist targets from piki.toml."""
    piki_toml = project_dir / "piki.toml"
    if not piki_toml.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    try:
        data = tomllib.loads(piki_toml.read_text())
        return data.get("generators", {}).get("dist", {}).get("targets", {})
    except Exception:
        return {}


# ── Main orchestrator ────────────────────────────────────────────────────

def score_task(
    task_id: str,
    agent_output_dir: Path,
    expected_deliverables: list[str] | None = None,
    rubric_sets: list[RubricSet] | None = None,
    requirement: str = "",
    rubrics_model: str | None = None,
    runner: SandboxRunner | None = None,
) -> TaskScore:
    """Score a single task attempt using the critic pipeline."""
    from sd_hwe_bench.task import TaskInstance

    score = TaskScore(task_id=task_id, success=False)
    project_dir = Path(agent_output_dir)

    # Ensure we have task metadata; if not, create a minimal TaskInstance stub
    try:
        task = TaskInstance(project_dir.parent)
    except Exception:
        # Fallback: build a minimal task from arguments
        import types
        task = types.SimpleNamespace(
            metadata=types.SimpleNamespace(
                expected_files=[],
                expected_deliverables=expected_deliverables or [],
                rubrics=rubric_sets or [],
                requirement=requirement,
            )
        )

    # 1. Syntax critic (L0)
    syntax = SyntaxCritic()
    syntax_res = syntax.evaluate(project_dir, task)  # type: ignore[arg-type]
    score.critic_results.append(syntax_res)
    score.layers["L0"] = LayerScore(
        layer="L0",
        total=1,
        passed=1 if syntax_res.passed else 0,
        failed=0 if syntax_res.passed else 1,
        errors=syntax_res.comments,
    )

    # 2. Piki critic (L1-L4)
    piki = PikiCritic(runner=runner)
    piki_res = piki.evaluate(project_dir, task)  # type: ignore[arg-type]
    score.critic_results.append(piki_res)

    layer_scores = piki_res.artifacts.get("layer_scores", {})
    layer_errors = piki_res.artifacts.get("layer_errors", {})
    for layer in ("L1", "L2", "L3", "L4"):
        score.layers[layer] = LayerScore(
            layer=layer,
            total=1,
            passed=1 if not layer_errors.get(layer) else 0,
            failed=0 if not layer_errors.get(layer) else 1,
            errors=layer_errors.get(layer, []),
        )
        score.overall_score += layer_scores.get(layer, 0.0)

    # If piki unavailable, fall back to static checks
    if not piki_res.available if hasattr(piki_res, "available") else False:  # noqa: SIM222
        static_result = _static_check_yaml(project_dir)
        _layer_scores_from_static(score, static_result)

    # 3. Deliverable critic (L5/L6)
    deliverable = DeliverableCritic()
    deliv_res = deliverable.evaluate(project_dir, task)  # type: ignore[arg-type]
    score.critic_results.append(deliv_res)

    if expected_deliverables:
        for d in expected_deliverables:
            score.deliverable_scores[d] = _check_deliverable(project_dir, d)
        delivered = sum(score.deliverable_scores.values())
        total = len(expected_deliverables)
        if total > 0:
            score.overall_score += DELIVERABLE_WEIGHT * (delivered / total)

    # 4. Rubric critic (optional)
    if rubric_sets:
        rubric = RubricCritic(model=rubrics_model)
        rubric_res = rubric.evaluate(project_dir, task)  # type: ignore[arg-type]
        score.critic_results.append(rubric_res)
        score.rubric_score = rubric_res.score
        score.rubric_results = rubric_res.comments

    # Determine success: all L0-L4 + deliverables must pass
    critical_layers = ["L0", "L1", "L2", "L3", "L4"]
    layers_ok = all(
        score.layers.get(layer) and score.layers[layer].passed for layer in critical_layers
    )
    deliverables_ok = all(score.deliverable_scores.values()) if expected_deliverables else True
    score.success = layers_ok and deliverables_ok

    return score


# ── Aggregate metrics ────────────────────────────────────────────────────

def compute_pass_at_k(scores: list[list[TaskScore]], k: int) -> float:
    """Compute Pass@k from per-attempt scores."""
    total = len(scores)
    if total == 0:
        return 0.0

    passed = 0
    for task_scores in scores:
        best_k = task_scores[:k]
        if any(s.success for s in best_k):
            passed += 1

    return passed / total


def compute_partial_credit(scores: list[TaskScore]) -> list[dict]:
    """Compute per-layer pass rates across all task attempts."""
    layer_stats: dict[str, dict] = {}
    for layer in LAYER_WEIGHTS:
        layer_stats[layer] = {"total": 0, "passed": 0}

    for score in scores:
        for layer, ls in score.layers.items():
            if layer not in layer_stats:
                continue
            layer_stats[layer]["total"] += ls.total
            layer_stats[layer]["passed"] += ls.passed

    return [
        {
            "layer": layer,
            "weight": LAYER_WEIGHTS[layer],
            "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0,
            "passed": stats["passed"],
            "total": stats["total"],
        }
        for layer, stats in layer_stats.items()
    ]
