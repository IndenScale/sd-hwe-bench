"""Shared CLI helpers used by multiple commands."""

from __future__ import annotations

import logging
from typing import Optional

from sd_hwe_bench.dataset import Dataset


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

    matched = [tid for tid in all_ids if tid == task_id or tid.startswith(task_id)]
    if not matched:
        for tid in all_ids:
            task = dataset.load_task(tid)
            if task_id in task.metadata.name:
                matched.append(tid)
    return matched if matched else [task_id]
