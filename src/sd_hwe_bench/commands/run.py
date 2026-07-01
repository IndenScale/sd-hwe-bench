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
from sd_hwe_bench.cli_common import build_env_vars, resolve_task_ids, setup_logging
from sd_hwe_bench.console import console, print_score, print_score_summary
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.prompts import PromptBuilder
from sd_hwe_bench.sandbox.runner import SandboxBackend, SandboxRunner
from sd_hwe_bench.sandbox.workspace import Workspace
from sd_hwe_bench.scorer import TaskScore, compute_pass_at_k, score_task
from sd_hwe_bench.settings import settings

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
        return min(settings.MAX_AUTO_JOBS, (os.cpu_count() or 1))
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
    env_vars: dict[str, str] | None = None,
    self_check: bool = True,
    isolate: bool = True,
    actor_sandbox: str = "auto",
) -> dict:
    """Execute a single rollout in a worker process.

    This function must be module-level and accept only pickle-friendly arguments
    so that it can be dispatched via ``ProcessPoolExecutor``.
    """
    setup_logging(verbose)

    # Apply self-check override (settings is frozen, use object.__setattr__)
    if not self_check:
        object.__setattr__(settings, "SELF_CHECK_ENABLED", False)
    object.__setattr__(settings, "ACTOR_SANDBOX", actor_sandbox)

    ds = Dataset(dataset_path)
    task = ds.load_task(job.task_id)

    runner = SandboxRunner(backend=sandbox, image=sandbox_image, env_vars=env_vars)
    builder = PromptBuilder(piki_ref_path=piki_ref)

    ws = Workspace.create(
        run_root=run_dir,
        task_id=job.task_id,
        actor_name=actor_spec.split(":")[0],
        model=actor_spec,
        scaffold_dir=task.scaffold_dir,
        attempt=job.attempt,
        isolate=isolate,
        work_root=settings.ISOLATED_WORK_ROOT if isolate else None,
    )

    prompt = builder.build(
        task_metadata=task.metadata.model_dump(),
        scaffold_dir=task.scaffold_dir,
        require_generator=True,

    )
    ws.write_prompt(prompt)

    act = create_actor(actor_spec, timeout=timeout)
    ws.log_trajectory(
        {
            "event": "actor_started",
            "actor": actor_spec,
            "timeout_s": timeout,
        }
    )
    result = act.run(prompt, ws.project_dir)
    ws.append_actor_log("initial", result.raw_output)

    ws.log_trajectory(
        {
            "event": "actor_finished",
            "actor": actor_spec,
            "success": result.success,
            "files_written": result.files_written,
            "elapsed_s": result.elapsed_s,
            "error": result.error,
            "raw_output_preview": result.raw_output[: settings.LOG_PREVIEW_CHARS],
        }
    )

    # ── Self-check hook ──────────────────────────────────────────
    # After the agent finishes, automatically run piki check.  If errors
    # remain, inject diagnostics and let the agent fix them — up to
    # SELF_CHECK_MAX_ROUNDS iterations.
    self_check_rounds = 0
    while settings.SELF_CHECK_ENABLED and self_check_rounds < settings.SELF_CHECK_MAX_ROUNDS:
        sc_score = score_task(
            task_id=job.task_id,
            agent_output_dir=ws.project_dir,
            expected_deliverables=task.metadata.expected_deliverables,
            rubric_sets=None,  # no rubrics during self-check
            requirement=task.metadata.requirement,
            rubrics_model=None,
            runner=runner,
            task=task,
        )
        if sc_score.success:
            break  # all clear — no self-check needed

        # Extract diagnostics from the piki critic
        diagnostics = []
        piki_result = next(
            (cr for cr in sc_score.critic_results if cr.name == "piki"), None
        )
        if piki_result and piki_result.artifacts.get("parsed"):
            parsed = piki_result.artifacts["parsed"]
            for rule in parsed.get("results", []):
                if not rule.get("passed"):
                    diagnostics.append({
                        "rule_id": rule.get("rule_id", ""),
                        "name": rule.get("name", ""),
                        "message": rule.get("message", ""),
                        "file": rule.get("file", ""),
                    })
            for diag in parsed.get("diagnostics", []):
                if str(diag.get("severity", "")).upper() in ("ERROR", "FATAL"):
                    diagnostics.append({
                        "rule_id": diag.get("code", ""),
                        "name": diag.get("code", ""),
                        "message": diag.get("message", ""),
                        "file": diag.get("file", ""),
                    })

        if not diagnostics:
            break  # syntax errors or deliverable-only — don't loop

        self_check_rounds += 1
        sc_prompt = builder.build_self_check_turn(
            task_metadata=task.metadata.model_dump(),
            project_dir=ws.project_dir,
            diagnostics=diagnostics,
            turn=self_check_rounds,
            max_rounds=settings.SELF_CHECK_MAX_ROUNDS,
        )
        ws.log_trajectory({
            "event": "self_check_prompt",
            "round": self_check_rounds,
            "diagnostics_count": len(diagnostics),
        })
        ws.log_trajectory({
            "event": "actor_started",
            "actor": actor_spec,
            "timeout_s": timeout,
            "phase": "self_check_repair",
            "round": self_check_rounds,
        })
        result = act.run(sc_prompt, ws.project_dir)
        ws.append_actor_log(f"self_check_round_{self_check_rounds}", result.raw_output)
        ws.log_trajectory({
            "event": "self_check_finished",
            "round": self_check_rounds,
            "success": result.success,
            "files_written": result.files_written,
            "elapsed_s": result.elapsed_s,
            "error": result.error,
        })
    # ── End self-check hook ──────────────────────────────────────

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

    # Copy the isolated (out-of-repo) working copy back into runs/<run>/workspace
    # so the archive is self-contained.  No-op when not isolated.
    ws.archive_project_dir(cleanup=settings.ISOLATED_WORK_CLEANUP)

    rollout_success = result.success and score.success
    ws.update_manifest(
        {
            "success": rollout_success,
            "score_success": score.success,
            "actor_success": result.success,
            "overall_score": score.overall_score,
            "layers": {
                name: {"passed": ls.passed, "total": ls.total} for name, ls in score.layers.items()
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
        "success": rollout_success,
        "score_success": score.success,
        "actor_success": result.success,
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
    env_vars: dict[str, str] | None = None,
    self_check: bool = True,
    isolate: bool = True,
    actor_sandbox: str = "auto",
) -> list[list[TaskScore]]:
    """Run rollouts serially, preserving the original interactive output."""
    all_scores: list[list[TaskScore]] = []

    # Recreate runner with env vars if they were provided (the caller's runner
    # may have been constructed before env_vars were resolved).
    if env_vars is not None:
        runner = SandboxRunner(backend=runner.backend, image=runner.image, env_vars=env_vars)

    # Apply self-check override
    if not self_check:
        object.__setattr__(settings, "SELF_CHECK_ENABLED", False)
    object.__setattr__(settings, "ACTOR_SANDBOX", actor_sandbox)

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
                isolate=isolate,
                work_root=settings.ISOLATED_WORK_ROOT if isolate else None,
            )

            prompt = builder.build(
                task_metadata=task.metadata.model_dump(),
                scaffold_dir=task.scaffold_dir,
                require_generator=True,

            )
            ws.write_prompt(prompt)

            act = create_actor(actor, timeout=timeout)
            ws.log_trajectory(
                {
                    "event": "actor_started",
                    "actor": actor,
                    "timeout_s": timeout,
                }
            )
            result = act.run(prompt, ws.project_dir)
            ws.append_actor_log("initial", result.raw_output)

            ws.log_trajectory(
                {
                    "event": "actor_finished",
                    "actor": actor,
                    "success": result.success,
                    "files_written": result.files_written,
                    "elapsed_s": result.elapsed_s,
                    "error": result.error,
                    "raw_output_preview": result.raw_output[: settings.LOG_PREVIEW_CHARS],
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

            ws.archive_project_dir(cleanup=settings.ISOLATED_WORK_CLEANUP)

            rollout_success = result.success and score.success
            ws.update_manifest(
                {
                    "success": rollout_success,
                    "score_success": score.success,
                    "actor_success": result.success,
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

            score.success = rollout_success
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
    env_vars: dict[str, str] | None = None,
    self_check: bool = True,
    isolate: bool = True,
    actor_sandbox: str = "auto",
) -> list[list[TaskScore]]:
    """Run rollouts in parallel using a process pool."""
    jobs_list = [
        RolloutJob(task_id=tid, attempt=attempt) for tid in task_ids for attempt in range(passes)
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
                env_vars,
                self_check,
                isolate,
                actor_sandbox,
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
        task_id: str = typer.Argument(
            ..., help="Task ID or prefix, e.g. telecom/comprehensive-001."
        ),
        actor: str = typer.Option(
            settings.DEFAULT_ACTOR,
            "--actor",
            "-a",
            help="Actor spec: kimi[:model], codex[:model], claude[:model].",
        ),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        passes: int = typer.Option(
            settings.DEFAULT_PASSES, "--passes", "-p", help="Number of independent runs per task."
        ),
        jobs: int = typer.Option(
            -1,
            "--jobs",
            "-j",
            help=f"Max parallel rollouts. -1 = auto (min({settings.MAX_AUTO_JOBS}, cpu_count)); 1 = serial.",
        ),
        run_dir: Path = typer.Option(
            settings.RUN_DIR, "--run-dir", help="Directory to store rollout archives."
        ),
        sandbox: SandboxBackend = typer.Option(
            settings.DEFAULT_SANDBOX_BACKEND,
            "--sandbox",
            help="Sandbox backend for piki execution (auto/none/docker/podman).",
        ),
        sandbox_image: str = typer.Option(
            settings.DEFAULT_SANDBOX_IMAGE,
            "--sandbox-image",
            help="Container image for piki sandbox.",
        ),
        rubrics: bool = typer.Option(False, "--rubrics", help="Enable LLM-as-Judge rubrics."),
        rubrics_model: Optional[str] = typer.Option(
            None, "--rubrics-model", help="Model for rubric judging."
        ),
        piki_ref: Optional[Path] = typer.Option(
            None, "--piki-ref", help="Path to full piki reference (e.g. piki/AGENTS.md)."
        ),
        self_check: bool = typer.Option(
            settings.SELF_CHECK_ENABLED,
            "--self-check/--no-self-check",
            help="Enable/disable the automatic piki check + repair hook after agent run.",
        ),
        isolate: bool = typer.Option(
            settings.ACTOR_ISOLATE,
            "--isolate/--no-isolate",
            help="Run the actor in an out-of-repo workspace (only scaffold visible) "
            "so it cannot read reference solutions. Strongly recommended for formal runs.",
        ),
        actor_sandbox: str = typer.Option(
            settings.ACTOR_SANDBOX,
            "--actor-sandbox",
            help="Kernel-level actor isolation: auto|seatbelt|none "
            "(auto = macOS sandbox-exec when available).",
        ),
        timeout: int = typer.Option(
            settings.DEFAULT_ACTOR_TIMEOUT_S, "--timeout", "-t", help="Actor timeout in seconds."
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
        env: Optional[list[str]] = typer.Option(
            None,
            "--env",
            help="Environment variable to inject into the sandbox (KEY=VALUE). Repeatable.",
        ),
        env_file: Optional[Path] = typer.Option(
            None,
            "--env-file",
            help="Path to a KEY=VALUE file whose variables are injected into the sandbox.",
        ),
    ) -> None:
        """Run an Actor-Critic rollout on a task."""
        setup_logging(verbose)

        ds = Dataset(dataset)
        task_ids = resolve_task_ids(ds, task_id)
        if not task_ids:
            console.print(f"[red]No tasks matched: {task_id}[/red]")
            raise typer.Exit(code=1)

        try:
            env_vars = build_env_vars(env_options=env, env_file=env_file)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)

        effective_jobs = _effective_jobs(jobs)

        # ProcessPoolExecutor on macOS can cause silent failures when
        # forked subprocesses spawn their own subprocesses (e.g. codex CLI).
        # For single-task rollouts, always use serial mode regardless of
        # --jobs setting. Parallel mode is only used when multiple *distinct*
        # task IDs are being run simultaneously.
        use_parallel = effective_jobs > 1 and len(task_ids) > 1

        if self_check and use_parallel:
            console.print(
                "[yellow]Warning: --self-check is disabled in parallel mode.[/yellow]"
            )
            self_check = False

        if not use_parallel:
            runner = SandboxRunner(backend=sandbox, image=sandbox_image, env_vars=env_vars)
            builder = PromptBuilder(piki_ref_path=piki_ref)
            all_scores = _run_serial(
                task_ids=task_ids,
                self_check=self_check,
                passes=passes,
                ds=ds,
                run_dir=run_dir,
                actor=actor,
                runner=runner,
                builder=builder,
                timeout=timeout,
                rubrics=rubrics,
                rubrics_model=rubrics_model,
                env_vars=env_vars,
                isolate=isolate,
                actor_sandbox=actor_sandbox,
            )
        else:
            all_scores = _run_parallel(
                task_ids=task_ids,
                self_check=self_check,
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
                env_vars=env_vars,
                isolate=isolate,
                actor_sandbox=actor_sandbox,
            )

        if len(all_scores) > 1 or passes > 1:
            console.print(f"\n[bold]Pass@1: {compute_pass_at_k(all_scores, k=1):.0%}[/bold]")
