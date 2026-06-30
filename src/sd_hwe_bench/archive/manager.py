"""Archive manager for rollout trajectories and results."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RunEntry:
    """A single rollout archive entry."""

    run_dir: Path
    manifest: dict[str, Any]

    @property
    def run_name(self) -> str:
        return self.run_dir.name

    @property
    def task_id(self) -> str:
        return self.manifest.get("task_id", "unknown")

    @property
    def actor(self) -> str:
        return self.manifest.get("actor", "unknown")

    @property
    def model(self) -> str | None:
        return self.manifest.get("model")

    @property
    def success(self) -> bool:
        return self.manifest.get("success", False)

    @property
    def overall_score(self) -> float:
        return self.manifest.get("overall_score", 0.0)


class ArchiveManager:
    """Manage rollout archive directories under a root."""

    def __init__(self, run_root: Path):
        self.run_root = Path(run_root)

    def list_runs(self) -> list[RunEntry]:
        """List all valid rollout archives."""
        entries: list[RunEntry] = []
        if not self.run_root.exists():
            return entries

        for manifest_path in sorted(self.run_root.rglob("manifest.json")):
            run_dir = manifest_path.parent
            if not (run_dir / "workspace").is_dir():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to read manifest %s: %s", manifest_path, exc)
                continue
            entries.append(RunEntry(run_dir=run_dir, manifest=manifest))

        return entries

    def summarize(self) -> list[dict[str, Any]]:
        """Return a JSON-serializable summary of all archives."""
        return [
            {
                "run_name": e.run_name,
                "task_id": e.task_id,
                "actor": e.actor,
                "model": e.model,
                "success": e.success,
                "overall_score": e.overall_score,
                "run_dir": str(e.run_dir),
            }
            for e in self.list_runs()
        ]

    def by_model(self) -> dict[str, list[RunEntry]]:
        """Group run entries by model identifier."""
        groups: dict[str, list[RunEntry]] = {}
        for entry in self.list_runs():
            model_id = entry.model or entry.actor
            groups.setdefault(model_id, []).append(entry)
        return groups

    def by_task(self) -> dict[str, list[RunEntry]]:
        """Group run entries by task ID."""
        groups: dict[str, list[RunEntry]] = {}
        for entry in self.list_runs():
            groups.setdefault(entry.task_id, []).append(entry)
        return groups
