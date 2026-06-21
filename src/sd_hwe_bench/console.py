"""Rich console and score printing utilities for the CLI."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from sd_hwe_bench.scorer import TaskScore

console = Console()


def print_score(score: TaskScore) -> None:
    """Render a TaskScore to the console."""
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
