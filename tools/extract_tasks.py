#!/usr/bin/env python3
"""Extract SD-HWE-Bench tasks from a canonical ADL project git history.

This tool implements ADR 0003: each task corresponds to the state transition
between two adjacent commits in a canonical project. The scaffold is commit k,
the reference solution is commit k+1, and the requirement is taken from the
project's task_manifest.yaml.

Usage:
    python tools/extract_tasks.py \
        --project-dir canonical/telecom-rack \
        --output-dir tasks/telecom

The tool will:
1. Read canonical/<project>/task_manifest.yaml.
2. For each adjacent commit pair (k, k+1) defined in the manifest:
   - Export commit k files to <output-dir>/<task-id>/scaffold/.
   - Export commit k+1 files to <output-dir>/<task-id>/solution/.
   - Generate <output-dir>/<task-id>/task.yaml.
3. Optionally run `piki check` on each reference solution.
4. Print a summary report.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Files and directories that should never be copied into scaffold/solution.
EXCLUDED_PATTERNS = {
    ".git",
    ".DS_Store",
    ".gitignore",
    "dist",
    "__pycache__",
    "*.pyc",
    "*.pyo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract benchmark tasks from a canonical project git history."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Path to the canonical project directory (must be a git repo with task_manifest.yaml).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where extracted tasks will be written (e.g. tasks/telecom).",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="task_manifest.yaml",
        help="Name of the manifest file inside the project directory (default: task_manifest.yaml).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run `piki check` on each reference solution after extraction.",
    )
    parser.add_argument(
        "--piki-python",
        type=str,
        default=None,
        help="Python interpreter to use for `piki check` (default: auto-detect).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def load_manifest(project_dir: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = project_dir / manifest_name
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_excluded(rel_path: str) -> bool:
    """Return True if a relative path should be excluded from scaffold/solution."""
    parts = Path(rel_path).parts
    for part in parts:
        if part in EXCLUDED_PATTERNS:
            return True
        if any(part.endswith(ext.lstrip("*")) for ext in EXCLUDED_PATTERNS if ext.startswith("*")):
            return True
    return False


def git_archive(project_dir: Path, ref: str, dest_dir: Path) -> None:
    """Export the file tree of ``ref`` into ``dest_dir`` using git archive."""
    result = subprocess.run(
        ["git", "archive", "--format=tar", ref],
        cwd=project_dir,
        capture_output=True,
        check=True,
    )
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as tar:
        for member in tar.getmembers():
            if is_excluded(member.name):
                continue
            tar.extract(member, path=dest_dir, filter="data")


def resolve_ref(project_dir: Path, commit_name: str) -> str:
    """Resolve a manifest commit name to an actual git ref (tag or hash)."""
    # Prefer an annotated or lightweight tag named after the commit.
    for prefix in ("", "refs/tags/"):
        ref = f"{prefix}{commit_name}"
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    raise ValueError(
        f"Could not resolve commit '{commit_name}' to a git ref in {project_dir}"
    )


def find_piki_python(piki_python: str | None) -> str:
    """Find a Python interpreter that can run piki."""
    if piki_python:
        return piki_python
    # Current interpreter if piki is importable.
    try:
        import piki  # noqa: F401
        return sys.executable
    except ImportError:
        pass
    # Legacy monorepo fallback.
    fallback = "/Users/indenscale/workspace/piki/.venv/bin/python"
    if Path(fallback).exists():
        return fallback
    # Try PATH.
    python = shutil.which("python3") or shutil.which("python")
    if python:
        return python
    raise RuntimeError("Could not find a Python interpreter with piki installed.")


def validate_solution(solution_dir: Path, piki_python: str) -> tuple[bool, str]:
    """Run `piki check` on a solution directory and return (passed, output)."""
    result = subprocess.run(
        [piki_python, "-m", "piki", "check", "--format", "json"],
        cwd=solution_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    stdout = result.stdout.strip()
    try:
        parsed = yaml.safe_load(stdout)
        passed = bool(parsed.get("passed", False)) and result.returncode == 0
    except Exception:
        passed = result.returncode == 0
    return passed, stdout + (f"\n{result.stderr}" if result.stderr else "")


def generate_task_id(domain: str, project: str, step: int) -> str:
    """Generate a stable task ID from domain, project, and step number."""
    short_project = project.replace("canonical-", "")
    return f"{domain}/{short_project}-{step:03d}"


def build_task_yaml(
    manifest: dict[str, Any],
    from_commit: dict[str, Any],
    to_commit: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
    """Compose the task.yaml content for one task."""
    domain = manifest.get("domain", "unknown")
    return {
        "task_id": task_id,
        "name": to_commit.get("summary", f"Step {to_commit.get('step', 0)}"),
        "description": f"Canonical task extracted from {manifest['project']} commit {from_commit['commit']} → {to_commit['commit']}",
        "domain": domain,
        "source_project": manifest["project"],
        "source_commit_from": from_commit["commit"],
        "source_commit_to": to_commit["commit"],
        "task_type": to_commit.get("task_type", "comprehensive"),
        "difficulty": to_commit.get("difficulty", "medium"),
        "requirement": to_commit.get("requirement", "").strip(),
        "plugins": [domain],
        "expected_files": to_commit.get("expected_files", []),
        "scoring_layers": ["L0", "L1", "L2", "L3", "L4"],
        "expected_deliverables": to_commit.get("expected_deliverables", []),
        "rubrics": [],
    }


def extract_task(
    project_dir: Path,
    output_dir: Path,
    manifest: dict[str, Any],
    from_commit: dict[str, Any],
    to_commit: dict[str, Any],
    dry_run: bool,
) -> Path:
    """Extract a single task and return the task directory path."""
    task_id = generate_task_id(
        manifest.get("domain", "unknown"),
        manifest["project"],
        to_commit.get("step", 0),
    )
    task_dir = output_dir / task_id

    if dry_run:
        logger.info("[dry-run] Would create %s", task_dir)
        return task_dir

    if task_dir.exists():
        logger.warning("Removing existing task directory: %s", task_dir)
        shutil.rmtree(task_dir)

    scaffold_dir = task_dir / "scaffold"
    solution_dir = task_dir / "solution"

    git_archive(project_dir, resolve_ref(project_dir, from_commit["commit"]), scaffold_dir)
    git_archive(project_dir, resolve_ref(project_dir, to_commit["commit"]), solution_dir)

    task_yaml = build_task_yaml(manifest, from_commit, to_commit, task_id)
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(task_yaml, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    logger.info("Extracted %s", task_id)
    return task_dir


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    project_dir = args.project_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not project_dir.is_dir():
        logger.error("Project directory does not exist: %s", project_dir)
        return 1

    # Verify the project is a git repository.
    git_dir = project_dir / ".git"
    if not (git_dir.is_dir() or git_dir.is_file()):
        logger.error(
            "%s is not a git repository. Initialize it first with `git init`.", project_dir
        )
        return 1

    manifest = load_manifest(project_dir, args.manifest)
    commits = manifest.get("commit_history", [])

    if len(commits) < 2:
        logger.error("Manifest must contain at least two commits to extract tasks.")
        return 1

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    piki_python = None
    if args.validate:
        piki_python = find_piki_python(args.piki_python)
        logger.info("Using piki interpreter: %s", piki_python)

    stats = {"extracted": 0, "validated": 0, "failed_validation": 0}

    for i in range(len(commits) - 1):
        from_commit = commits[i]
        to_commit = commits[i + 1]

        if to_commit.get("is_scaffold_only", False):
            logger.debug("Skipping scaffold-only commit: %s", to_commit.get("commit"))
            continue

        task_dir = extract_task(
            project_dir, output_dir, manifest, from_commit, to_commit, args.dry_run
        )
        stats["extracted"] += 1

        if args.validate and not args.dry_run:
            passed, output = validate_solution(task_dir / "solution", piki_python)
            if passed:
                logger.info("  ✓ %s solution passes piki check", task_dir.name)
                stats["validated"] += 1
            else:
                logger.error("  ✗ %s solution failed piki check", task_dir.name)
                if args.verbose:
                    logger.error(output)
                stats["failed_validation"] += 1

    logger.info("-" * 50)
    logger.info("Extraction complete: %d tasks extracted", stats["extracted"])
    if args.validate:
        logger.info(
            "Validation: %d passed, %d failed",
            stats["validated"],
            stats["failed_validation"],
        )
    logger.info("Output directory: %s", output_dir)

    return 1 if stats["failed_validation"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
