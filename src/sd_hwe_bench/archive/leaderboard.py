"""Leaderboard builder from rollout archives."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sd_hwe_bench.archive.manager import ArchiveManager

logger = logging.getLogger(__name__)


@dataclass
class ModelResult:
    """Aggregated result for one model."""

    model: str
    total_tasks: int = 0
    passed_tasks: int = 0
    scores: list[float] = field(default_factory=list)
    task_ids: set[str] = field(default_factory=set)

    @property
    def pass_at_1(self) -> float:
        return self.passed_tasks / self.total_tasks if self.total_tasks > 0 else 0.0

    @property
    def avg_score(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "tasks": self.total_tasks,
            "pass_at_1": self.pass_at_1,
            "avg_score": self.avg_score,
            "task_ids": sorted(self.task_ids),
        }


@dataclass
class Leaderboard:
    """Leaderboard data structure."""

    models: list[ModelResult]
    generated_at: str

    def to_markdown(self) -> str:
        lines = [
            "# SD-HWE-Bench Leaderboard\n",
            f"_Generated at {self.generated_at}_\n",
            "| Model | Tasks | Pass@1 | Avg Score |",
            "|-------|-------|--------|-----------|",
        ]
        for model in sorted(self.models, key=lambda m: m.avg_score, reverse=True):
            lines.append(
                f"| {model.model} | {model.total_tasks} | {model.pass_at_1:.0%} | {model.avg_score:.0%} |"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "models": [m.to_dict() for m in self.models],
        }

    def save(self, json_path: Path, md_path: Path) -> None:
        json_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        md_path.write_text(self.to_markdown(), encoding="utf-8")


class LeaderboardBuilder:
    """Build a leaderboard from archived rollouts."""

    def __init__(self, manager: ArchiveManager):
        self.manager = manager

    def build(self) -> Leaderboard:
        from datetime import datetime, timezone

        by_model = self.manager.by_model()
        models: list[ModelResult] = []

        for model_id, entries in by_model.items():
            result = ModelResult(model=model_id)
            for entry in entries:
                result.total_tasks += 1
                result.scores.append(entry.overall_score)
                result.task_ids.add(entry.task_id)
                if entry.success:
                    result.passed_tasks += 1
            models.append(result)

        return Leaderboard(
            models=models,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
