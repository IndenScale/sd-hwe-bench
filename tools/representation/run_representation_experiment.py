#!/usr/bin/env python3
"""Launch representation-gap experiments from a YAML matrix.

The launcher writes one normalized ``manifest.json`` per condition/attempt and
keeps each path's raw artifacts beside it.  It is intentionally small: the
first fixture smoke is about proving that MCP, CUA, OpenSCAD-only, and
ADL+OpenSCAD can all produce re-checkable artifacts before scaling to model
attempts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from sd_hwe_bench.representation.adl_openscad import write_reference_adl_project
from sd_hwe_bench.representation.fixture_checker import (
    DEFAULT_FIXTURE_SPEC,
    check_fixture,
    export_openscad,
    metadata_from_spec,
    write_metadata,
)
from sd_hwe_bench.representation.fixture_mcp import FixtureToolSession

REPO_ROOT = Path(__file__).resolve().parents[2]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_manifest(
    *,
    matrix_path: Path,
    run_dir: Path,
    condition: dict[str, Any],
    attempt: int,
    started: float,
) -> dict[str, Any]:
    return {
        "schema_version": "representation-gap-manifest-v1",
        "experiment": "representation-gap",
        "fixture_id": "single-part-fixture-v0",
        "matrix": _rel(matrix_path),
        "run_dir": _rel(run_dir),
        "condition": condition["name"],
        "representation_path": condition["kind"],
        "actor": condition.get("actor", "no-model"),
        "attempt": attempt,
        "started_at_unix": started,
        "status": "running",
        "success": False,
        "score": None,
        "artifacts": {},
        "metrics": {},
    }


def _finalize(
    manifest: dict[str, Any],
    *,
    status: str,
    success: bool,
    score: float | None = None,
    artifacts: dict[str, str] | None = None,
    metrics: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    elapsed_ms = round((time.perf_counter() - manifest["_perf_started"]) * 1000, 3)
    manifest.pop("_perf_started", None)
    manifest.update(
        {
            "status": status,
            "success": success,
            "score": score,
            "elapsed_ms": elapsed_ms,
            "artifacts": artifacts or {},
            "metrics": metrics or {},
        }
    )
    if notes:
        manifest["notes"] = notes
    return manifest


def run_mcp(out_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    session = FixtureToolSession(out_dir / "workspace")
    spec = DEFAULT_FIXTURE_SPEC
    session.create_fixture_base(spec.length, spec.width, spec.height, spec.material)
    session.add_mounting_holes(
        pattern=[{"x": hole.x, "y": hole.y} for hole in spec.holes],
        diameter=spec.holes[0].diameter,
        countersink=True,
        edge_clearance=spec.min_edge_clearance,
    )
    session.add_clamping_slot(
        width=spec.slot.width,
        depth=spec.slot.depth,
        centerline=spec.slot.centerline_y,
        clearance_rule=spec.slot.clearance_rule,
    )
    session.add_locator_pins(
        count=len(spec.pins),
        diameter=spec.pins[0].diameter,
        positions=[{"x": pin.x, "y": pin.y} for pin in spec.pins],
    )
    export = session.export_openscad()
    score = session.run_checker()
    artifacts = {
        "call_log": _rel(session.log_path),
        "design_state": _rel(session.state_path),
        "scad": _rel(Path(export["path"])),
        "score": _rel(Path(score["score_path"])),
        "stl": _rel(Path(score["artifacts"].get("stl_path", ""))),
    }
    metrics = {
        "deterministic_artifact": True,
        "semantic_source": True,
        "tool_call_log": True,
        "localized_feedback": True,
        "archive_rescore": True,
        "feedback_latency_ms": score["artifacts"].get("elapsed_ms"),
        "invalid_submission": False,
    }
    return _finalize(
        manifest,
        status="passed" if score["passed"] else "failed",
        success=bool(score["passed"]),
        score=float(score["score"]),
        artifacts=artifacts,
        metrics=metrics,
    )


def run_openscad_only(out_dir: Path, manifest: dict[str, Any], openscad_bin: str) -> dict[str, Any]:
    workspace = out_dir / "workspace"
    metadata_path = workspace / "metadata.json"
    scad_path = workspace / "design.scad"
    stl_path = workspace / "design.stl"
    metadata = metadata_from_spec(DEFAULT_FIXTURE_SPEC)
    write_metadata(metadata, metadata_path)
    export_openscad(metadata, scad_path)
    result = check_fixture(
        metadata_path=metadata_path,
        scad_path=scad_path,
        stl_path=stl_path,
        openscad_bin=openscad_bin,
        require_openscad=True,
    )
    score_path = out_dir / "score.json"
    _write_json(score_path, result.to_dict())
    artifacts = {
        "metadata": _rel(metadata_path),
        "scad": _rel(scad_path),
        "stl": _rel(stl_path),
        "score": _rel(score_path),
    }
    metrics = {
        "deterministic_artifact": True,
        "semantic_source": False,
        "tool_call_log": False,
        "localized_feedback": False,
        "archive_rescore": True,
        "feedback_latency_ms": result.artifacts.get("elapsed_ms"),
        "invalid_submission": False,
    }
    return _finalize(
        manifest,
        status="passed" if result.passed else "failed",
        success=result.passed,
        score=result.score,
        artifacts=artifacts,
        metrics=metrics,
    )


def run_adl_openscad(out_dir: Path, manifest: dict[str, Any], openscad_bin: str) -> dict[str, Any]:
    workspace = out_dir / "workspace"
    artifacts_raw = write_reference_adl_project(workspace)
    stl_path = workspace / "generated" / "design.stl"
    result = check_fixture(
        metadata_path=Path(artifacts_raw["metadata_path"]),
        scad_path=Path(artifacts_raw["scad_path"]),
        stl_path=stl_path,
        openscad_bin=openscad_bin,
        require_openscad=True,
    )
    score_path = out_dir / "score.json"
    _write_json(score_path, result.to_dict())
    artifacts = {
        "adl": _rel(Path(artifacts_raw["adl_path"])),
        "mapping": _rel(Path(artifacts_raw["mapping_path"])),
        "metadata": _rel(Path(artifacts_raw["metadata_path"])),
        "scad": _rel(Path(artifacts_raw["scad_path"])),
        "stl": _rel(stl_path),
        "score": _rel(score_path),
    }
    metrics = {
        "deterministic_artifact": True,
        "semantic_source": True,
        "tool_call_log": False,
        "localized_feedback": True,
        "archive_rescore": True,
        "feedback_latency_ms": result.artifacts.get("elapsed_ms"),
        "invalid_submission": False,
    }
    return _finalize(
        manifest,
        status="passed" if result.passed else "failed",
        success=result.passed,
        score=result.score,
        artifacts=artifacts,
        metrics=metrics,
    )


def run_blender_gui(out_dir: Path, manifest: dict[str, Any], blender_bin: str) -> dict[str, Any]:
    workspace = out_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    script = REPO_ROOT / "tools/representation/run_blender_cua_keyboard_smoke.py"
    stl_path = workspace / "cua_keyboard_cube.stl"
    if not shutil.which(blender_bin) and not Path(blender_bin).exists():
        return _finalize(
            manifest,
            status="blocked",
            success=False,
            notes=[f"Blender binary not found: {blender_bin}"],
        )
    command = [
        "uv",
        "run",
        "python",
        str(script),
        "--blender",
        shutil.which(blender_bin) or blender_bin,
        "--out-dir",
        str(workspace),
    ]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    manifest_path = workspace / "blender_cua_keyboard_smoke_manifest.json"
    run_manifest = {}
    if manifest_path.exists():
        try:
            run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            run_manifest = {}
    passed = completed.returncode == 0 and stl_path.exists() and stl_path.stat().st_size > 0
    blocked_reason = run_manifest.get("blocked_reason")
    artifacts = {
        "stl": _rel(stl_path),
        "cua_manifest": _rel(manifest_path),
        "payload_manifest": _rel(stl_path.with_suffix(".manifest.json")),
        "stdout_tail": completed.stdout[-2000:],
    }
    metrics = {
        "deterministic_artifact": False,
        "semantic_source": False,
        "tool_call_log": False,
        "localized_feedback": False,
        "archive_rescore": False,
        "feedback_latency_ms": None,
        "invalid_submission": not passed,
        "visual_gui_process": True,
        "ui_element_interaction": True,
    }
    return _finalize(
        manifest,
        status="passed" if passed else ("blocked" if blocked_reason else "failed"),
        success=passed,
        artifacts=artifacts,
        metrics=metrics,
        notes=(
            ["Visible Blender GUI was driven through keyboard UI interaction."]
            if passed
            else [f"CUA keyboard smoke blocked: {blocked_reason or 'unknown'}"]
        ),
    )


def run_cua_actor(
    out_dir: Path,
    manifest: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    workspace = out_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    prompt = (
        "Run this exact CUA keyboard smoke command and do not edit repository source files: "
        f"uv run python tools/representation/run_blender_cua_keyboard_smoke.py --out-dir {_rel(workspace)}. "
        f"After it finishes, report whether {_rel(workspace / 'cua_keyboard_cube.stl')} exists and is non-empty."
    )
    transcript_path = out_dir / "actor_output.log"
    if actor.startswith("codex:"):
        model = actor.split(":", 1)[1]
        last_message = out_dir / "last-message.txt"
        cmd = [
            "codex",
            "exec",
            "-C",
            str(REPO_ROOT),
            "-m",
            model,
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--output-last-message",
            str(last_message),
            prompt,
        ]
    elif actor.startswith("kimi:"):
        model = actor.split(":", 1)[1]
        cmd = [
            "kimi",
            "-m",
            model,
            "--output-format",
            "text",
            "-p",
            prompt,
        ]
        last_message = None
    else:
        return _finalize(
            manifest,
            status="skipped",
            success=False,
            notes=[f"CUA actor is not visual-capable or not supported by this launcher: {actor}"],
        )

    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    transcript_path.write_text(completed.stdout, encoding="utf-8")
    stl_path = workspace / "cua_keyboard_cube.stl"
    manifest_file = workspace / "blender_cua_keyboard_smoke_manifest.json"
    run_manifest = {}
    if manifest_file.exists():
        try:
            run_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            run_manifest = {}
    passed = completed.returncode == 0 and stl_path.exists() and stl_path.stat().st_size > 0
    blocked_reason = run_manifest.get("blocked_reason")
    artifacts = {
        "stl": _rel(stl_path),
        "blender_manifest": _rel(manifest_file),
        "actor_output": _rel(transcript_path),
    }
    if last_message is not None:
        artifacts["last_message"] = _rel(last_message)
    metrics = {
        "deterministic_artifact": False,
        "semantic_source": False,
        "tool_call_log": True,
        "localized_feedback": False,
        "archive_rescore": False,
        "feedback_latency_ms": None,
        "invalid_submission": not passed,
        "visual_gui_process": True,
        "ui_element_interaction": True,
        "actor_triggered": True,
    }
    return _finalize(
        manifest,
        status="passed" if passed else ("blocked" if blocked_reason else "failed"),
        success=passed,
        artifacts=artifacts,
        metrics=metrics,
        notes=(
            [f"Actor {actor} triggered the GUI smoke command."]
            if passed
            else [f"Actor {actor} CUA keyboard smoke blocked: {blocked_reason or 'unknown'}"]
        ),
    )


def run_condition(
    *,
    matrix_path: Path,
    run_dir: Path,
    condition: dict[str, Any],
    attempt: int,
    openscad_bin: str,
    blender_bin: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    condition_dir = run_dir / condition["name"] / f"attempt-{attempt:03d}"
    started = time.time()
    manifest = _base_manifest(
        matrix_path=matrix_path,
        run_dir=run_dir,
        condition=condition,
        attempt=attempt,
        started=started,
    )
    manifest["_perf_started"] = time.perf_counter()

    if not condition.get("enabled", True):
        manifest = _finalize(
            manifest,
            status="skipped",
            success=False,
            notes=[condition.get("skip_reason", "disabled")],
        )
    elif dry_run:
        manifest = _finalize(manifest, status="dry_run", success=False)
    elif condition["kind"] == "mcp":
        manifest = run_mcp(condition_dir, manifest)
    elif condition["kind"] == "openscad-only":
        manifest = run_openscad_only(condition_dir, manifest, openscad_bin)
    elif condition["kind"] == "adl-openscad":
        manifest = run_adl_openscad(condition_dir, manifest, openscad_bin)
    elif condition["kind"] == "cua-gui":
        manifest = run_blender_gui(condition_dir, manifest, blender_bin)
    elif condition["kind"] == "cua-actor":
        manifest = run_cua_actor(condition_dir, manifest, condition.get("actor", ""))
    else:
        manifest = _finalize(
            manifest,
            status="blocked",
            success=False,
            notes=[f"unknown condition kind: {condition['kind']}"],
        )

    _write_json(condition_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    matrix = yaml.safe_load(args.matrix.read_text(encoding="utf-8"))
    run_dir = args.run_dir or Path(matrix["run_dir"])
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    attempts = int(matrix.get("attempts", 1))
    run_dir.mkdir(parents=True, exist_ok=True)

    manifests: list[dict[str, Any]] = []
    for condition in matrix.get("conditions", []):
        for attempt in range(attempts):
            manifests.append(
                run_condition(
                    matrix_path=args.matrix,
                    run_dir=run_dir,
                    condition=condition,
                    attempt=attempt,
                    openscad_bin=matrix.get("openscad_bin", "openscad"),
                    blender_bin=matrix.get("blender_bin", "/opt/homebrew/bin/blender"),
                    dry_run=args.dry_run,
                )
            )

    summary = {
        "schema_version": "representation-gap-run-summary-v1",
        "matrix": _rel(args.matrix),
        "run_dir": _rel(run_dir),
        "attempts": len(manifests),
        "passed": sum(1 for manifest in manifests if manifest["status"] == "passed"),
        "skipped": sum(1 for manifest in manifests if manifest["status"] == "skipped"),
        "conditions": [manifest["condition"] for manifest in manifests],
    }
    _write_json(run_dir / "run_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    failed = [manifest for manifest in manifests if manifest["status"] == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
