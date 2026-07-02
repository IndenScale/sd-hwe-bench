#!/usr/bin/env python3
"""Run a visible Blender CUA smoke through keyboard-driven UI interaction.

This launcher intentionally does not pass ``--python`` to Blender. It opens a
normal Blender window, dismisses the splash screen, switches to the Python
Console via a keyboard shortcut, pastes a one-line command through the system
clipboard, and presses Return. The pasted command exports an STL and writes a
manifest before quitting Blender.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _run_osascript(source: str) -> None:
    completed = subprocess.run(
        ["osascript", "-e", source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip())


def _paste_python_console_command(command: str) -> None:
    subprocess.run(["pbcopy"], input=command, text=True, check=True)
    script = """
tell application "Blender" to activate
delay 0.5
tell application "System Events"
  key code 53
  delay 0.4
  key code 118 using {shift down}
  delay 0.8
  keystroke "v" using {command down}
  delay 0.2
  key code 36
end tell
"""
    _run_osascript(script)


def _stop_blender_process(proc: subprocess.Popen[str]) -> str:
    stdout = ""
    if proc.poll() is None:
        subprocess.run(["pkill", "-x", "Blender"], check=False)
        proc.terminate()
    try:
        stdout, _stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            stdout, _stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            subprocess.run(["pkill", "-9", "-x", "Blender"], check=False)
            stdout = ""
    return stdout or ""


def _console_payload(output_stl: Path) -> str:
    code = f"""
import bpy, json, time
from pathlib import Path
out = Path({str(output_stl)!r})
out.parent.mkdir(parents=True, exist_ok=True)
if not bpy.data.objects:
    bpy.ops.mesh.primitive_cube_add(size=20, location=(0, 0, 10))
bpy.ops.object.select_all(action='SELECT')
for obj in bpy.context.selected_objects:
    obj.name = 'cua_keyboard_smoke_cube'
bpy.ops.wm.stl_export(filepath=str(out))
manifest = {{
    'tool': 'blender',
    'mode': 'cua-keyboard',
    'ui_interaction': 'keyboard_shortcut_python_console',
    'version': bpy.app.version_string,
    'background': bpy.app.background,
    'output_path': str(out),
    'output_bytes': out.stat().st_size if out.exists() else 0,
    'created_at_unix': time.time(),
}}
out.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\\n')
bpy.ops.wm.quit_blender()
"""
    return "exec(" + repr(code) + ")"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", default="/opt/homebrew/bin/blender")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = args.out_dir or Path(tempfile.mkdtemp(prefix="blender-cua-keyboard-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    output_stl = out_dir / "cua_keyboard_cube.stl"
    run_manifest_path = out_dir / "blender_cua_keyboard_smoke_manifest.json"

    blender_path = shutil.which(args.blender) or args.blender
    command = [blender_path, "--factory-startup"]
    proc = subprocess.Popen(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout = ""
    automation_error: str | None = None
    try:
        time.sleep(3.0)
        _paste_python_console_command(_console_payload(output_stl))
        stdout, _stderr = proc.communicate(timeout=args.timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout = _stop_blender_process(proc)
    except Exception as exc:
        automation_error = str(exc)
        stdout = _stop_blender_process(proc)
        stdout = (stdout or "") + f"\n[CUA_AUTOMATION_ERROR] {automation_error}"
        timed_out = False

    returncode = proc.returncode
    payload_manifest = output_stl.with_suffix(".manifest.json")
    blocked_reason = None
    if automation_error and (
        "不允许发送按键" in automation_error
        or "not allowed to send keystrokes" in automation_error.lower()
    ):
        blocked_reason = "accessibility_permission_denied"
    manifest = {
        "tool": "blender",
        "mode": "cua-keyboard",
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "output_path": str(output_stl),
        "output_bytes": output_stl.stat().st_size if output_stl.exists() else 0,
        "payload_manifest": str(payload_manifest),
        "payload_manifest_exists": payload_manifest.exists(),
        "blocked_reason": blocked_reason,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout_tail": (stdout or "")[-4000:],
    }
    run_manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if timed_out or manifest["output_bytes"] <= 0 or not payload_manifest.exists():
        print(json.dumps(manifest, indent=2, sort_keys=True), file=sys.stderr)
        return 2 if blocked_reason else 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
