"""Minimal stdio server for fixture representation smoke tests.

This module exposes the same tool surface planned for the MCP condition while
keeping the core testable without installing an MCP SDK. Each stdin line is a
JSON object: {"tool": "...", "arguments": {...}}. Each stdout line is a JSON
response. A future Python MCP SDK wrapper can call FixtureToolSession directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sd_hwe_bench.representation.fixture_mcp import FixtureToolSession


def handle_line(session: FixtureToolSession, line: str) -> dict[str, Any]:
    request = json.loads(line)
    tool = request.get("tool")
    if not isinstance(tool, str):
        raise ValueError("request.tool must be a string")
    arguments = request.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise ValueError("request.arguments must be a mapping")
    return session.dispatch(tool, arguments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    session = FixtureToolSession(args.work_dir)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            result = {"ok": True, "result": handle_line(session, line)}
        except Exception as exc:  # pragma: no cover - exercised by subprocess smoke
            result = {"ok": False, "error": str(exc)}
        print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
