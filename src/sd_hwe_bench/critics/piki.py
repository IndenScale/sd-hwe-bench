"""Piki critic: L1-L4 rule checks via piki engine."""

from __future__ import annotations

from pathlib import Path

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.sandbox.runner import SandboxRunner
from sd_hwe_bench.task import TaskInstance

# Map piki rule IDs to scoring layers
PIKI_RULE_LAYERS: dict[str, str] = {
    "SCHEMA-001": "L1",
    "TELECOM-POWER-001": "L3",
    "TELECOM-POWER-002": "L3",
    "CATALOG-LIFECYCLE-001": "L3",
    "TELECOM-RACK-001": "L4",
    "TELECOM-RACK-002": "L4",
    "TELECOM-RACK-003": "L4",
    "TELECOM-COLLISION-001": "L4",
    "REFS-001": "L2",
    "REFS-002": "L2",
    "FK-001": "L2",
    "TAGS-001": "L2",
    "INTERFACE-COMPAT-001": "L2",
    "INTERFACE-CABLE-001": "L2",
    "MATE-001": "L2",
    "MATE-002": "L2",
    "MATE-003": "L2",
    "CATALOG-001": "L2",
    "CATALOG-002": "L2",
    "TELECOM-FK-001": "L2",
    "TELECOM-PORT-001": "L2",
    "TELECOM-PORT-002": "L2",
    "TELECOM-CONN-001": "L2",
    "TELECOM-CONN-002": "L2",
    "TELECOM-CONN-003": "L2",
}

LAYER_WEIGHTS = {
    "L1": 0.10,
    "L2": 0.15,
    "L3": 0.40,
    "L4": 0.20,
}


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
                artifacts={"stdout": result.stdout, "stderr": result.stderr},
            )

        parsed = result.parsed or {}
        layer_errors: dict[str, list[str]] = {"L1": [], "L2": [], "L3": [], "L4": []}

        for rule_result in parsed.get("results", []):
            if rule_result.get("passed"):
                continue
            rule_id = rule_result.get("rule_id", "")
            layer = PIKI_RULE_LAYERS.get(rule_id, "L2")
            layer_errors[layer].append(
                f"{rule_id}: {rule_result.get('message', 'failed')}"
            )

        for diag in parsed.get("diagnostics", []):
            severity = str(diag.get("severity", "")).upper()
            if severity not in ("ERROR", "FATAL"):
                continue
            code = diag.get("code", "")
            layer = PIKI_RULE_LAYERS.get(code, "L2")
            layer_errors[layer].append(
                f"{code}: {diag.get('message', 'failed')}"
            )

        layer_scores: dict[str, float] = {}
        comments: list[str] = []
        for layer in ("L1", "L2", "L3", "L4"):
            errors = layer_errors[layer]
            passed = not errors
            layer_scores[layer] = LAYER_WEIGHTS[layer] if passed else 0.0
            status = "passed" if passed else f"failed ({len(errors)} errors)"
            comments.append(f"{layer}: {status}")
            for err in errors[:5]:
                comments.append(f"  - {err}")
            if len(errors) > 5:
                comments.append(f"  ... and {len(errors) - 5} more")

        score = sum(layer_scores.values())
        passed = all(layer_errors[layer] == [] for layer in ("L1", "L2", "L3", "L4"))

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
