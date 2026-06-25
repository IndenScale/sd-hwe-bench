"""List and summarize rollout archives."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.table import Table

from sd_hwe_bench.archive.manager import ArchiveManager
from sd_hwe_bench.cli_common import setup_logging
from sd_hwe_bench.console import console
from sd_hwe_bench.settings import settings


def register(app: typer.Typer) -> None:
    @app.command("archive")
    def archive_command(
        run_dir: Path = typer.Option(settings.RUN_DIR, "--run-dir", help="Rollout archive root."),
        format: str = typer.Option("markdown", "--format", help="Output format: json or markdown."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """List and summarize rollout archives."""
        setup_logging(verbose)

        manager = ArchiveManager(run_dir)
        summary = manager.summarize()

        if format == "json":
            console.print(json.dumps(summary, indent=2, default=str))
            return

        table = Table(title=f"Rollout Archives ({len(summary)} runs)")
        table.add_column("Run", style="cyan")
        table.add_column("Task", style="green")
        table.add_column("Actor", style="yellow")
        table.add_column("Success", style="magenta")
        table.add_column("Score", style="blue")

        for entry in summary:
            status = "✓" if entry.get("success") else "✗"
            table.add_row(
                entry.get("run_name", "?"),
                entry.get("task_id", "?"),
                entry.get("actor", "?"),
                status,
                f"{entry.get('overall_score', 0):.0%}",
            )

        console.print(table)
