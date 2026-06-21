"""List available benchmark tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console
from sd_hwe_bench.dataset import Dataset


def register(app: typer.Typer) -> None:
    @app.command("list")
    def list_tasks(
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        domain: Optional[str] = typer.Option(None, "--domain", help="Filter by domain."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """List available benchmark tasks."""
        setup_logging(verbose)
        ds = Dataset(dataset)
        task_ids = resolve_task_ids(ds, None)

        if domain:
            task_ids = [tid for tid in task_ids if tid.startswith(domain)]

        table = Table(title=f"SD-HWE-Bench Tasks ({len(task_ids)} found)")
        table.add_column("Task ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Difficulty", style="magenta")
        table.add_column("Plugins", style="dim")

        for tid in task_ids:
            task = ds.load_task(tid)
            table.add_row(
                tid,
                task.metadata.name,
                task.metadata.task_type.value,
                task.metadata.difficulty.value,
                ", ".join(task.metadata.plugins),
            )

        console.print(table)
