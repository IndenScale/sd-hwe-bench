"""Score a pre-generated agent output directory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from sd_hwe_bench.cli_common import setup_logging
from sd_hwe_bench.console import print_score
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.sandbox.runner import SandboxBackend, SandboxRunner
from sd_hwe_bench.scorer import score_task


def register(app: typer.Typer) -> None:
    @app.command("score")
    def score_command(
        task_id: str = typer.Argument(..., help="Task ID."),
        output: Path = typer.Argument(..., help="Path to agent output directory (workspace)."),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        sandbox: SandboxBackend = typer.Option(
            "auto", "--sandbox", help="Sandbox backend for piki execution (auto/none/docker/podman)."
        ),
        sandbox_image: str = typer.Option(
            "sd-hwe-bench-piki:latest", "--sandbox-image", help="Container image for piki sandbox."
        ),
        rubrics: bool = typer.Option(False, "--rubrics", help="Enable LLM-as-Judge rubrics."),
        rubrics_model: Optional[str] = typer.Option(
            None, "--rubrics-model", help="Model for rubric judging."
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Score a pre-generated agent output directory."""
        setup_logging(verbose)

        ds = Dataset(dataset)
        task = ds.load_task(task_id)
        runner = SandboxRunner(backend=sandbox, image=sandbox_image)

        score = score_task(
            task_id=task_id,
            agent_output_dir=output,
            expected_deliverables=task.metadata.expected_deliverables,
            rubric_sets=task.metadata.rubrics if rubrics else None,
            requirement=task.metadata.requirement,
            rubrics_model=rubrics_model,
            runner=runner,
            task=task,
        )
        print_score(score)
