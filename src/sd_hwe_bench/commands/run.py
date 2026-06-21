"""Run an Actor-Critic rollout on one or more tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from sd_hwe_bench.actors import create_actor
from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console, print_score
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.prompts import PromptBuilder
from sd_hwe_bench.sandbox.runner import SandboxBackend, SandboxRunner
from sd_hwe_bench.sandbox.workspace import Workspace
from sd_hwe_bench.scorer import TaskScore, compute_pass_at_k, score_task


def register(app: typer.Typer) -> None:
    @app.command("run")
    def run_task(
        task_id: str = typer.Argument(..., help="Task ID or prefix, e.g. telecom/comprehensive-001."),
        actor: str = typer.Option(
            "kimi",
            "--actor",
            "-a",
            help="Actor spec: kimi[:model], codex[:model], gemini[:model], openai:MODEL, deepseek:MODEL.",
        ),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        passes: int = typer.Option(1, "--passes", "-p", help="Number of independent runs per task."),
        run_dir: Path = typer.Option(
            Path("runs"), "--run-dir", help="Directory to store rollout archives."
        ),
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
        piki_ref: Optional[Path] = typer.Option(
            None, "--piki-ref", help="Path to full piki reference (e.g. piki/AGENTS.md)."
        ),
        timeout: int = typer.Option(600, "--timeout", "-t", help="Actor timeout in seconds."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Run an Actor-Critic rollout on a task."""
        setup_logging(verbose)

        ds = Dataset(dataset)
        task_ids = resolve_task_ids(ds, task_id)
        if not task_ids:
            console.print(f"[red]No tasks matched: {task_id}[/red]")
            raise typer.Exit(code=1)

        runner = SandboxRunner(backend=sandbox, image=sandbox_image)
        builder = PromptBuilder(piki_ref_path=piki_ref)

        all_scores: list[list[TaskScore]] = []

        for tid in task_ids:
            task = ds.load_task(tid)
            task_scores: list[TaskScore] = []

            for attempt in range(passes):
                console.print(
                    f"\n[bold]Running {actor} on {tid} (attempt {attempt + 1}/{passes})...[/bold]"
                )

                ws = Workspace.create(
                    run_root=run_dir,
                    task_id=tid,
                    actor_name=actor.split(":")[0],
                    model=actor,
                    scaffold_dir=task.scaffold_dir,
                )

                prompt = builder.build(
                    task_metadata=task.metadata.model_dump(),
                    scaffold_dir=task.scaffold_dir,
                    require_generator=True,
                )
                ws.write_prompt(prompt)

                act = create_actor(actor, timeout=timeout)
                result = act.run(prompt, ws.project_dir)

                ws.log_trajectory(
                    {
                        "event": "actor_finished",
                        "actor": actor,
                        "success": result.success,
                        "files_written": result.files_written,
                        "elapsed_s": result.elapsed_s,
                        "error": result.error,
                        "raw_output_preview": result.raw_output[:2000],
                    }
                )

                if result.error:
                    console.print(f"[red]Actor error: {result.error}[/red]")

                score = score_task(
                    task_id=tid,
                    agent_output_dir=ws.project_dir,
                    expected_deliverables=task.metadata.expected_deliverables,
                    rubric_sets=task.metadata.rubrics if rubrics else None,
                    requirement=task.metadata.requirement,
                    rubrics_model=rubrics_model,
                    runner=runner,
                    task=task,
                )

                ws.update_manifest(
                    {
                        "success": score.success,
                        "overall_score": score.overall_score,
                        "layers": {
                            name: {"passed": ls.passed, "total": ls.total}
                            for name, ls in score.layers.items()
                        },
                        "deliverables": score.deliverable_scores,
                        "rubric_score": score.rubric_score,
                        "actor_elapsed_s": result.elapsed_s,
                        "files_written": result.files_written,
                    }
                )

                task_scores.append(score)
                print_score(score)

            all_scores.append(task_scores)

        if len(all_scores) > 1 or passes > 1:
            console.print(f"\n[bold]Pass@1: {compute_pass_at_k(all_scores, k=1):.0%}[/bold]")
