"""Run an Actor through a multi-turn repair loop with explicit termination."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from sd_hwe_bench.actors import create_actor
from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console, print_score
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
            help="Actor spec: kimi[:model], gemini[:model], openai:MODEL, deepseek:MODEL.",
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
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Run an Actor through a multi-turn repair loop.

        The Actor may report completion via `.sdhwe.done`, or failure via
        `.sdhwe.give_up`, `.sdhwe.info_gap`, or `.sdhwe.no_solution`.
        If none of these occur and the design does not pass, the loop terminates
        with reason `budget_exceeded` after MAX_REPAIR rounds.
        """
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
                    f"\n[bold]Running {actor} on {tid} (attempt {attempt + 1}/{passes}, max repair={max_repair})...[/bold]"
                )

                ws = Workspace.create(
                    run_root=run_dir,
                    task_id=tid,
                    actor_name=actor.split(":")[0],
                    model=actor,
                    scaffold_dir=task.scaffold_dir,
                )

                act = create_actor(actor, timeout=timeout)

                initial_prompt = builder.build(
                    task_metadata=task.metadata.model_dump(),
                    scaffold_dir=task.scaffold_dir,
                    require_generator=True,
                    repair_mode=not no_repair,
                    baseline_mode=no_repair,
                    output_mode="api" if actor.split(":", 1)[0].lower() in ("openai", "deepseek") else "cli",
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
                    turn_scores.append(
                        {
                            "turn": turn,
                            **_score_to_dict(score),
                            "actor_elapsed_s": result.elapsed_s,
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

                    # Extract clean diagnostics from the Piki critic for the repair prompt
                    piki_result = next(
                        (cr for cr in score.critic_results if cr.name == "piki"), None
                    )
                    diagnostics: list[dict] = []
                    if piki_result and piki_result.artifacts.get("parsed"):
                        for rule in piki_result.artifacts["parsed"].get("results", []):
                            if not rule.get("passed"):
                                diagnostics.append(
                                    {
                                        "rule_id": rule.get("rule_id", ""),
                                        "name": rule.get("name", ""),
                                        "message": rule.get("message", ""),
                                        "file": rule.get("file", ""),
                                    }
                                )
                        for diag in piki_result.artifacts["parsed"].get("diagnostics", []):
                            if str(diag.get("severity", "")).upper() in ("ERROR", "FATAL"):
                                diagnostics.append(
                                    {
                                        "rule_id": diag.get("code", ""),
                                        "name": diag.get("code", ""),
                                        "message": diag.get("message", ""),
                                        "file": diag.get("file", ""),
                                    }
                                )

                    # Build repair prompt for next turn
                    current_prompt = builder.build_repair_turn(
                        task_metadata=task.metadata.model_dump(),
                        project_dir=ws.project_dir,
                        score=score,
                        turn=turn + 1,
                        max_repair=max_repair,
                        diagnostics=diagnostics,
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
