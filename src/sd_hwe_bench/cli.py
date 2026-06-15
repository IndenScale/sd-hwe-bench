"""Typer CLI entry point for SD-HWE-Bench."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from sd_hwe_bench.actors import create_actor
from sd_hwe_bench.archive.leaderboard import LeaderboardBuilder
from sd_hwe_bench.archive.manager import ArchiveManager
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.prompts import PromptBuilder
from sd_hwe_bench.sandbox.runner import SandboxBackend, SandboxRunner
from sd_hwe_bench.sandbox.workspace import Workspace
from sd_hwe_bench.scorer import TaskScore, compute_pass_at_k, score_task

app = typer.Typer(
    name="sd-hwe-bench",
    help="SD-HWE-Bench: evaluate AI agents on declarative hardware engineering tasks.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _resolve_task_ids(dataset: Dataset, task_id: Optional[str]) -> list[str]:
    all_ids = dataset.discover()
    if not task_id:
        return all_ids
    matched = [tid for tid in all_ids if tid == task_id or tid.startswith(task_id)]
    if not matched:
        for tid in all_ids:
            task = dataset.load_task(tid)
            if task_id in task.metadata.name:
                matched.append(tid)
    return matched if matched else [task_id]


@app.command("list")
def list_tasks(
    dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
    domain: Optional[str] = typer.Option(None, "--domain", help="Filter by domain."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """List available benchmark tasks."""
    _setup_logging(verbose)
    ds = Dataset(dataset)
    task_ids = ds.discover()

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
        "none", "--sandbox", help="Sandbox backend for piki execution."
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
    _setup_logging(verbose)

    ds = Dataset(dataset)
    task_ids = _resolve_task_ids(ds, task_id)
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
            console.print(f"\n[bold]Running {actor} on {tid} (attempt {attempt + 1}/{passes})...[/bold]")

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
            _print_score(score)

        all_scores.append(task_scores)

    if len(all_scores) > 1 or passes > 1:
        console.print(f"\n[bold]Pass@1: {compute_pass_at_k(all_scores, k=1):.0%}[/bold]")


@app.command("score")
def score_command(
    task_id: str = typer.Argument(..., help="Task ID."),
    output: Path = typer.Argument(..., help="Path to agent output directory (workspace)."),
    dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
    sandbox: SandboxBackend = typer.Option(
        "none", "--sandbox", help="Sandbox backend for piki execution."
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
    _setup_logging(verbose)

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
    )
    _print_score(score)


def _print_score(score: TaskScore) -> None:
    status = "[green]PASS[/green]" if score.success else "[red]FAIL[/red]"
    console.print(f"\n{status} {score.task_id} — overall score: {score.overall_score:.2%}")

    table = Table(title="Layer Breakdown")
    table.add_column("Layer", style="cyan")
    table.add_column("Passed", style="green")
    table.add_column("Errors", style="red")

    for layer in ["L0", "L1", "L2", "L3", "L4"]:
        ls = score.layers.get(layer)
        if not ls:
            continue
        err_text = "; ".join(ls.errors[:3]) if ls.errors else "—"
        table.add_row(layer, f"{ls.passed}/{ls.total}", err_text)

    console.print(table)

    if score.deliverable_scores:
        console.print("\n[bold]Deliverables:[/bold]")
        for name, ok in score.deliverable_scores.items():
            icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
            console.print(f"  {icon} {name}")

    if score.rubric_score is not None:
        console.print(f"\n[bold]Rubric score: {score.rubric_score:.2%}[/bold]")

    if score.critic_results:
        console.print("\n[bold]Review Comments:[/bold]")
        for cr in score.critic_results:
            icon = "[green]✓[/green]" if cr.passed else "[red]✗[/red]"
            console.print(f"\n{icon} [bold]{cr.name}[/bold] ({cr.score:.0%})")
            for comment in cr.comments[:5]:
                console.print(f"  • {comment}")


@app.command("archive")
def archive_command(
    run_dir: Path = typer.Option(Path("runs"), "--run-dir", help="Rollout archive root."),
    format: str = typer.Option("markdown", "--format", help="Output format: json or markdown."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """List and summarize rollout archives."""
    _setup_logging(verbose)

    manager = ArchiveManager(run_dir)
    summary = manager.summarize()

    if format == "json":
        import json
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


@app.command("leaderboard")
def leaderboard_command(
    run_dir: Path = typer.Option(Path("runs"), "--run-dir", help="Rollout archive root."),
    output: Path = typer.Option(
        Path("leaderboard"), "--output", help="Leaderboard output directory."
    ),
    update: bool = typer.Option(False, "--update", help="Write leaderboard files."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """Generate leaderboard from rollout archives."""
    _setup_logging(verbose)

    manager = ArchiveManager(run_dir)
    builder = LeaderboardBuilder(manager)
    board = builder.build()

    if update:
        output.mkdir(parents=True, exist_ok=True)
        board.save(output / "results.json", output / "results.md")
        console.print(f"[green]Leaderboard saved to {output}[/green]")

    console.print(board.to_markdown())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
