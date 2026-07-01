"""Run an Actor through a multi-turn repair loop with explicit termination."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, cast

import typer

from sd_hwe_bench.actors import create_actor
from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console, print_score
from sd_hwe_bench.constraints import (
    build_constraint_catalog,
    collect_score_diagnostics,
    parse_constraint_selectors,
    render_diagnostics,
    summarize_diagnostics,
)
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.prompts import REPAIR_MARKERS, PromptBuilder
from sd_hwe_bench.sandbox.runner import SandboxBackend, SandboxRunner
from sd_hwe_bench.sandbox.workspace import Workspace
from sd_hwe_bench.scorer import TaskScore, compute_pass_at_k, score_task
from sd_hwe_bench.settings import settings


def _detect_marker(project_dir: Path) -> tuple[Optional[str], str]:
    """Return (reason_key, rationale) if a termination marker exists."""
    for key, filename in REPAIR_MARKERS.items():
        path = project_dir / filename
        if path.exists():
            rationale = path.read_text(encoding="utf-8").strip() if path.stat().st_size > 0 else ""
            return key, rationale
    return None, ""


def _score_to_dict(score: TaskScore) -> dict:
    """Serialize a TaskScore for manifest storage."""
    return {
        "success": score.success,
        "overall_score": score.overall_score,
        "layers": {
            name: {"passed": ls.passed, "total": ls.total, "failed": ls.failed}
            for name, ls in score.layers.items()
        },
        "deliverables": score.deliverable_scores,
    }


def _constraint_ids(items: list) -> set[str]:
    return {str(item.id) for item in items}


def register(app: typer.Typer) -> None:
    @app.command("run-repair")
    def run_repair(
        task_id: str = typer.Argument(
            ..., help="Task ID or prefix, e.g. telecom/comprehensive-001."
        ),
        actor: str = typer.Option(
            settings.DEFAULT_ACTOR,
            "--actor",
            "-a",
            help="Actor spec: kimi[:model], codex[:model].",
        ),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        passes: int = typer.Option(
            settings.DEFAULT_PASSES, "--passes", "-p", help="Number of independent runs per task."
        ),
        max_repair: int = typer.Option(
            settings.DEFAULT_MAX_REPAIR,
            "--max-repair",
            "-r",
            help="Maximum number of repair rounds (excluding initial generation).",
        ),
        no_repair: bool = typer.Option(
            False,
            "--no-repair",
            help="Baseline mode: run a single turn without ESA feedback or repair loop.",
        ),
        context_mode: str = typer.Option(
            "full",
            "--context-mode",
            help="Experimental context condition: full, docs-only, or nl-only.",
        ),
        constraint_coverage_mode: str = typer.Option(
            "full",
            "--constraint-coverage-mode",
            help="Constraint visibility mode for experiments: full, explicit-mute, random-mute.",
        ),
        prompt_mute: str = typer.Option(
            "",
            "--prompt-mute",
            help="Comma-separated constraint selectors hidden from the prompt, e.g. id:X,family:layout,layer:L3.",
        ),
        feedback_mute: str = typer.Option(
            "",
            "--feedback-mute",
            help="Comma-separated constraint selectors hidden from repair feedback.",
        ),
        mute_ratio: float = typer.Option(
            0.0,
            "--mute-ratio",
            help="Random mute ratio used when --constraint-coverage-mode=random-mute.",
        ),
        mute_seed: Optional[int] = typer.Option(
            None,
            "--mute-seed",
            help="Random seed for random constraint mute conditions.",
        ),
        diagnostic_verbosity: str = typer.Option(
            "localized",
            "--diagnostic-verbosity",
            help="Repair diagnostic renderer: none, coarse, attributed, localized.",
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
        piki_ref: Optional[Path] = typer.Option(
            None, "--piki-ref", help="Path to full piki reference (e.g. piki/AGENTS.md)."
        ),
        timeout: int = typer.Option(
            settings.DEFAULT_ACTOR_TIMEOUT_S,
            "--timeout",
            "-t",
            help="Actor timeout in seconds per turn.",
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
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Run an Actor through a multi-turn repair loop.

        The Actor may report completion via `.sdhwe.done`, or failure via
        `.sdhwe.give_up`, `.sdhwe.info_gap`, or `.sdhwe.no_solution`.
        If none of these occur and the design does not pass, the loop terminates
        with reason `budget_exceeded` after MAX_REPAIR rounds.
        """
        setup_logging(verbose)
        if context_mode not in {"full", "docs-only", "nl-only"}:
            console.print("[red]--context-mode must be one of: full, docs-only, nl-only[/red]")
            raise typer.Exit(code=1)
        if constraint_coverage_mode not in {"full", "explicit-mute", "random-mute"}:
            console.print(
                "[red]--constraint-coverage-mode must be one of: full, explicit-mute, random-mute[/red]"
            )
            raise typer.Exit(code=1)
        if diagnostic_verbosity not in {"none", "coarse", "attributed", "localized"}:
            console.print(
                "[red]--diagnostic-verbosity must be one of: none, coarse, attributed, localized[/red]"
            )
            raise typer.Exit(code=1)
        prompt_context_mode = cast(Literal["full", "docs-only", "nl-only"], context_mode)
        repair_diagnostic_verbosity = cast(
            Literal["none", "coarse", "attributed", "localized"], diagnostic_verbosity
        )
        object.__setattr__(settings, "ACTOR_SANDBOX", actor_sandbox)

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
            catalog = build_constraint_catalog(task)
            try:
                prompt_selectors = parse_constraint_selectors(prompt_mute)
                feedback_selectors = parse_constraint_selectors(feedback_mute)
            except ValueError as exc:
                console.print(f"[red]{exc}[/red]")
                raise typer.Exit(code=1) from exc

            random_muted = (
                catalog.randomized(mute_ratio, mute_seed)
                if constraint_coverage_mode == "random-mute"
                else []
            )
            prompt_muted = catalog.selected(prompt_selectors)
            feedback_muted = catalog.selected(feedback_selectors)
            if random_muted:
                prompt_muted = sorted(
                    {spec.id: spec for spec in [*prompt_muted, *random_muted]}.values(),
                    key=lambda s: s.id,
                )
                feedback_muted = sorted(
                    {spec.id: spec for spec in [*feedback_muted, *random_muted]}.values(),
                    key=lambda s: s.id,
                )
            prompt_muted_ids = _constraint_ids(prompt_muted)
            feedback_muted_ids = _constraint_ids(feedback_muted)
            visible_constraints = [
                spec.to_dict() for spec in catalog.constraints if spec.id not in prompt_muted_ids
            ]
            task_scores: list[TaskScore] = []

            for attempt in range(passes):
                console.print(
                    f"\n[bold]Running {actor} on {tid} (attempt {attempt + 1}/{passes}, max repair={max_repair})...[/bold]"
                )

                ws = Workspace.create(
                    run_root=run_dir,
                    task_id=tid,
                    actor_name=actor.split(":")[0],
                    model=actor,
                    scaffold_dir=task.scaffold_dir,
                    attempt=attempt,
                    scaffold_excludes=["docs"] if context_mode == "nl-only" else None,
                    isolate=isolate,
                    work_root=settings.ISOLATED_WORK_ROOT if isolate else None,
                )

                act = create_actor(actor, timeout=timeout)

                initial_prompt = builder.build(
                    task_metadata=task.metadata.model_dump(),
                    scaffold_dir=task.scaffold_dir,
                    require_generator=True,
                    repair_mode=not no_repair,
                    baseline_mode=no_repair,
                    context_mode=prompt_context_mode,
                    visible_constraints=visible_constraints,
                )
                ws.write_prompt(initial_prompt)

                turn_scores: list[dict] = []
                termination_reason: Optional[str] = None
                agent_declared_reason: str = ""
                final_score: Optional[TaskScore] = None
                current_prompt = initial_prompt

                for turn in range(max_repair + 1):
                    console.print(f"  [dim]Turn {turn}/{max_repair}...[/dim]")

                    result = act.run(current_prompt, ws.project_dir)
                    ws.append_actor_log(f"turn_{turn}", result.raw_output)

                    ws.log_trajectory(
                        {
                            "event": "actor_turn",
                            "turn": turn,
                            "actor": actor,
                            "success": result.success,
                            "files_written": result.files_written,
                            "elapsed_s": result.elapsed_s,
                            "error": result.error,
                            "raw_output_preview": result.raw_output[: settings.LOG_PREVIEW_CHARS],
                        }
                    )

                    if result.error:
                        console.print(f"[red]Actor error on turn {turn}: {result.error}[/red]")
                        termination_reason = "actor_error"
                        break

                    score = score_task(
                        task_id=tid,
                        agent_output_dir=ws.project_dir,
                        expected_deliverables=task.metadata.expected_deliverables,
                        rubric_sets=None,
                        requirement=task.metadata.requirement,
                        runner=runner,
                        task=task,
                    )
                    full_diagnostics = collect_score_diagnostics(score, catalog)
                    visible_feedback_diagnostics = [
                        diag for diag in full_diagnostics if diag.constraint_id not in feedback_muted_ids
                    ]
                    diagnostics_summary = summarize_diagnostics(
                        full_diagnostics,
                        catalog,
                        muted_constraint_ids=feedback_muted_ids,
                    )
                    ws.log_trajectory(
                        {
                            "event": "diagnostics",
                            "turn": turn,
                            "diagnostic_verbosity": diagnostic_verbosity,
                            "summary": diagnostics_summary,
                            "diagnostics": [diag.to_dict() for diag in full_diagnostics],
                            "feedback_diagnostics": [
                                diag.to_dict() for diag in visible_feedback_diagnostics
                            ],
                        }
                    )
                    turn_scores.append(
                        {
                            "turn": turn,
                            **_score_to_dict(score),
                            "actor_elapsed_s": result.elapsed_s,
                            "diagnostics": diagnostics_summary,
                        }
                    )
                    final_score = score
                    console.print(
                        f"  [dim]Turn {turn} score: {score.overall_score:.0%} success={score.success}[/dim]"
                    )

                    # Check for explicit termination markers
                    marker, rationale = _detect_marker(ws.project_dir)
                    if marker:
                        agent_declared_reason = rationale
                        if marker == "done" and score.success:
                            termination_reason = "success"
                        elif marker == "done":
                            termination_reason = "done_but_failed"
                        else:
                            termination_reason = marker
                        console.print(
                            f"  [yellow]Agent declared '{marker}': {rationale[:80]}[/yellow]"
                        )
                        break

                    if score.success:
                        termination_reason = "success"
                        console.print(f"  [green]Task passed on turn {turn}[/green]")
                        break

                    if no_repair:
                        termination_reason = "baseline"
                        console.print("  [dim]Baseline turn complete (no repair)[/dim]")
                        break

                    if turn >= max_repair:
                        termination_reason = "budget_exceeded"
                        console.print(
                            f"  [red]Budget exhausted after {max_repair} repair rounds[/red]"
                        )
                        break

                    # Build repair prompt for next turn
                    diagnostics = render_diagnostics(
                        visible_feedback_diagnostics,
                        verbosity=diagnostic_verbosity,
                        max_items=settings.REPAIR_PROMPT_MAX_DIAGNOSTICS,
                    )
                    current_prompt = builder.build_repair_turn(
                        task_metadata=task.metadata.model_dump(),
                        project_dir=ws.project_dir,
                        score=score,
                        turn=turn + 1,
                        max_repair=max_repair,
                        diagnostics=diagnostics,
                        diagnostic_verbosity=repair_diagnostic_verbosity,
                    )
                    ws.log_trajectory(
                        {
                            "event": "repair_prompt",
                            "turn": turn + 1,
                            "prompt": current_prompt,
                        }
                    )

                # Ensure final_score is set even if actor errored on turn 0
                if final_score is None:
                    final_score = TaskScore(task_id=tid, success=False)

                # Archive the isolated (out-of-repo) working copy back into
                # runs/<run>/workspace before writing the manifest.  No-op when
                # not isolated.
                ws.archive_project_dir(cleanup=settings.ISOLATED_WORK_CLEANUP)

                ws.update_manifest(
                    {
                        "success": final_score.success and termination_reason == "success",
                        "overall_score": final_score.overall_score,
                        "layers": {
                            name: {"passed": ls.passed, "total": ls.total}
                            for name, ls in final_score.layers.items()
                        },
                        "deliverables": final_score.deliverable_scores,
                        "termination_reason": termination_reason,
                        "context_mode": context_mode,
                        "repair_mode": not no_repair,
                        "constraint_coverage_mode": constraint_coverage_mode,
                        "constraint_catalog": catalog.to_dicts(),
                        "constraint_coverage": catalog.coverage_summary(),
                        "enabled_constraints": [
                            spec.id for spec in catalog.constraints if spec.id not in prompt_muted_ids
                        ],
                        "prompt_muted_constraints": [spec.to_dict() for spec in prompt_muted],
                        "feedback_muted_constraints": [spec.to_dict() for spec in feedback_muted],
                        "offline_constraints": [
                            spec.to_dict() for spec in catalog.constraints if not spec.executable
                        ],
                        "diagnostic_verbosity": diagnostic_verbosity,
                        "mute_seed": mute_seed,
                        "mute_ratio": mute_ratio,
                        "agent_declared_reason": agent_declared_reason,
                        "repair_rounds_used": len(turn_scores) - 1,
                        "max_repair": max_repair,
                        "turn_scores": turn_scores,
                        "actor_elapsed_s": sum(t.get("actor_elapsed_s", 0.0) for t in turn_scores),
                    }
                )

                task_scores.append(final_score)
                print_score(final_score)

            all_scores.append(task_scores)

        if len(all_scores) > 1 or passes > 1:
            console.print(f"\n[bold]Pass@1: {compute_pass_at_k(all_scores, k=1):.0%}[/bold]")
