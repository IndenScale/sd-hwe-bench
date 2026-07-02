"""Minimal fixture checker for representation-path experiments.

The first version intentionally checks a small, explicit metadata contract plus
an optional STL bounding box. This keeps OpenSCAD-only, ADL+OpenSCAD, and MCP
conditions on one scoring entrypoint without pretending that STL alone carries
all engineering semantics.
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class HoleSpec:
    x: float
    y: float
    diameter: float
    countersink: bool = True


@dataclass(frozen=True)
class SlotSpec:
    width: float
    depth: float
    centerline_y: float = 0.0
    clearance_rule: str = "object_width_plus_2mm"


@dataclass(frozen=True)
class PinSpec:
    x: float
    y: float
    diameter: float


@dataclass(frozen=True)
class FixtureSpec:
    length: float = 120.0
    width: float = 60.0
    height: float = 12.0
    material: str = "aluminum-6061"
    min_edge_clearance: float = 10.0
    tolerance: float = 0.25
    holes: tuple[HoleSpec, ...] = (
        HoleSpec(-45.0, -15.0, 6.0),
        HoleSpec(45.0, -15.0, 6.0),
        HoleSpec(-45.0, 15.0, 6.0),
        HoleSpec(45.0, 15.0, 6.0),
    )
    slot: SlotSpec = SlotSpec(width=24.0, depth=6.0)
    pins: tuple[PinSpec, ...] = (
        PinSpec(-30.0, 0.0, 4.0),
        PinSpec(30.0, 0.0, 4.0),
    )


DEFAULT_FIXTURE_SPEC = FixtureSpec()


@dataclass
class FixtureCheckResult:
    passed: bool
    score: float
    checks: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "checks": self.checks,
            "artifacts": self.artifacts,
        }


def load_metadata(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Fixture metadata must be a mapping: {path}")
    return data


def write_metadata(metadata: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metadata_from_spec(spec: FixtureSpec = DEFAULT_FIXTURE_SPEC) -> dict[str, Any]:
    return {
        "fixture": {
            "length": spec.length,
            "width": spec.width,
            "height": spec.height,
            "material": spec.material,
        },
        "mounting_holes": [
            {
                "x": hole.x,
                "y": hole.y,
                "diameter": hole.diameter,
                "countersink": hole.countersink,
            }
            for hole in spec.holes
        ],
        "clamping_slot": {
            "width": spec.slot.width,
            "depth": spec.slot.depth,
            "centerline_y": spec.slot.centerline_y,
            "clearance_rule": spec.slot.clearance_rule,
        },
        "locator_pins": [
            {"x": pin.x, "y": pin.y, "diameter": pin.diameter} for pin in spec.pins
        ],
    }


def generate_openscad(metadata: dict[str, Any]) -> str:
    fixture = metadata.get("fixture", {})
    length = float(fixture.get("length", DEFAULT_FIXTURE_SPEC.length))
    width = float(fixture.get("width", DEFAULT_FIXTURE_SPEC.width))
    height = float(fixture.get("height", DEFAULT_FIXTURE_SPEC.height))
    holes = metadata.get("mounting_holes", [])
    slot = metadata.get("clamping_slot", {})
    pins = metadata.get("locator_pins", [])

    lines = [
        "// Generated fixture for PEaC representation experiments.",
        "$fn = 48;",
        "",
        "module fixture_base() {",
        f"  cube([{length:.3f}, {width:.3f}, {height:.3f}], center=true);",
        "}",
        "",
        "module subtractive_features() {",
    ]
    for hole in holes:
        x = float(hole["x"])
        y = float(hole["y"])
        diameter = float(hole["diameter"])
        lines.append(
            f"  translate([{x:.3f}, {y:.3f}, 0]) cylinder(h={height + 2:.3f}, d={diameter:.3f}, center=true);"
        )
        if hole.get("countersink", False):
            lines.append(
                f"  translate([{x:.3f}, {y:.3f}, {height / 2 - 1.0:.3f}]) cylinder(h=2.200, d1={diameter * 1.8:.3f}, d2={diameter:.3f}, center=true);"
            )
    if slot:
        slot_width = float(slot.get("width", 0.0))
        slot_depth = float(slot.get("depth", 0.0))
        centerline_y = float(slot.get("centerline_y", 0.0))
        lines.append(
            f"  translate([0, {centerline_y:.3f}, {height / 2 - slot_depth / 2 + 0.001:.3f}]) cube([{length * 0.62:.3f}, {slot_width:.3f}, {slot_depth + 0.002:.3f}], center=true);"
        )
    lines.extend(
        [
            "}",
            "",
            "module additive_features() {",
        ]
    )
    for pin in pins:
        x = float(pin["x"])
        y = float(pin["y"])
        diameter = float(pin["diameter"])
        lines.append(
            f"  translate([{x:.3f}, {y:.3f}, {height / 2 + 2.0:.3f}]) cylinder(h=4.000, d={diameter:.3f}, center=true);"
        )
    lines.extend(
        [
            "}",
            "",
            "difference() {",
            "  union() {",
            "    fixture_base();",
            "    additive_features();",
            "  }",
            "  subtractive_features();",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def export_openscad(metadata: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_openscad(metadata), encoding="utf-8")


def check_fixture(
    *,
    metadata_path: Path,
    scad_path: Path | None = None,
    stl_path: Path | None = None,
    spec: FixtureSpec = DEFAULT_FIXTURE_SPEC,
    openscad_bin: str = "openscad",
    require_openscad: bool = False,
) -> FixtureCheckResult:
    start = time.perf_counter()
    metadata = load_metadata(metadata_path)
    checks: list[dict[str, Any]] = []
    artifacts: dict[str, Any] = {"metadata_path": str(metadata_path)}

    _check_metadata(metadata, spec, checks)

    if scad_path is not None:
        artifacts["scad_path"] = str(scad_path)
        if scad_path.exists():
            _record(checks, "artifact.scad_exists", True, f"{scad_path} exists")
        else:
            _record(checks, "artifact.scad_exists", False, f"{scad_path} does not exist")

    exported_stl: Path | None = stl_path
    if scad_path is not None and scad_path.exists():
        if require_openscad or shutil.which(openscad_bin):
            exported_stl = stl_path or Path(tempfile.mkdtemp(prefix="fixture-check-")) / "design.stl"
            _run_openscad(scad_path, exported_stl, openscad_bin, checks, artifacts)
        else:
            _record(
                checks,
                "artifact.openscad_available",
                True,
                "OpenSCAD not found; skipped compile because require_openscad=false",
                skipped=True,
            )

    if exported_stl is not None and exported_stl.exists():
        artifacts["stl_path"] = str(exported_stl)
        bbox = read_stl_bbox(exported_stl)
        artifacts["stl_bbox"] = bbox
        if bbox is None:
            _record(checks, "geometry.stl_parseable", False, "STL has no parseable triangles")
        else:
            _record(checks, "geometry.stl_parseable", True, "STL contains parseable triangles")
            _check_bbox(bbox, spec, checks)

    counted = [check for check in checks if not check.get("skipped")]
    passed_count = sum(1 for check in counted if check["passed"])
    score = passed_count / len(counted) if counted else 0.0
    artifacts["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return FixtureCheckResult(
        passed=bool(counted) and passed_count == len(counted),
        score=score,
        checks=checks,
        artifacts=artifacts,
    )


def read_stl_bbox(path: Path) -> dict[str, list[float]] | None:
    data = path.read_bytes()
    vertices: list[tuple[float, float, float]]
    if _looks_like_binary_stl(data):
        vertices = _read_binary_stl_vertices(data)
    else:
        vertices = _read_ascii_stl_vertices(data)
    if not vertices:
        return None
    mins = [min(vertex[i] for vertex in vertices) for i in range(3)]
    maxs = [max(vertex[i] for vertex in vertices) for i in range(3)]
    size = [maxs[i] - mins[i] for i in range(3)]
    return {"min": mins, "max": maxs, "size": size}


def _check_metadata(metadata: dict[str, Any], spec: FixtureSpec, checks: list[dict[str, Any]]) -> None:
    fixture = metadata.get("fixture", {})
    for key, expected in {
        "length": spec.length,
        "width": spec.width,
        "height": spec.height,
    }.items():
        actual = _as_float(fixture.get(key))
        _record(
            checks,
            f"metadata.fixture.{key}",
            actual is not None and _close(actual, expected, spec.tolerance),
            f"{key}: expected {expected}, actual {actual}",
        )
    _record(
        checks,
        "metadata.fixture.material",
        fixture.get("material") == spec.material,
        f"material: expected {spec.material}, actual {fixture.get('material')}",
    )

    holes = metadata.get("mounting_holes", [])
    _record(
        checks,
        "metadata.holes.count",
        isinstance(holes, list) and len(holes) == len(spec.holes),
        f"expected {len(spec.holes)} holes, actual {len(holes) if isinstance(holes, list) else 'invalid'}",
    )
    if isinstance(holes, list):
        for index, expected_hole in enumerate(spec.holes):
            actual = holes[index] if index < len(holes) and isinstance(holes[index], dict) else {}
            _check_feature_position(
                checks,
                f"metadata.holes.{index}",
                actual,
                expected_hole.x,
                expected_hole.y,
                expected_hole.diameter,
                spec,
            )
            edge_clearance = _hole_edge_clearance(actual, spec)
            _record(
                checks,
                f"metadata.holes.{index}.edge_clearance",
                edge_clearance is not None and edge_clearance >= spec.min_edge_clearance,
                f"edge clearance: expected >= {spec.min_edge_clearance}, actual {edge_clearance}",
            )

    slot = metadata.get("clamping_slot", {})
    _record(checks, "metadata.slot.exists", isinstance(slot, dict), "clamping_slot must be a mapping")
    if isinstance(slot, dict):
        for key, expected in {
            "width": spec.slot.width,
            "depth": spec.slot.depth,
            "centerline_y": spec.slot.centerline_y,
        }.items():
            actual = _as_float(slot.get(key))
            _record(
                checks,
                f"metadata.slot.{key}",
                actual is not None and _close(actual, expected, spec.tolerance),
                f"{key}: expected {expected}, actual {actual}",
            )
        _record(
            checks,
            "metadata.slot.clearance_rule",
            slot.get("clearance_rule") == spec.slot.clearance_rule,
            f"clearance_rule: expected {spec.slot.clearance_rule}, actual {slot.get('clearance_rule')}",
        )

    pins = metadata.get("locator_pins", [])
    _record(
        checks,
        "metadata.pins.count",
        isinstance(pins, list) and len(pins) == len(spec.pins),
        f"expected {len(spec.pins)} pins, actual {len(pins) if isinstance(pins, list) else 'invalid'}",
    )
    if isinstance(pins, list):
        for index, expected_pin in enumerate(spec.pins):
            actual = pins[index] if index < len(pins) and isinstance(pins[index], dict) else {}
            _check_feature_position(
                checks,
                f"metadata.pins.{index}",
                actual,
                expected_pin.x,
                expected_pin.y,
                expected_pin.diameter,
                spec,
            )


def _check_feature_position(
    checks: list[dict[str, Any]],
    prefix: str,
    actual: dict[str, Any],
    expected_x: float,
    expected_y: float,
    expected_diameter: float,
    spec: FixtureSpec,
) -> None:
    for key, expected in {
        "x": expected_x,
        "y": expected_y,
        "diameter": expected_diameter,
    }.items():
        actual_value = _as_float(actual.get(key))
        _record(
            checks,
            f"{prefix}.{key}",
            actual_value is not None and _close(actual_value, expected, spec.tolerance),
            f"{key}: expected {expected}, actual {actual_value}",
        )


def _check_bbox(bbox: dict[str, list[float]], spec: FixtureSpec, checks: list[dict[str, Any]]) -> None:
    size = bbox["size"]
    expected = [spec.length, spec.width, spec.height]
    # Pins add height above the base; the base dimensions remain checked through metadata.
    names = ["length", "width"]
    for index, name in enumerate(names):
        _record(
            checks,
            f"geometry.bbox.{name}",
            _close(size[index], expected[index], max(spec.tolerance, 0.5)),
            f"{name}: expected {expected[index]}, actual {size[index]}",
        )
    _record(
        checks,
        "geometry.bbox.height_at_least_base",
        size[2] >= spec.height - spec.tolerance,
        f"height: expected >= {spec.height}, actual {size[2]}",
    )


def _run_openscad(
    scad_path: Path,
    stl_path: Path,
    openscad_bin: str,
    checks: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> None:
    if not shutil.which(openscad_bin):
        _record(checks, "artifact.openscad_available", False, f"{openscad_bin} not found")
        return
    version = subprocess.run(
        [openscad_bin, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    ).stdout.strip()
    artifacts["openscad_version"] = version
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [openscad_bin, "-o", str(stl_path), str(scad_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    artifacts["openscad_output"] = completed.stdout[-4000:]
    _record(
        checks,
        "artifact.openscad_compile",
        completed.returncode == 0 and stl_path.exists() and stl_path.stat().st_size > 0,
        f"openscad exit={completed.returncode}, stl_size={stl_path.stat().st_size if stl_path.exists() else 0}",
    )


def _hole_edge_clearance(hole: dict[str, Any], spec: FixtureSpec) -> float | None:
    x = _as_float(hole.get("x"))
    y = _as_float(hole.get("y"))
    diameter = _as_float(hole.get("diameter"))
    if x is None or y is None or diameter is None:
        return None
    radius = diameter / 2
    return min(
        spec.length / 2 - abs(x) - radius,
        spec.width / 2 - abs(y) - radius,
    )


def _looks_like_binary_stl(data: bytes) -> bool:
    if len(data) < 84:
        return False
    triangle_count = struct.unpack("<I", data[80:84])[0]
    return 84 + triangle_count * 50 == len(data)


def _read_binary_stl_vertices(data: bytes) -> list[tuple[float, float, float]]:
    triangle_count = struct.unpack("<I", data[80:84])[0]
    vertices: list[tuple[float, float, float]] = []
    offset = 84
    for _ in range(triangle_count):
        chunk = data[offset : offset + 50]
        if len(chunk) < 50:
            break
        values = struct.unpack("<12fH", chunk)
        vertices.extend((values[i], values[i + 1], values[i + 2]) for i in (3, 6, 9))
        offset += 50
    return vertices


def _read_ascii_stl_vertices(data: bytes) -> list[tuple[float, float, float]]:
    vertices = []
    for raw_line in data.decode("utf-8", errors="ignore").splitlines():
        parts = raw_line.strip().split()
        if len(parts) == 4 and parts[0] == "vertex":
            try:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError:
                continue
    return vertices


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def _record(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    message: str,
    *,
    skipped: bool = False,
) -> None:
    checks.append(
        {
            "id": check_id,
            "passed": passed,
            "message": message,
            "skipped": skipped,
        }
    )
