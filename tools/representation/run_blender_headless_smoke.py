#!/usr/bin/env python3
"""Run the Blender headless smoke and write a JSON manifest."""

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
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="blender-smoke-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    output_stl = out_dir / "cube.stl"
    manifest_path = out_dir / "blender_headless_smoke_manifest.json"
    script_path = Path(__file__).with_name("blender_headless_smoke.py")

    blender_path = shutil.which(args.blender) or args.blender
    command = [
        blender_path,
        "--background",
        "--factory-startup",
        "--python",
        str(script_path),
        "--",
        str(output_stl),
    ]
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    manifest = {
        "tool": "blender",
        "command": command,
        "returncode": completed.returncode,
        "output_path": str(output_stl),
        "output_bytes": output_stl.stat().st_size if output_stl.exists() else 0,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout_tail": completed.stdout[-4000:],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if completed.returncode != 0 or manifest["output_bytes"] <= 0:
        print(json.dumps(manifest, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
