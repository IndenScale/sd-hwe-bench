"""Piki critic: L1-L4 rule checks via piki engine."""

from __future__ import annotations

import logging
from pathlib import Path

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.sandbox.runner import SandboxRunner
from sd_hwe_bench.settings import settings
from sd_hwe_bench.task import TaskInstance

logger = logging.getLogger(__name__)

# Load rule->layer mapping from bundled YAML config. Re-export the derived
# dicts so existing imports keep working.
_rule_layers_config = settings.RULE_LAYERS_CONFIG
PIKI_RULE_LAYERS: dict[str, str] = dict(_rule_layers_config.get("exact", {}))
PIKI_RULE_PREFIXES: list[tuple[str, str]] = [
    (entry["prefix"], entry["layer"]) for entry in _rule_layers_config.get("prefixes", [])
]

# Use the shared layer weights from scorer/settings.
LAYER_WEIGHTS = settings.LAYER_WEIGHTS


def _layer_for_rule(rule_id: str) -> str:
    """Map a piki rule ID to a scoring layer (L1-L4).

    First tries an exact match, then falls back to known prefixes.  Unknown
    rules default to L2 so the failure is visible, but a warning is logged.
    """
    if rule_id in PIKI_RULE_LAYERS:
        return PIKI_RULE_LAYERS[rule_id]
    for prefix, layer in PIKI_RULE_PREFIXES:
        if rule_id.startswith(prefix):
            return layer
    logger.warning("Unknown piki rule ID %r; defaulting to L2", rule_id)
    return "L2"


class PikiCritic(Critic):
    """Run piki check and map failures to L1-L4 layers."""

    name = "piki"

    def __init__(self, runner: SandboxRunner | None = None):
        self.runner = runner or SandboxRunner()

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        project_dir = workspace_root
        result = self.runner.check(project_dir)

        if not result.available:
            return CriticResult(
                name=self.name,
                passed=False,
                score=0.0,
                comments=["piki engine not available"],
                artifacts={
                    "available": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        parsed = result.parsed or {}
        layer_errors: dict[str, list[str]] = {"L1": [], "L2a": [], "L2b": [], "L2c": [], "L3": [], "L4": []}

        for rule_result in parsed.get("results", []):
            if rule_result.get("passed"):
                continue
            rule_id = rule_result.get("rule_id", "")
            layer = _layer_for_rule(rule_id)
            layer_errors[layer].append(f"{rule_id}: {rule_result.get('message', 'failed')}")

        for diag in parsed.get("diagnostics", []):
            severity = str(diag.get("severity", "")).upper()
            if severity not in ("ERROR", "FATAL"):
                continue
            code = diag.get("code", "")
            layer = _layer_for_rule(code)
            layer_errors[layer].append(f"{code}: {diag.get('message', 'failed')}")

        layer_scores: dict[str, float] = {}
        comments: list[str] = []
        for layer in ("L1", "L2a", "L2b", "L2c", "L3", "L4"):
            errors = layer_errors[layer]
            passed = not errors
            layer_scores[layer] = LAYER_WEIGHTS[layer] if passed else 0.0
            status = "passed" if passed else f"failed ({len(errors)} errors)"
            comments.append(f"{layer}: {status}")
            max_errors = settings.PIKI_CRITIC_MAX_ERRORS
            for err in errors[:max_errors]:
                comments.append(f"  - {err}")
            if len(errors) > max_errors:
                comments.append(f"  ... and {len(errors) - max_errors} more")

        score = sum(layer_scores.values())
        passed = all(layer_errors[layer] == [] for layer in ("L1", "L2a", "L2b", "L2c", "L3", "L4"))

        return CriticResult(
            name=self.name,
            passed=passed,
            score=score,
            comments=comments,
            artifacts={
                "layer_scores": layer_scores,
                "layer_errors": layer_errors,
                "parsed": parsed,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
