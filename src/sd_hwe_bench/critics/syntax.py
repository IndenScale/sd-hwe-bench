"""Syntax critic: YAML parse checks and expected file existence."""

from __future__ import annotations

from pathlib import Path

import yaml

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.task import TaskInstance


class SyntaxCritic(Critic):
    """Check L0: YAML validity and presence of expected files."""

    name = "syntax"

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        project_dir = workspace_root
        comments: list[str] = []

        yaml_files = sorted(project_dir.rglob("*.yaml")) + sorted(project_dir.rglob("*.yml"))
        instance_files = [
            f for f in yaml_files
            if "models/" not in str(f.relative_to(project_dir)) and f.name != "piki.toml"
        ]

        if not instance_files:
            return CriticResult(
                name=self.name,
                passed=False,
                score=0.0,
                comments=["L0 failed: no YAML instance files found in workspace"],
            )

        parse_errors = 0
        for fpath in instance_files:
            try:
                yaml.safe_load(fpath.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                parse_errors += 1
                comments.append(f"L0 YAML parse error in {fpath.relative_to(project_dir)}: {exc}")

        missing_expected: list[str] = []
        for expected in task.metadata.expected_files:
            if not (project_dir / expected).exists():
                missing_expected.append(expected)

        if missing_expected:
            comments.append(f"Missing expected files: {', '.join(missing_expected)}")

        # L0 fails only on YAML parse errors or empty project, not on missing expected files.
        passed = parse_errors == 0
        score = 1.0
        score -= 0.1 * parse_errors
        score = max(0.0, score)

        if passed:
            comments.insert(0, f"L0 passed: {len(instance_files)} YAML files valid")

        return CriticResult(
            name=self.name,
            passed=passed,
            score=score,
            comments=comments,
        )
