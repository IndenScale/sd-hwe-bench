"""Run an Actor-Critic rollout on one or more tasks."""

from __future__ import annotations

import dataclasses
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Optional

import typer

from sd_hwe_bench.actors import create_actor
from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console, print_score, print_score_summary
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.prompts import PromptBuilder
from sd_hwe_bench.sandbox.runner import SandboxBackend, SandboxRunner
from sd_hwe_bench.sandbox.workspace import Workspace
from sd_hwe_bench.scorer import TaskScore, compute_pass_at_k, score_task

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class RolloutJob:
    """A single rollout unit."""

    task_id: str
    attempt: int


def _effective_jobs(jobs: int) -> int:
    """Resolve the --jobs option to a concrete worker count.

    ``jobs == -1`` means "auto": use a conservative number of workers based on
    the host CPU count.
    """
    if jobs == -1:
        return min(4, (os.cpu_count() or 1))
    return max(1, jobs)


def _run_rollout(
    job: RolloutJob,
    dataset_path: Path,
    run_dir: Path,
    actor_spec: str,
    sandbox: SandboxBackend,
    sandbox_image: str,
    piki_ref: Path | None,
    timeout: int,
    rubrics: bool,
    rubrics_model: str | None,
    verbose: bool,
) -> dict:
    """Execute a single rollout in a worker process.

    This function must be module-level and accept only pickle-friendly arguments
    so that it can be dispatched via ``ProcessPoolExecutor``.
    """
    setup_logging(verbose)

    ds = Dataset(dataset_path)
    task = ds.load_task(job.task_id)

    runner = SandboxRunner(backend=sandbox, image=sandbox_image)
    builder = PromptBuilder(piki_ref_path=piki_ref)

    ws = Workspace.create(
        run_root=run_dir,
        task_id=job.task_id,
        actor_name=actor_spec.split(":")[0],
        model=actor_spec,
        scaffold_dir=task.scaffold_dir,
        attempt=job.attempt,
    )

    prompt = builder.build(
        task_metadata=task.metadata.model_dump(),
        scaffold_dir=task.scaffold_dir,
        require_generator=True,
    )
    ws.write_prompt(prompt)

    act = create_actor(actor_spec, timeout=timeout)
    result = act.run(prompt, ws.project_dir)

    ws.log_trajectory(
        {
            "event": "actor_finished",
            "actor": actor_spec,
            "success": result.success,
            "files_written": result.files_written,
            "elapsed_s": result.elapsed_s,
            "error": result.error,
            "raw_output_preview": result.raw_output[:2000],
        }
    )

    score = score_task(
        task_id=job.task_id,
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

    return {
        "task_id": job.task_id,
        "attempt": job.attempt,
        "run_dir": str(ws.run_dir),
        "success": score.success,
        "overall_score": score.overall_score,
        "layers": {
            name: {"passed": ls.passed, "total": ls.total, "errors": ls.errors}
            for name, ls in score.layers.items()
        },
        "deliverables": score.deliverable_scores,
        "rubric_score": score.rubric_score,
        "actor_error": result.error,
        "actor_elapsed_s": result.elapsed_s,
        "files_written": result.files_written,
    }


def _run_serial(
    task_ids: list[str],
    passes: int,
    ds: Dataset,
    run_dir: Path,
    actor: str,
    runner: SandboxRunner,
    builder: PromptBuilder,
    timeout: int,
    rubrics: bool,
    rubrics_model: str | None,
) -> list[list[TaskScore]]:
    """Run rollouts serially, preserving the original interactive output."""
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
                attempt=attempt,
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

    return all_scores


def _run_parallel(
    task_ids: list[str],
    passes: int,
    ds: Dataset,
    run_dir: Path,
    actor: str,
    sandbox: SandboxBackend,
    sandbox_image: str,
    piki_ref: Path | None,
    timeout: int,
    rubrics: bool,
    rubrics_model: str | None,
    jobs: int,
    verbose: bool,
) -> list[list[TaskScore]]:
    """Run rollouts in parallel using a process pool."""
    jobs_list = [
        RolloutJob(task_id=tid, attempt=attempt)
        for tid in task_ids
        for attempt in range(passes)
    ]

    console.print(
        f"\n[bold]Running {len(jobs_list)} rollouts with {jobs} parallel workers...[/bold]"
    )

    task_index: dict[str, int] = {tid: idx for idx, tid in enumerate(task_ids)}
    all_scores: list[list[TaskScore | None]] = [[None] * passes for _ in task_ids]

    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(
                _run_rollout,
                job,
                ds.root_dir,
                run_dir,
                actor,
                sandbox,
                sandbox_image,
                piki_ref,
                timeout,
                rubrics,
                rubrics_model,
                verbose,
            ): job
            for job in jobs_list
        }

        for future in futures:
            job = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.exception("Rollout failed for %s attempt %d", job.task_id, job.attempt)
                console.print(
                    f"[red]Rollout failed for {job.task_id} attempt {job.attempt + 1}: {exc}[/red]"
                )
                result = {
                    "task_id": job.task_id,
                    "attempt": job.attempt,
                    "run_dir": "",
                    "success": False,
                    "overall_score": 0.0,
                    "layers": {},
                    "deliverables": {},
                    "rubric_score": None,
                    "actor_error": str(exc),
                    "actor_elapsed_s": 0.0,
                    "files_written": 0,
                }

            print_score_summary(result)
            score = TaskScore(
                task_id=result["task_id"],
                success=result["success"],
                layers={},
                deliverable_scores=result.get("deliverables", {}),
                overall_score=result.get("overall_score", 0.0),
                rubric_score=result.get("rubric_score"),
            )
            all_scores[task_index[job.task_id]][job.attempt] = score

    # Convert from list-of-maybe-None to list-of-TaskScore.
    return [[s for s in task_scores if s is not None] for task_scores in all_scores]


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
        jobs: int = typer.Option(
            -1,
            "--jobs",
            "-j",
            help="Max parallel rollouts. -1 = auto (min(4, cpu_count)); 1 = serial.",
        ),
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

        effective_jobs = _effective_jobs(jobs)

        if effective_jobs == 1:
            runner = SandboxRunner(backend=sandbox, image=sandbox_image)
            builder = PromptBuilder(piki_ref_path=piki_ref)
            all_scores = _run_serial(
                task_ids=task_ids,
                passes=passes,
                ds=ds,
                run_dir=run_dir,
                actor=actor,
                runner=runner,
                builder=builder,
                timeout=timeout,
                rubrics=rubrics,
                rubrics_model=rubrics_model,
            )
        else:
            all_scores = _run_parallel(
                task_ids=task_ids,
                passes=passes,
                ds=ds,
                run_dir=run_dir,
                actor=actor,
                sandbox=sandbox,
                sandbox_image=sandbox_image,
                piki_ref=piki_ref,
                timeout=timeout,
                rubrics=rubrics,
                rubrics_model=rubrics_model,
                jobs=effective_jobs,
                verbose=verbose,
            )

        if len(all_scores) > 1 or passes > 1:
            console.print(f"\n[bold]Pass@1: {compute_pass_at_k(all_scores, k=1):.0%}[/bold]")
