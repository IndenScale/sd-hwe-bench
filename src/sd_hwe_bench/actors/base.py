"""Base Actor interface."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sd_hwe_bench.settings import settings


def to_text(stream: bytes | str | None) -> str:
    """Coerce a subprocess stream to ``str``.

    ``subprocess.TimeoutExpired.stdout``/``.stderr`` may be ``bytes`` even when
    the process was started with ``text=True``, so concatenating them into a
    transcript string can raise ``TypeError``.  This helper makes that path safe
    by decoding ``bytes`` (replacing undecodable runs) and mapping ``None`` to
    the empty string.
    """
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", "replace")
    return stream


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


def snapshot_yaml_files(root: Path) -> dict[Path, str]:
    """Return content hashes for YAML files under root, keyed by relative path."""
    snapshot: dict[Path, str] = {}
    for rel in list_yaml_files(root):
        path = root / rel
        snapshot[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def count_changed_yaml_files(before: dict[Path, str], root: Path) -> int:
    """Count added, modified, and deleted YAML files relative to a snapshot."""
    after = snapshot_yaml_files(root)
    changed = 0
    for rel, digest in after.items():
        if before.get(rel) != digest:
            changed += 1
    for rel in before:
        if rel not in after:
            changed += 1
    return changed
