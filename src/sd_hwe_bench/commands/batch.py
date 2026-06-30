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
    self_check: false                # append --no-self-check when false
    command: run                     # run or run-repair
    context_mode: full               # full, docs-only, nl-only (run-repair only)
    no_repair: false                 # pass --no-repair to run-repair
    max_repair: 5                    # repair rounds for run-repair
    conditions:                      # optional per-condition overrides
      - name: executable
        command: run-repair
        context_mode: full
        no_repair: false
    models:                          # name -> actor spec
      kimi: kimi
      deepseek-v4-flash: claude:deepseek-v4-flash
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

_BATCH_COMMANDS = {"run", "run-repair"}
_CONTEXT_MODES = {"full", "docs-only", "nl-only"}


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


def load_conditions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized condition entries for a matrix."""
    raw_conditions = data.get("conditions")
    if raw_conditions is None:
        raw_conditions = [{"name": data.get("condition", "default")}]
    if not isinstance(raw_conditions, list) or not raw_conditions:
        raise ValueError("matrix 'conditions' must be a non-empty list when provided")

    conditions: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_conditions):
        if not isinstance(raw, dict):
            raise ValueError("each condition must be a YAML mapping")
        name = str(raw.get("name", f"condition-{idx + 1}"))
        command = str(raw.get("command", data.get("command", "run")))
        context_mode = str(raw.get("context_mode", data.get("context_mode", "full")))
        if command not in _BATCH_COMMANDS:
            raise ValueError(f"unsupported batch command: {command}")
        if context_mode not in _CONTEXT_MODES:
            raise ValueError(f"unsupported context_mode: {context_mode}")
        conditions.append(
            {
                "name": name,
                "command": command,
                "context_mode": context_mode,
                "no_repair": bool(raw.get("no_repair", data.get("no_repair", False))),
                "max_repair": int(raw.get("max_repair", data.get("max_repair", settings.DEFAULT_MAX_REPAIR))),
            }
        )
    return conditions


def _safe_condition_name(name: str) -> str:
    """Make a condition name safe for a run subdirectory."""
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


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
        conditions = load_conditions(data)
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
        self_check = bool(data.get("self_check", True))

        plan = [
            (condition, name, spec, tid)
            for condition in conditions
            for name, spec in models.items()
            for tid in task_ids
        ]

        total_attempts = len(plan) * passes
        console.print(
            f"[bold]Batch plan:[/bold] {len(conditions)} conditions × "
            f"{len(models)} models × {len(task_ids)} tasks "
            f"= {len(plan)} task-model entries | attempts={total_attempts} "
            f"| passes={passes} | sandbox={sandbox} | self_check={self_check} "
            f"| run_dir={run_dir}"
        )
        for condition, name, spec, tid in plan:
            console.print(
                f"  - {condition['name']}:{condition['command']} "
                f"{name} ({spec})  {tid}"
            )

        if dry_run:
            return

        def _one(
            condition: dict[str, Any], model_name: str, actor_spec: str, task_id: str
        ) -> tuple[str, str, str, int]:
            condition_run_dir = str(Path(run_dir) / _safe_condition_name(condition["name"]))
            cmd = [
                sys.executable, "-m", "sd_hwe_bench.cli", condition["command"], task_id,
                "--actor", actor_spec,
                "--passes", str(passes),
                "--run-dir", condition_run_dir,
                "--sandbox", sandbox,
                "--timeout", str(timeout),
                "--dataset", str(dataset),
            ]
            if condition["command"] == "run" and not self_check:
                cmd.append("--no-self-check")
            if condition["command"] == "run-repair":
                cmd.extend(["--max-repair", str(condition["max_repair"])])
                cmd.extend(["--context-mode", condition["context_mode"]])
                if condition["no_repair"]:
                    cmd.append("--no-repair")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return condition["name"], model_name, task_id, proc.returncode

        failures = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {
                ex.submit(_one, c, n, s, t): (c["name"], n, t)
                for (c, n, s, t) in plan
            }
            for fut in as_completed(futures):
                condition_name, name, tid, rc = fut.result()
                ok = rc == 0
                if not ok:
                    failures += 1
                color = "green" if ok else "red"
                console.print(
                    f"  [{color}]{'ok' if ok else 'FAIL'}[/{color}] "
                    f"{condition_name} {name} {tid} (rc={rc})"
                )

        # Aggregate leaderboard from the shared run_dir manifests.
        manager = ArchiveManager(Path(run_dir))
        board = LeaderboardBuilder(manager).build()
        console.print(board.to_markdown())

        if failures:
            console.print(f"[yellow]{failures}/{len(plan)} rollouts returned non-zero.[/yellow]")
            raise typer.Exit(code=1)
