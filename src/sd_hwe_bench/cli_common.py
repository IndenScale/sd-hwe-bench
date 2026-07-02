"""Shared CLI helpers used by multiple commands."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sd_hwe_bench.dataset import Dataset


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse a single KEY=VALUE line, skipping comments and blanks."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def load_env_file(path: Path) -> dict[str, str]:
    """Load environment variables from a ``KEY=VALUE`` file.

    Supports simple ``.env`` style files:
    - Blank lines and ``#`` comments are ignored.
    - Values may be quoted with ``"`` or ``'``.
    """
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        pair = _parse_env_line(line)
        if pair:
            env[pair[0]] = pair[1]
    return env


def build_env_vars(
    env_options: list[str] | None = None,
    env_file: Path | None = None,
) -> dict[str, str]:
    """Build a merged env dict from ``--env`` options and an ``--env-file``.

    ``--env`` values take precedence over the file.
    """
    env: dict[str, str] = {}
    if env_file:
        env.update(load_env_file(env_file))
    if env_options:
        for item in env_options:
            pair = _parse_env_line(item)
            if pair is None:
                raise ValueError(f"Invalid --env value: {item!r}")
            env[pair[0]] = pair[1]
    return env


def setup_logging(verbose: bool) -> None:
    """Configure root logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def resolve_task_ids(dataset: Dataset, task_id: Optional[str]) -> list[str]:
    """Resolve a task ID, prefix, or name substring to a list of task IDs."""
    all_ids = dataset.discover()
    if not task_id:
        return all_ids

    matched = [
        tid
        for tid in all_ids
        if tid == task_id or tid.startswith(task_id) or tid.split("/", 1)[-1].startswith(task_id)
    ]
    if not matched:
        for tid in all_ids:
            task = dataset.load_task(tid)
            if task_id in task.metadata.name:
                matched.append(tid)
    return matched if matched else [task_id]
