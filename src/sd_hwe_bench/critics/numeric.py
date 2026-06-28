"""Numeric critic — validates computed values in reports against expected with tolerance."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.task import TaskInstance

logger = logging.getLogger(__name__)


class NumericCritic(Critic):
    """Verifies numeric values in YAML output files against expected values.

    Reads numeric_assertions from TaskMetadata and performs tolerance-based
    comparison. Works on any YAML file in the agent's workspace.
    """

    name = "numeric"

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        assertions = task.metadata.numeric_assertions
        if not assertions:
            return CriticResult(
                name=self.name,
                passed=True,
                score=1.0,
                comments=["Numeric layer: no assertions defined — skipped."],
            )

        passed_count = 0
        total_weight = 0.0
        weighted_passed = 0.0
        comments: list[str] = []

        for a in assertions:
            total_weight += a.weight
            file_path = workspace_root / a.file
            if not file_path.exists():
                comments.append(f"✗ {a.file}: file not found")
                continue

            try:
                raw = yaml.safe_load(file_path.read_text())
            except yaml.YAMLError as exc:
                comments.append(f"✗ {a.file}: YAML parse error — {exc}")
                continue

            actual = self._resolve_path(raw, a.yaml_path)
            if actual is None:
                comments.append(
                    f"✗ {a.file} → {a.yaml_path}: path not found in YAML"
                )
                continue

            if not isinstance(actual, (int, float)):
                comments.append(
                    f"✗ {a.file} → {a.yaml_path}: value is {type(actual).__name__}, expected numeric"
                )
                continue

            delta = abs(float(actual) - a.expected)
            max_delta = abs(a.expected) * a.tolerance
            if delta <= max_delta or (a.expected == 0 and delta == 0):
                passed_count += 1
                weighted_passed += a.weight
                comments.append(
                    f"✓ {a.file} → {a.yaml_path}: {actual} ≈ {a.expected} (Δ={delta:.4g}, tol={a.tolerance*100:.1f}%)"
                )
            else:
                comments.append(
                    f"✗ {a.file} → {a.yaml_path}: {actual} ≠ {a.expected} (Δ={delta:.4g}, tol={a.tolerance*100:.1f}%)"
                )

        if total_weight == 0:
            return CriticResult(name=self.name, passed=True, score=1.0, comments=comments)

        score = weighted_passed / total_weight
        passed = passed_count == len(assertions)
        return CriticResult(
            name=self.name,
            passed=passed,
            score=score,
            comments=comments,
        )

    @staticmethod
    def _resolve_path(data: dict, path: str):
        """Resolve a dot-separated path in a nested dict/list structure.

        Supports integer indices for list access: 'sectors.0.coverage_radius_km'.
        """
        parts = re.split(r"\.", path)
        current: object = data
        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if idx < 0 or idx >= len(current):  # pyright: ignore[reportUnknownArgumentType]
                        return None
                    current = current[idx]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current
