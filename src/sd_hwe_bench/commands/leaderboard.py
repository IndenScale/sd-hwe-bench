"""Generate leaderboard from rollout archives."""

from __future__ import annotations

from pathlib import Path

import typer

from sd_hwe_bench.archive.leaderboard import LeaderboardBuilder
from sd_hwe_bench.archive.manager import ArchiveManager
from sd_hwe_bench.cli_common import setup_logging
from sd_hwe_bench.console import console
from sd_hwe_bench.settings import settings


def register(app: typer.Typer) -> None:
    @app.command("leaderboard")
    def leaderboard_command(
        run_dir: Path = typer.Option(settings.RUN_DIR, "--run-dir", help="Rollout archive root."),
        output: Path = typer.Option(
            settings.LEADERBOARD_DIR, "--output", help="Leaderboard output directory."
        ),
        update: bool = typer.Option(False, "--update", help="Write leaderboard files."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Generate leaderboard from rollout archives."""
        setup_logging(verbose)

        manager = ArchiveManager(run_dir)
        builder = LeaderboardBuilder(manager)
        board = builder.build()

        if update:
            output.mkdir(parents=True, exist_ok=True)
            board.save(output / "results.json", output / "results.md")
            console.print(f"[green]Leaderboard saved to {output}[/green]")

        console.print(board.to_markdown())
