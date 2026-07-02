#!/usr/bin/env python3
"""Run OpenSCAD CLI smoke and write a JSON manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", default="openscad")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="openscad-smoke-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    scad_path = Path(__file__).with_name("openscad_smoke.scad")
    stl_path = out_dir / "openscad_smoke.stl"
    manifest_path = out_dir / "openscad_smoke_manifest.json"
    openscad_path = shutil.which(args.openscad) or args.openscad

    version = subprocess.run(
        [openscad_path, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    completed = subprocess.run(
        [openscad_path, "-o", str(stl_path), str(scad_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    manifest = {
        "tool": "openscad",
        "version": version.stdout.strip(),
        "command": [openscad_path, "-o", str(stl_path), str(scad_path)],
        "returncode": completed.returncode,
        "input_path": str(scad_path),
        "output_path": str(stl_path),
        "output_bytes": stl_path.stat().st_size if stl_path.exists() else 0,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout_tail": (version.stdout + completed.stdout)[-4000:],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if version.returncode != 0 or completed.returncode != 0 or manifest["output_bytes"] <= 0:
        print(json.dumps(manifest, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
