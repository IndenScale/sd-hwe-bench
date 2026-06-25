"""Base Actor interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sd_hwe_bench.settings import settings


@dataclass
class ActorResult:
    """Result of an actor run."""

    success: bool
    raw_output: str
    files_written: int
    elapsed_s: float
    error: str | None = None


class Actor:
    """Base class for agent actors."""

    name: str = "base"

    def __init__(self, model: str | None = None, timeout: int | None = None):
        self.model = model
        self.timeout = timeout if timeout is not None else settings.DEFAULT_ACTOR_TIMEOUT_S

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        """Run the actor in the given workspace directory.

        The actor should write YAML/design files into workspace_root.
        """
        raise NotImplementedError


def list_yaml_files(root: Path) -> set[Path]:
    """Return the set of YAML files under root, relative to root."""
    return {
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file() and p.suffix in (".yaml", ".yml")
    }
