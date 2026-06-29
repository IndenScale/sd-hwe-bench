"""Batch-run a model × task matrix of rollouts, then aggregate a leaderboard.

Replaces the per-experiment ``scripts/*_batch.py`` wrappers (which hardcoded an
absolute repo path, a task list, a model map, and a brittle stdout parser) with
a single matrix-driven command that reuses the tested ``run`` command and the
existing leaderboard aggregation.

Matrix YAML schema::

    run_dir: runs/pass5-2026xxxx     # archive root (shared across models)
    passes: 5                        # passes per (model, task)
    sandbox: none                    # auto/none/docker/podman
    timeout: 600                     # actor timeout (s)
    max_workers: 4                   # concurrent (model, task) rollouts
    models:                          # name -> actor spec
      kimi: kimi
      deepseek-v4-pro: codex:deepseek-v4-pro
    tasks:                           # ids / prefixes / globs, expanded via dataset
      - telecom/aidc-*
      - telecom/comprehensive-001
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import typer
import yaml

from sd_hwe_bench.archive.leaderboard import LeaderboardBuilder
from sd_hwe_bench.archive.manager import ArchiveManager
from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.settings import settings


def load_matrix(path: Path) -> dict[str, Any]:
    """Load and validate a batch matrix file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("matrix file must be a YAML mapping")
    if not data.get("models"):
        raise ValueError("matrix must define a non-empty 'models' map")
    if not data.get("tasks"):
        raise ValueError("matrix must define a non-empty 'tasks' list")
    return data


def expand_tasks(ds: Dataset, entries: list[str]) -> list[str]:
    """Expand task entries (ids / prefixes / globs) to a de-duplicated id list."""
    all_ids = ds.discover()
    resolved: list[str] = []
    for entry in entries:
        if any(ch in entry for ch in "*?["):
            matched = [tid for tid in all_ids if fnmatch.fnmatch(tid, entry)]
        else:
            matched = resolve_task_ids(ds, entry)
        for tid in matched:
            if tid not in resolved:
                resolved.append(tid)
    return resolved


def register(app: typer.Typer) -> None:
    @app.command("batch")
    def batch_command(
        matrix: Path = typer.Option(..., "--matrix", help="Path to batch matrix YAML."),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        dry_run: bool = typer.Option(
            False, "--dry-run", help="Print the (model, task) plan and exit; do not run actors."
        ),
        max_workers: int = typer.Option(
            settings.MAX_AUTO_JOBS, "--max-workers", help="Concurrent (model, task) rollouts."
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Run a model × task matrix of rollouts, then build a leaderboard."""
        setup_logging(verbose)

        data = load_matrix(matrix)
        models: dict[str, str] = dict(data["models"])
        ds = Dataset(dataset)
        task_ids = expand_tasks(ds, list(data["tasks"]))
        if not task_ids:
            console.print("[red]No tasks matched the matrix 'tasks' patterns.[/red]")
            raise typer.Exit(code=1)

        passes = int(data.get("passes", settings.DEFAULT_PASSES))
        sandbox = str(data.get("sandbox", settings.DEFAULT_SANDBOX_BACKEND))
        timeout = int(data.get("timeout", settings.DEFAULT_ACTOR_TIMEOUT_S))
        run_dir = str(data.get("run_dir", settings.RUN_DIR))
        workers = int(data.get("max_workers", max_workers))

        plan = [(name, spec, tid) for name, spec in models.items() for tid in task_ids]

        console.print(
            f"[bold]Batch plan:[/bold] {len(models)} models × {len(task_ids)} tasks "
            f"= {len(plan)} rollouts | passes={passes} | sandbox={sandbox} | run_dir={run_dir}"
        )
        for name, spec, tid in plan:
            console.print(f"  - {name} ({spec})  {tid}")

        if dry_run:
            return

        def _one(model_name: str, actor_spec: str, task_id: str) -> tuple[str, str, int]:
            cmd = [
                sys.executable, "-m", "sd_hwe_bench.cli", "run", task_id,
                "--actor", actor_spec,
                "--passes", str(passes),
                "--run-dir", run_dir,
                "--sandbox", sandbox,
                "--timeout", str(timeout),
                "--dataset", str(dataset),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return model_name, task_id, proc.returncode

        failures = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_one, n, s, t): (n, t) for (n, s, t) in plan}
            for fut in as_completed(futures):
                name, tid, rc = fut.result()
                ok = rc == 0
                if not ok:
                    failures += 1
                color = "green" if ok else "red"
                console.print(f"  [{color}]{'ok' if ok else 'FAIL'}[/{color}] {name} {tid} (rc={rc})")

        # Aggregate leaderboard from the shared run_dir manifests.
        manager = ArchiveManager(Path(run_dir))
        board = LeaderboardBuilder(manager).build()
        console.print(board.to_markdown())

        if failures:
            console.print(f"[yellow]{failures}/{len(plan)} rollouts returned non-zero.[/yellow]")
            raise typer.Exit(code=1)
