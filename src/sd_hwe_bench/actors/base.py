"""Base Actor interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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

    def __init__(self, model: str | None = None, timeout: int = 600):
        self.model = model
        self.timeout = timeout

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        """Run the actor in the given workspace directory.

        The actor should write YAML/design files into workspace_root.
        """
        raise NotImplementedError
