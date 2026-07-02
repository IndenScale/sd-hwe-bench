#!/usr/bin/env python3
"""No-model smoke for the fixture MCP-like tool path."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from sd_hwe_bench.representation.fixture_checker import DEFAULT_FIXTURE_SPEC
from sd_hwe_bench.representation.fixture_mcp import FixtureToolSession


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="fixture-mcp-smoke-"))
    session = FixtureToolSession(out_dir)
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
    manifest = {
        "representation_path": "mcp",
        "work_dir": str(out_dir),
        "call_log": str(session.log_path),
        "design_state": str(session.state_path),
        "export": export,
        "score_path": score["score_path"],
        "passed": score["passed"],
        "score": score["score"],
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    manifest_path = out_dir / "mcp_fixture_smoke_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if score["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
