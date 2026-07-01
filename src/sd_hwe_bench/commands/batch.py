"""Batch-run a model × task matrix of rollouts, then aggregate a leaderboard.

Replaces the per-experiment ``scripts/*_batch.py`` wrappers (which hardcoded an
absolute repo path, a task list, a model map, and a brittle stdout parser) with
a single matrix-driven command that reuses the tested ``run`` command and the
existing leaderboard aggregation.

Matrix YAML schema::

    run_dir: runs/pass5-2026xxxx     # archive root (shared across models)
    passes: 5                        # passes per (model, task)
    sandbox: none                    # auto/none/docker/podman
    timeout: 600                     # actor timeout (s)
    max_workers: 4                   # concurrent (model, task) rollouts
    provider_max_workers:            # optional provider-level concurrency caps
      deepseek: 1
      kimi: 1
      codex: 1
    self_check: false                # append --no-self-check when false
    command: run                     # run or run-repair
    context_mode: full               # full, docs-only, nl-only (run-repair only)
    diagnostic_verbosity: localized  # none, coarse, attributed, localized (run-repair only)
    constraint_coverage_mode: full    # full, explicit-mute, random-mute (run-repair only)
    prompt_mute: family:layout        # optional selector list/string
    feedback_mute: layer:L5           # optional selector list/string
    mute_ratio: 0.25                  # for random-mute
    mute_seed: 42                     # for random-mute
    no_repair: false                 # pass --no-repair to run-repair
    max_repair: 5                    # repair rounds for run-repair
    conditions:                      # optional per-condition overrides
      - name: executable
        command: run-repair
        context_mode: full
        no_repair: false
    models:                          # name -> actor spec
      kimi: kimi
      deepseek-v4-flash: claude:deepseek-v4-flash
    tasks:                           # ids / prefixes / globs, expanded via dataset
      - telecom/aidc-*
      - telecom/comprehensive-001
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
import threading
from collections import defaultdict, deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

import typer
import yaml

from sd_hwe_bench.archive.leaderboard import LeaderboardBuilder
from sd_hwe_bench.archive.manager import ArchiveManager
from sd_hwe_bench.cli_common import resolve_task_ids, setup_logging
from sd_hwe_bench.console import console
from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.settings import settings

_BATCH_COMMANDS = {"run", "run-repair"}
_CONTEXT_MODES = {"full", "docs-only", "nl-only"}
_DIAGNOSTIC_VERBOSITIES = {"none", "coarse", "attributed", "localized"}
_CONSTRAINT_COVERAGE_MODES = {"full", "explicit-mute", "random-mute"}


def load_matrix(path: Path) -> dict[str, Any]:
    """Load and validate a batch matrix file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("matrix file must be a YAML mapping")
    if not data.get("models"):
        raise ValueError("matrix must define a non-empty 'models' map")
    if not data.get("tasks"):
        raise ValueError("matrix must define a non-empty 'tasks' list")
    return data


def expand_tasks(ds: Dataset, entries: list[str]) -> list[str]:
    """Expand task entries (ids / prefixes / globs) to a de-duplicated id list."""
    all_ids = ds.discover()
    resolved: list[str] = []
    for entry in entries:
        if any(ch in entry for ch in "*?["):
            matched = [tid for tid in all_ids if fnmatch.fnmatch(tid, entry)]
        else:
            matched = resolve_task_ids(ds, entry)
        for tid in matched:
            if tid not in resolved:
                resolved.append(tid)
    return resolved


def load_conditions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized condition entries for a matrix."""
    raw_conditions = data.get("conditions")
    if raw_conditions is None:
        raw_conditions = [{"name": data.get("condition", "default")}]
    if not isinstance(raw_conditions, list) or not raw_conditions:
        raise ValueError("matrix 'conditions' must be a non-empty list when provided")

    conditions: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_conditions):
        if not isinstance(raw, dict):
            raise ValueError("each condition must be a YAML mapping")
        name = str(raw.get("name", f"condition-{idx + 1}"))
        command = str(raw.get("command", data.get("command", "run")))
        context_mode = str(raw.get("context_mode", data.get("context_mode", "full")))
        diagnostic_verbosity = str(
            raw.get("diagnostic_verbosity", data.get("diagnostic_verbosity", "localized"))
        )
        constraint_coverage_mode = str(
            raw.get("constraint_coverage_mode", data.get("constraint_coverage_mode", "full"))
        )
        if command not in _BATCH_COMMANDS:
            raise ValueError(f"unsupported batch command: {command}")
        if context_mode not in _CONTEXT_MODES:
            raise ValueError(f"unsupported context_mode: {context_mode}")
        if diagnostic_verbosity not in _DIAGNOSTIC_VERBOSITIES:
            raise ValueError(f"unsupported diagnostic_verbosity: {diagnostic_verbosity}")
        if constraint_coverage_mode not in _CONSTRAINT_COVERAGE_MODES:
            raise ValueError(f"unsupported constraint_coverage_mode: {constraint_coverage_mode}")
        conditions.append(
            {
                "name": name,
                "command": command,
                "context_mode": context_mode,
                "diagnostic_verbosity": diagnostic_verbosity,
                "constraint_coverage_mode": constraint_coverage_mode,
                "prompt_mute": raw.get("prompt_mute", data.get("prompt_mute", "")),
                "feedback_mute": raw.get("feedback_mute", data.get("feedback_mute", "")),
                "mute_ratio": float(raw.get("mute_ratio", data.get("mute_ratio", 0.0))),
                "mute_seed": raw.get("mute_seed", data.get("mute_seed")),
                "no_repair": bool(raw.get("no_repair", data.get("no_repair", False))),
                "max_repair": int(raw.get("max_repair", data.get("max_repair", settings.DEFAULT_MAX_REPAIR))),
            }
        )
    return conditions


def _safe_condition_name(name: str) -> str:
    """Make a condition name safe for a run subdirectory."""
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


def _selector_arg(value: Any) -> str:
    """Normalize selector strings/lists from YAML for CLI forwarding."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def _complete_manifest(manifest: dict[str, Any]) -> bool:
    """A complete run has passed through scoring/final manifest update."""
    if manifest.get("termination_reason") == "actor_error":
        return False
    if "success" not in manifest:
        return False
    turn_scores = manifest.get("turn_scores")
    if isinstance(turn_scores, list) and turn_scores:
        return True
    layers = manifest.get("layers")
    if isinstance(layers, dict) and layers:
        return True
    deliverables = manifest.get("deliverables")
    return isinstance(deliverables, dict) and bool(deliverables)


def _completed_attempts(run_dir: Path, condition_name: str, actor_spec: str, task_id: str) -> int:
    """Count complete attempts already present for a condition/model/task."""
    condition_dir = run_dir / _safe_condition_name(condition_name)
    if not condition_dir.exists():
        return 0

    completed = 0
    for path in condition_dir.rglob("manifest.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not _complete_manifest(manifest):
            continue
        if manifest.get("task_id") != task_id:
            continue
        if manifest.get("model") != actor_spec:
            continue
        completed += 1
    return completed


def _provider_for_actor_spec(actor_spec: str) -> str:
    """Return the rate-limit/provider bucket for an actor spec."""
    driver, _, model = actor_spec.partition(":")
    driver = driver.lower()
    model = model.lower()
    if driver == "claude" and model.startswith("deepseek"):
        return "deepseek"
    return driver


def _load_provider_max_workers(raw: Any) -> dict[str, int]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("provider_max_workers must be a YAML mapping")
    caps: dict[str, int] = {}
    for provider, value in raw.items():
        cap = int(value)
        if cap <= 0:
            raise ValueError("provider_max_workers values must be positive integers")
        caps[str(provider).lower()] = cap
    return caps


def _interleave_plan_by_provider(
    plan: list[tuple[dict[str, Any], str, str, str, int, int]],
) -> list[tuple[dict[str, Any], str, str, str, int, int]]:
    """Round-robin the plan across provider buckets.

    The raw matrix order groups all tasks for one model before the next model.
    Interleaving prevents a global worker pool from initially filling with a
    single provider when independent providers could run concurrently.
    """
    buckets: dict[str, deque[tuple[dict[str, Any], str, str, str, int, int]]] = defaultdict(deque)
    provider_order: list[str] = []
    for item in plan:
        provider = _provider_for_actor_spec(item[2])
        if provider not in buckets:
            provider_order.append(provider)
        buckets[provider].append(item)

    interleaved: list[tuple[dict[str, Any], str, str, str, int, int]] = []
    while any(buckets.values()):
        for provider in provider_order:
            if buckets[provider]:
                interleaved.append(buckets[provider].popleft())
    return interleaved


def register(app: typer.Typer) -> None:
    @app.command("batch")
    def batch_command(
        matrix: Path = typer.Option(..., "--matrix", help="Path to batch matrix YAML."),
        dataset: Path = typer.Option(Path("."), "--dataset", help="Path to dataset root."),
        dry_run: bool = typer.Option(
            False, "--dry-run", help="Print the (model, task) plan and exit; do not run actors."
        ),
        resume: bool = typer.Option(
            False,
            "--resume",
            help="Skip complete existing attempts and run only missing passes.",
        ),
        max_workers: int = typer.Option(
            settings.MAX_AUTO_JOBS, "--max-workers", help="Concurrent (model, task) rollouts."
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    ) -> None:
        """Run a model × task matrix of rollouts, then build a leaderboard."""
        setup_logging(verbose)

        data = load_matrix(matrix)
        models: dict[str, str] = dict(data["models"])
        conditions = load_conditions(data)
        ds = Dataset(dataset)
        task_ids = expand_tasks(ds, list(data["tasks"]))
        if not task_ids:
            console.print("[red]No tasks matched the matrix 'tasks' patterns.[/red]")
            raise typer.Exit(code=1)

        passes = int(data.get("passes", settings.DEFAULT_PASSES))
        sandbox = str(data.get("sandbox", settings.DEFAULT_SANDBOX_BACKEND))
        timeout = int(data.get("timeout", settings.DEFAULT_ACTOR_TIMEOUT_S))
        run_dir = str(data.get("run_dir", settings.RUN_DIR))
        workers = int(data.get("max_workers", max_workers))
        provider_caps = _load_provider_max_workers(data.get("provider_max_workers"))
        self_check = bool(data.get("self_check", True))

        raw_plan = [
            (condition, name, spec, tid)
            for condition in conditions
            for name, spec in models.items()
            for tid in task_ids
        ]
        plan: list[tuple[dict[str, Any], str, str, str, int, int]] = []
        skipped_entries = 0
        for condition, name, spec, tid in raw_plan:
            completed = (
                _completed_attempts(Path(run_dir), condition["name"], spec, tid) if resume else 0
            )
            remaining = max(0, passes - completed)
            if remaining == 0:
                skipped_entries += 1
                continue
            plan.append((condition, name, spec, tid, remaining, completed))
        plan = _interleave_plan_by_provider(plan)

        total_attempts = sum(remaining for *_prefix, remaining, _completed in plan)
        provider_summary = (
            " | provider_max_workers="
            + ", ".join(f"{k}:{v}" for k, v in sorted(provider_caps.items()))
            if provider_caps
            else ""
        )
        console.print(
            f"[bold]Batch plan:[/bold] {len(conditions)} conditions × "
            f"{len(models)} models × {len(task_ids)} tasks "
            f"= {len(plan)} task-model entries | attempts={total_attempts} "
            f"| passes={passes} | sandbox={sandbox} | self_check={self_check} "
            f"| resume={resume} | skipped={skipped_entries}{provider_summary} | run_dir={run_dir}"
        )
        for condition, name, spec, tid, remaining, completed in plan:
            console.print(
                f"  - {condition['name']}:{condition['command']} "
                f"{name} ({spec})  {tid}"
                f" remaining={remaining}, complete={completed}/{passes}"
            )

        if dry_run:
            return

        def _one(
            condition: dict[str, Any],
            model_name: str,
            actor_spec: str,
            task_id: str,
            pass_count: int,
        ) -> tuple[str, str, str, int]:
            condition_run_dir = str(Path(run_dir) / _safe_condition_name(condition["name"]))
            cmd = [
                sys.executable, "-m", "sd_hwe_bench.cli", condition["command"], task_id,
                "--actor", actor_spec,
                "--passes", str(pass_count),
                "--run-dir", condition_run_dir,
                "--sandbox", sandbox,
                "--timeout", str(timeout),
                "--dataset", str(dataset),
            ]
            if condition["command"] == "run" and not self_check:
                cmd.append("--no-self-check")
            if condition["command"] == "run-repair":
                cmd.extend(["--max-repair", str(condition["max_repair"])])
                cmd.extend(["--context-mode", condition["context_mode"]])
                cmd.extend(["--diagnostic-verbosity", condition["diagnostic_verbosity"]])
                cmd.extend(["--constraint-coverage-mode", condition["constraint_coverage_mode"]])
                if condition.get("prompt_mute"):
                    cmd.extend(["--prompt-mute", _selector_arg(condition["prompt_mute"])])
                if condition.get("feedback_mute"):
                    cmd.extend(["--feedback-mute", _selector_arg(condition["feedback_mute"])])
                if condition.get("mute_ratio"):
                    cmd.extend(["--mute-ratio", str(condition["mute_ratio"])])
                if condition.get("mute_seed") is not None:
                    cmd.extend(["--mute-seed", str(condition["mute_seed"])])
                if condition["no_repair"]:
                    cmd.append("--no-repair")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return condition["name"], model_name, task_id, proc.returncode

        failures = 0
        provider_running: dict[str, int] = defaultdict(int)
        pending = deque(plan)
        futures: dict[Any, tuple[str, str, str, str]] = {}
        lock = threading.Lock()

        def _submit_ready(ex: ThreadPoolExecutor) -> None:
            made_progress = True
            while pending and len(futures) < workers and made_progress:
                made_progress = False
                for _ in range(len(pending)):
                    condition, name, spec, tid, remaining, _completed = pending[0]
                    provider = _provider_for_actor_spec(spec)
                    cap = provider_caps.get(provider)
                    if cap is not None and provider_running[provider] >= cap:
                        pending.rotate(-1)
                        continue
                    pending.popleft()
                    provider_running[provider] += 1
                    fut = ex.submit(_one, condition, name, spec, tid, remaining)
                    futures[fut] = (condition["name"], name, tid, provider)
                    made_progress = True
                    break

        with ThreadPoolExecutor(max_workers=workers) as ex:
            _submit_ready(ex)
            while futures:
                done_futures, _pending_futures = wait(futures, return_when=FIRST_COMPLETED)
                for fut in done_futures:
                    condition_name, name, tid, provider = futures.pop(fut)
                    with lock:
                        provider_running[provider] -= 1
                    condition_name, name, tid, rc = fut.result()
                    ok = rc == 0
                    if not ok:
                        failures += 1
                    color = "green" if ok else "red"
                    console.print(
                        f"  [{color}]{'ok' if ok else 'FAIL'}[/{color}] "
                        f"{condition_name} {name} {tid} (rc={rc})"
                    )
                _submit_ready(ex)

        # Aggregate leaderboard from the shared run_dir manifests.
        manager = ArchiveManager(Path(run_dir))
        board = LeaderboardBuilder(manager).build()
        console.print(board.to_markdown())

        if failures:
            console.print(f"[yellow]{failures}/{len(plan)} rollouts returned non-zero.[/yellow]")
            raise typer.Exit(code=1)
