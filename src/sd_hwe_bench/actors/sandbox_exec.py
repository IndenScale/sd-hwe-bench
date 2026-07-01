"""macOS seatbelt (``sandbox-exec``) hardening for actor subprocesses.

Wrapping an actor command with ``sandbox-exec`` lets the kernel deny *all*
filesystem reads of the benchmark repository (``tasks/**/solution``,
``tasks/**/expected``, ``canonical/``, ``runs/``, ``leaderboard/``).  Combined
with an out-of-repo isolated workspace (see ``sandbox.workspace``), this stops
an agent from reading reference solutions through ``Bash`` (``cat``/``find``),
not only through guarded ``Read`` tools.

The profile is intentionally minimal — ``(allow default)`` keeps the actor
fully functional (network, process spawning, writes to its workspace and config
dirs) and only ``deny file-read*`` on the repo subtree is added.  Because the
isolated workspace lives outside the repo and the scaffold is copied in, the
actor needs nothing from the repo at runtime, so a blanket repo read-deny is
safe.

Seatbelt is macOS-only (and marked deprecated by Apple, though still
functional).  On other platforms, or when ``sandbox-exec`` is missing, wrapping
is skipped and a warning is logged so a run is never *silently* unprotected.
"""

from __future__ import annotations

import logging
import platform
import shutil
from pathlib import Path

import sd_hwe_bench

logger = logging.getLogger(__name__)


def repo_root() -> Path:
    """Return the benchmark repo root, derived from the installed package path.

    ``src/sd_hwe_bench/sandbox_exec.py`` → ``parents[2]`` is the repo root in the
    editable ``src`` layout.  This is independent of the actor workspace
    location, so it still points at the answer-bearing tree after the workspace
    is relocated out of the repo.
    """
    return Path(sd_hwe_bench.__file__).resolve().parents[2]


def _seatbelt_available() -> bool:
    return platform.system() == "Darwin" and shutil.which("sandbox-exec") is not None


def resolve_mode(mode: str | None) -> str:
    """Resolve an ``auto|seatbelt|none`` request to a concrete ``seatbelt|none``.

    ``auto``      → ``seatbelt`` when available, else ``none``.
    ``seatbelt``  → ``seatbelt`` when available, else ``none`` (with a warning).
    ``none``      → ``none``.
    """
    normalized = (mode or "auto").lower()
    if normalized == "none":
        return "none"
    if normalized == "seatbelt":
        if _seatbelt_available():
            return "seatbelt"
        logger.warning(
            "actor-sandbox=seatbelt requested but sandbox-exec is unavailable "
            "(non-macOS or not installed); running WITHOUT kernel-level isolation."
        )
        return "none"
    # auto (or any unrecognized value treated as auto)
    return "seatbelt" if _seatbelt_available() else "none"


def build_profile(deny_paths: list[Path]) -> str:
    """Build a seatbelt profile that allows everything but reads of ``deny_paths``."""
    subpaths = " ".join(f'(subpath "{p}")' for p in deny_paths)
    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            f"(deny file-read* {subpaths})",
        ]
    )


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def maybe_wrap(
    cmd: list[str],
    workspace_root: Path,
    mode: str | None = None,
    extra_deny: list[Path] | None = None,
) -> list[str]:
    """Return ``cmd`` wrapped with ``sandbox-exec`` when seatbelt isolation applies.

    Returns ``cmd`` unchanged when the resolved mode is ``none``, or when the
    actor's ``workspace_root`` sits *inside* the repo (denying repo reads would
    block the actor reading its own scaffold) — in that case a warning points at
    enabling actor isolation for an out-of-repo workspace.
    """
    resolved = resolve_mode(mode)
    if resolved != "seatbelt":
        return cmd

    root = repo_root()
    ws = Path(workspace_root).resolve()
    if _is_relative_to(ws, root):
        logger.warning(
            "actor-sandbox: workspace %s is inside repo %s; skipping seatbelt "
            "deny to avoid blocking scaffold reads. Enable actor isolation "
            "(out-of-repo workspace) for hard isolation.",
            ws,
            root,
        )
        return cmd

    deny = [root]
    if extra_deny:
        deny.extend(Path(p).resolve() for p in extra_deny)
    profile = build_profile(deny)
    return ["sandbox-exec", "-p", profile, *cmd]
