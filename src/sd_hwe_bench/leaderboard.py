"""Leaderboard management — store, query, and format benchmark results."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class LeaderboardEntry:
    """A single entry in the leaderboard."""

    submission_id: str
    model_name: str
    organization: str
    date: str
    pass_at_1: float
    pass_at_3: float
    total_tasks: int
    avg_score: float
    layer_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class Leaderboard:
    """In-memory leaderboard backed by a JSON file."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path("leaderboard/results.json")
        self._entries: list[LeaderboardEntry] = []
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self.path.read_text())
        self._entries = [
            LeaderboardEntry(**entry) for entry in data.get("entries", [])
        ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated": datetime.now(timezone.utc).isoformat(),
            "entries": [
                {
                    "submission_id": e.submission_id,
                    "model_name": e.model_name,
                    "organization": e.organization,
                    "date": e.date,
                    "pass_at_1": e.pass_at_1,
                    "pass_at_3": e.pass_at_3,
                    "total_tasks": e.total_tasks,
                    "avg_score": e.avg_score,
                    "layer_scores": e.layer_scores,
                    "metadata": e.metadata,
                }
                for e in self._entries
            ],
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def submit(self, entry: LeaderboardEntry) -> None:
        existing = [e for e in self._entries if e.submission_id == entry.submission_id]
        for e in existing:
            self._entries.remove(e)
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.pass_at_1, reverse=True)
        self.save()

    def top(self, n: int = 10) -> list[LeaderboardEntry]:
        return self._entries[:n]

    def render_markdown(self) -> str:
        lines = [
            "# SD-HWE-Bench Leaderboard\n",
            f"*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n",
            "| Rank | Model | Organization | Pass@1 | Pass@3 | Avg Score | Date |",
            "|------|-------|-------------|--------|--------|-----------|------|",
        ]
        for i, e in enumerate(self._entries[:20], 1):
            lines.append(
                f"| {i} | {e.model_name} | {e.organization} | "
                f"{e.pass_at_1:.1%} | {e.pass_at_3:.1%} | "
                f"{e.avg_score:.2%} | {e.date} |"
            )
        return "\n".join(lines)
