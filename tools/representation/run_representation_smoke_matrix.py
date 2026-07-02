#!/usr/bin/env python3
"""Run no-model representation smoke paths and collect one manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from sd_hwe_bench.representation.adl_openscad import write_reference_adl_project
from sd_hwe_bench.representation.fixture_checker import (
    DEFAULT_FIXTURE_SPEC,
    check_fixture,
    export_openscad,
    metadata_from_spec,
    write_metadata,
)
from sd_hwe_bench.representation.fixture_mcp import FixtureToolSession


def run_openscad_only(out_dir: Path) -> dict[str, Any]:
    path_dir = out_dir / "openscad-only"
    path_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = path_dir / "metadata.json"
    scad_path = path_dir / "design.scad"
    stl_path = path_dir / "design.stl"
    metadata = metadata_from_spec(DEFAULT_FIXTURE_SPEC)
    write_metadata(metadata, metadata_path)
    export_openscad(metadata, scad_path)
    result = check_fixture(
        metadata_path=metadata_path,
        scad_path=scad_path,
        stl_path=stl_path,
        require_openscad=True,
    )
    score_path = path_dir / "score.json"
    score_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
    return {
        "representation_path": "openscad-only",
        "status": "passed" if result.passed else "failed",
        "score": result.score,
        "artifacts": {
            "metadata": str(metadata_path),
            "scad": str(scad_path),
            "score": str(score_path),
            **result.artifacts,
        },
    }


def run_mcp(out_dir: Path) -> dict[str, Any]:
    path_dir = out_dir / "mcp"
    session = FixtureToolSession(path_dir)
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
    return {
        "representation_path": "mcp",
        "status": "passed" if score["passed"] else "failed",
        "score": score["score"],
        "artifacts": {
            "call_log": str(session.log_path),
            "design_state": str(session.state_path),
            "scad": export["path"],
            "score": score["score_path"],
        },
    }


def run_adl_openscad(out_dir: Path) -> dict[str, Any]:
    path_dir = out_dir / "adl-openscad"
    artifacts = write_reference_adl_project(path_dir)
    stl_path = path_dir / "generated" / "design.stl"
    result = check_fixture(
        metadata_path=Path(artifacts["metadata_path"]),
        scad_path=Path(artifacts["scad_path"]),
        stl_path=stl_path,
        require_openscad=True,
    )
    score_path = path_dir / "score.json"
    score_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
    return {
        "representation_path": "adl-openscad",
        "status": "passed" if result.passed else "failed",
        "score": result.score,
        "artifacts": {**artifacts, "score": str(score_path), **result.artifacts},
    }


def run_cua_gui(out_dir: Path, blender: str) -> dict[str, Any]:
    path_dir = out_dir / "cua-gui"
    path_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which(blender) and not Path(blender).exists():
        return {
            "representation_path": "cua",
            "status": "blocked",
            "score": None,
            "note": f"Blender binary not found: {blender}",
            "artifacts": {},
        }
    script = Path(__file__).with_name("blender_gui_smoke.py")
    stl_path = path_dir / "cua_gui_cube.stl"
    command = [
        shutil.which(blender) or blender,
        "--factory-startup",
        "--python",
        str(script),
        "--",
        str(stl_path),
    ]
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    blender_manifest = stl_path.with_suffix(".manifest.json")
    passed = completed.returncode == 0 and stl_path.exists() and stl_path.stat().st_size > 0
    return {
        "representation_path": "cua",
        "status": "gui_passed_visual_actor_not_run" if passed else "failed",
        "score": None,
        "note": (
            "Visible Blender GUI process produced an artifact. This validates the local GUI export "
            "path, but does not yet validate a Kimi Code or Codex visual actor controlling the GUI. "
            "DeepSeek Flash/Pro + Claude Code should be marked not_applicable_no_vision."
        ),
        "artifacts": {
            "stl": str(stl_path),
            "blender_manifest": str(blender_manifest),
            "stdout_tail": completed.stdout[-2000:],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--blender", default="/opt/homebrew/bin/blender")
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="representation-smoke-matrix-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [
        run_mcp(out_dir),
        run_openscad_only(out_dir),
        run_adl_openscad(out_dir),
        run_cua_gui(out_dir, args.blender),
    ]
    manifest = {
        "kind": "representation_smoke_matrix",
        "out_dir": str(out_dir),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "results": results,
    }
    manifest_path = out_dir / "representation_smoke_matrix.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    hard_failures = [
        result
        for result in results
        if result["representation_path"] != "cua" and result["status"] != "passed"
    ]
    cua_failed = [result for result in results if result["representation_path"] == "cua" and result["status"] == "failed"]
    return 1 if hard_failures or cua_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
