"""Base Critic interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sd_hwe_bench.task import TaskInstance


@dataclass
class CriticResult:
    """Result of a critic evaluation."""

    name: str
    passed: bool
    score: float = 0.0
    comments: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)


class Critic:
    """Base class for critics."""

    name: str = "base"

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        """Evaluate the workspace output for the given task."""
        raise NotImplementedError
