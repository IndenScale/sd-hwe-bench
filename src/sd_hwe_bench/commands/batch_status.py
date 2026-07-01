"""Inspect progress for a matrix-driven batch run."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import typer
from rich.table import Table

from sd_hwe_bench.cli_common import setup_logging
from sd_hwe_bench.commands.batch import (
    _complete_manifest,
    _safe_condition_name,
    expand_tasks,
    load_conditions,
    load_matrix,
)
from sd_hwe_bench.console import console
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.settings import settings


def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _manifest_state(manifest: dict[str, Any]) -> str:
    if _complete_manifest(manifest):
        return "complete"
    if manifest.get("termination_reason") == "actor_error":
        return "actor_error"
    return "in_flight"


def _last_nonempty_log_line(run_path: Path) -> str:
    log_path = run_path / "actor_output.log"
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if line:
            return line
    return ""


def _live_process_commands() -> list[str]:
    try:
        proc = subprocess.run(
            ["ps", "-axo", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return proc.stdout.splitlines()


def summarize_batch_status(matrix: Path, dataset: Path = Path(".")) -> dict[str, Any]:
    """Summarize completed and in-flight attempts for a batch matrix."""
    data = load_matrix(matrix)
    models: dict[str, str] = dict(data["models"])
    conditions = load_conditions(data)
    ds = Dataset(dataset)
    task_ids = expand_tasks(ds, list(data["tasks"]))
    passes = int(data.get("passes", settings.DEFAULT_PASSES))
    run_dir = Path(str(data.get("run_dir", settings.RUN_DIR)))
    live_commands = _live_process_commands()
    live_run = any(str(run_dir) in command for command in live_commands)

    entries: list[dict[str, Any]] = []
    totals = {
        "entries": 0,
        "attempts": 0,
        "complete": 0,
        "in_flight": 0,
        "stale": 0,
        "actor_error": 0,
        "remaining": 0,
    }

    for condition in conditions:
        condition_name = condition["name"]
        condition_dir = run_dir / _safe_condition_name(condition_name)
        live_condition = live_run or any(str(condition_dir) in command for command in live_commands)
        manifests: list[tuple[Path, dict[str, Any]]] = []
        if condition_dir.exists():
            for path in condition_dir.rglob("manifest.json"):
                manifest = _read_manifest(path)
                if manifest is not None:
                    manifests.append((path, manifest))

        for model_name, actor_spec in models.items():
            for task_id in task_ids:
                matched = [
                    (path, manifest)
                    for path, manifest in manifests
                    if manifest.get("task_id") == task_id and manifest.get("model") == actor_spec
                ]
                states = [_manifest_state(manifest) for _path, manifest in matched]
                complete = states.count("complete")
                raw_in_flight = states.count("in_flight")
                in_flight = raw_in_flight if live_condition else 0
                stale = 0 if live_condition else raw_in_flight
                actor_error = states.count("actor_error")
                remaining = max(0, passes - complete)
                latest_log = ""
                latest_path = ""
                if matched:
                    latest_path_obj, _latest_manifest = max(
                        matched, key=lambda item: item[0].parent.stat().st_mtime
                    )
                    latest_path = str(latest_path_obj.parent)
                    latest_log = _last_nonempty_log_line(latest_path_obj.parent)
                    logged_runs = [
                        (path, _last_nonempty_log_line(path.parent))
                        for path, _manifest in matched
                    ]
                    logged_runs = [(path, log) for path, log in logged_runs if log]
                    if logged_runs:
                        latest_log_path, latest_log = max(
                            logged_runs, key=lambda item: item[0].parent.stat().st_mtime
                        )
                        latest_path = str(latest_log_path.parent)

                status = (
                    "done"
                    if complete >= passes
                    else "running"
                    if in_flight
                    else "stale"
                    if stale
                    else "pending"
                )
                entry = {
                    "condition": condition_name,
                    "command": condition["command"],
                    "model_name": model_name,
                    "actor": actor_spec,
                    "task_id": task_id,
                    "passes": passes,
                    "complete": complete,
                    "in_flight": in_flight,
                    "stale": stale,
                    "actor_error": actor_error,
                    "remaining": remaining,
                    "status": status,
                    "latest_run": latest_path,
                    "latest_log": latest_log,
                }
                entries.append(entry)
                totals["entries"] += 1
                totals["attempts"] += passes
                totals["complete"] += complete
                totals["in_flight"] += in_flight
                totals["stale"] += stale
                totals["actor_error"] += actor_error
                totals["remaining"] += remaining

    return {
        "run_dir": str(run_dir),
        "passes": passes,
        "totals": totals,
        "entries": entries,
    }


def register(app: typer.Typer) -> None:
    @app.command("batch-status")
    def batch_status_command(
        matrix: Path = typer.Option(..., "--matrix", help="Path to batch matrix YAML."),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        format: str = typer.Option("text", "--format", help="Output format: text, table, or json."),
        show_log: bool = typer.Option(
            False,
            "--show-log",
            help="Include the latest non-empty actor log line for each entry.",
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Show completion and in-flight state for a batch matrix run."""
        setup_logging(verbose)
        summary = summarize_batch_status(matrix, dataset)

        if format == "json":
            console.print(json.dumps(summary, indent=2, ensure_ascii=False))
            return
        if format not in {"text", "table"}:
            console.print("[red]Unsupported --format. Use 'text', 'table', or 'json'.[/red]")
            raise typer.Exit(code=1)

        totals = summary["totals"]
        console.print(
            f"[bold]Batch status:[/bold] complete={totals['complete']}/{totals['attempts']} "
            f"| in_flight={totals['in_flight']} | stale={totals.get('stale', 0)} "
            f"| actor_error={totals['actor_error']} "
            f"| remaining={totals['remaining']} | run_dir={summary['run_dir']}"
        )

        if format == "text":
            for entry in summary["entries"]:
                console.print(
                    f"- {entry['condition']} {entry['task_id']} {entry['actor']}: "
                    f"{entry['status']} | complete={entry['complete']}/{entry['passes']} "
                    f"| in_flight={entry['in_flight']} | stale={entry.get('stale', 0)} "
                    f"| actor_error={entry['actor_error']} "
                    f"| remaining={entry['remaining']}"
                )
                if show_log and entry["latest_log"]:
                    console.print(f"  latest: {entry['latest_log']}")
            return

        table = Table(title="Matrix Entries")
        table.add_column("Condition", style="cyan", no_wrap=True)
        table.add_column("Task", style="green", no_wrap=True)
        table.add_column("Actor", style="yellow", no_wrap=True)
        table.add_column("Status", style="magenta", no_wrap=True)
        table.add_column("Complete", no_wrap=True)
        table.add_column("In Flight", no_wrap=True)
        table.add_column("Stale", no_wrap=True)
        table.add_column("Actor Error", no_wrap=True)
        table.add_column("Remaining", no_wrap=True)
        if show_log:
            table.add_column("Latest Log")

        for entry in summary["entries"]:
            row = [
                entry["condition"],
                entry["task_id"],
                entry["actor"],
                entry["status"],
                f"{entry['complete']}/{entry['passes']}",
                str(entry["in_flight"]),
                str(entry.get("stale", 0)),
                str(entry["actor_error"]),
                str(entry["remaining"]),
            ]
            if show_log:
                row.append(entry["latest_log"])
            table.add_row(*row)

        console.print(table)
