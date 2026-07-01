"""Typer CLI entry point for SD-HWE-Bench."""

from __future__ import annotations

import typer

from sd_hwe_bench.commands import (
    archive,
    batch,
    batch_status,
    constraints,
    leaderboard,
    list,
    run,
    run_repair,
    score,
)

app = typer.Typer(
    name="sd-hwe-bench",
    help="SD-HWE-Bench: evaluate AI agents on declarative hardware engineering tasks.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

list.register(app)
run.register(app)
run_repair.register(app)
score.register(app)
archive.register(app)
leaderboard.register(app)
batch.register(app)
batch_status.register(app)
constraints.register(app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
