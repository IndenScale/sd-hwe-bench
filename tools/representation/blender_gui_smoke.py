#!/usr/bin/env python3
"""Blender GUI smoke script for CUA representation experiments.

Run through Blender without --background:
  blender --factory-startup --python blender_gui_smoke.py -- /tmp/gui_fixture.stl
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def _output_path(argv: list[str]) -> Path:
    if "--" in argv:
        tail = argv[argv.index("--") + 1 :]
    else:
        tail = argv[1:]
    if not tail:
        raise SystemExit("usage: blender --factory-startup --python blender_gui_smoke.py -- OUT.stl")
    return Path(tail[0])


def main() -> None:
    started = time.perf_counter()
    output_path = _output_path(sys.argv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import bpy  # type: ignore

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cube_add(size=20, location=(0, 0, 10))
    cube = bpy.context.object
    cube.name = "cua_gui_smoke_cube"
    bpy.ops.wm.stl_export(filepath=str(output_path))

    manifest = {
        "tool": "blender",
        "mode": "gui",
        "version": bpy.app.version_string,
        "background": bpy.app.background,
        "output_path": str(output_path),
        "output_bytes": output_path.stat().st_size if output_path.exists() else 0,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    output_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise SystemExit("Blender GUI smoke did not produce a non-empty STL")
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    main()
