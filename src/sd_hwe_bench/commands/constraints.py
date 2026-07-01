"""Inspect task constraint catalogs."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console
from sd_hwe_bench.constraints import build_constraint_catalog
from sd_hwe_bench.dataset import Dataset


def register(app: typer.Typer) -> None:
    @app.command("constraints")
    def constraints_command(
        task_id: str = typer.Argument(..., help="Task ID or prefix, e.g. telecom/aidc-60mw-003."),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Export the applicable constraint catalog for one or more tasks."""

        setup_logging(verbose)
        ds = Dataset(dataset)
        task_ids = resolve_task_ids(ds, task_id)
        if not task_ids:
            console.print(f"[red]No tasks matched: {task_id}[/red]")
            raise typer.Exit(code=1)

        payload = []
        for tid in task_ids:
            task = ds.load_task(tid)
            catalog = build_constraint_catalog(task)
            payload.append(
                {
                    "task_id": tid,
                    "coverage": catalog.coverage_summary(),
                    "constraints": catalog.to_dicts(),
                }
            )

        if json_output:
            console.print(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        for item in payload:
            console.print(f"\n[bold]{item['task_id']}[/bold]")
            console.print(item["coverage"])
            for spec in item["constraints"]:
                executable = "exec" if spec["executable"] else "offline"
                console.print(
                    f"  - {spec['id']} [{spec['layer']}/{spec['family']}/{executable}] "
                    f"{spec['critic']} {spec['localization']}"
                )
