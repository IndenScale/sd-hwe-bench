"""Stateful fixture tool core used by the representation MCP smoke path."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from sd_hwe_bench.representation.fixture_checker import (
    DEFAULT_FIXTURE_SPEC,
    check_fixture,
    export_openscad,
    metadata_from_spec,
    write_metadata,
)


class FixtureToolSession:
    """Small auditable tool session for the fixture representation task."""

    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.export_dir = work_dir / "exported"
        self.state_path = work_dir / "design_state.json"
        self.log_path = work_dir / "mcp_call_log.jsonl"
        self.state: dict[str, Any] = {}
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def create_fixture_base(
        self, length: float, width: float, height: float, material: str = "aluminum-6061"
    ) -> dict[str, Any]:
        self.state["fixture"] = {
            "length": length,
            "width": width,
            "height": height,
            "material": material,
        }
        return self._finish("create_fixture_base", locals())

    def add_mounting_holes(
        self,
        pattern: list[dict[str, Any]] | None = None,
        diameter: float = 6.0,
        countersink: bool = True,
        edge_clearance: float = 10.0,
    ) -> dict[str, Any]:
        if pattern is None:
            pattern = [{"x": hole.x, "y": hole.y} for hole in DEFAULT_FIXTURE_SPEC.holes]
        self.state["mounting_holes"] = [
            {
                "x": float(item["x"]),
                "y": float(item["y"]),
                "diameter": diameter,
                "countersink": countersink,
                "edge_clearance": edge_clearance,
            }
            for item in pattern
        ]
        return self._finish("add_mounting_holes", locals())

    def add_clamping_slot(
        self,
        width: float,
        depth: float,
        centerline: float = 0.0,
        clearance_rule: str = "object_width_plus_2mm",
    ) -> dict[str, Any]:
        self.state["clamping_slot"] = {
            "width": width,
            "depth": depth,
            "centerline_y": centerline,
            "clearance_rule": clearance_rule,
        }
        return self._finish("add_clamping_slot", locals())

    def add_locator_pins(
        self,
        count: int = 2,
        diameter: float = 4.0,
        positions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if positions is None:
            positions = [{"x": pin.x, "y": pin.y} for pin in DEFAULT_FIXTURE_SPEC.pins[:count]]
        self.state["locator_pins"] = [
            {"x": float(item["x"]), "y": float(item["y"]), "diameter": diameter}
            for item in positions[:count]
        ]
        return self._finish("add_locator_pins", locals())

    def reset_to_reference(self) -> dict[str, Any]:
        self.state = metadata_from_spec()
        return self._finish("reset_to_reference", {})

    def export_openscad(self, path: str | None = None) -> dict[str, Any]:
        if path is None:
            output_path = self.export_dir / "design.scad"
        else:
            output_path = Path(path)
        if path is not None and not output_path.is_absolute():
            output_path = self.work_dir / output_path
        export_openscad(self.state, output_path)
        self._write_state()
        result = {"path": str(output_path), "bytes": output_path.stat().st_size}
        self._append_log("export_openscad", {"path": path}, result)
        return result

    def run_checker(self, path: str | None = None, stl_path: str | None = None) -> dict[str, Any]:
        if path is None:
            scad_path = self.export_dir / "design.scad"
        else:
            scad_path = Path(path)
        if path is not None and not scad_path.is_absolute():
            scad_path = self.work_dir / scad_path
        if stl_path is None:
            output_stl_path = self.export_dir / "design.stl"
        else:
            output_stl_path = Path(stl_path)
        if stl_path is not None and not output_stl_path.is_absolute():
            output_stl_path = self.work_dir / output_stl_path
        self._write_state()
        score_path = self.work_dir / "score.json"
        result = check_fixture(
            metadata_path=self.state_path,
            scad_path=scad_path,
            stl_path=output_stl_path,
        )
        score_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
        payload = {"score_path": str(score_path), **result.to_dict()}
        self._append_log("run_checker", {"path": path, "stl_path": stl_path}, payload)
        return payload

    def dispatch(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        if not hasattr(self, tool) or tool.startswith("_"):
            raise ValueError(f"Unknown fixture tool: {tool}")
        method = getattr(self, tool)
        return method(**arguments)

    def _finish(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        arguments = {key: value for key, value in arguments.items() if key != "self"}
        self._write_state()
        result = {"state_path": str(self.state_path), "state": self.state}
        self._append_log(tool, arguments, result)
        return result

    def _write_state(self) -> None:
        write_metadata(self.state, self.state_path)

    def _append_log(self, tool: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "ts": time.time(),
                        "tool": tool,
                        "arguments": arguments,
                        "result": result,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
