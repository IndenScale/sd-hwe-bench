from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sd_hwe_bench.representation.adl_openscad import write_reference_adl_project
from sd_hwe_bench.representation.fixture_checker import (
    DEFAULT_FIXTURE_SPEC,
    check_fixture,
    export_openscad,
    metadata_from_spec,
    read_stl_bbox,
    write_metadata,
)
from sd_hwe_bench.representation.fixture_mcp import FixtureToolSession


def test_fixture_checker_accepts_reference_metadata_and_scad(tmp_path: Path):
    metadata = metadata_from_spec(DEFAULT_FIXTURE_SPEC)
    metadata_path = tmp_path / "metadata.json"
    scad_path = tmp_path / "design.scad"

    write_metadata(metadata, metadata_path)
    export_openscad(metadata, scad_path)

    result = check_fixture(metadata_path=metadata_path, scad_path=scad_path)

    assert result.passed
    assert result.score == 1.0
    assert any(check["id"] == "metadata.holes.0.edge_clearance" for check in result.checks)
    assert scad_path.read_text(encoding="utf-8").startswith("// Generated fixture")


def test_fixture_checker_rejects_pseudo_correct_mirrored_hole(tmp_path: Path):
    metadata = metadata_from_spec(DEFAULT_FIXTURE_SPEC)
    metadata["mounting_holes"][0]["x"] = 45.0
    metadata_path = tmp_path / "metadata.json"
    write_metadata(metadata, metadata_path)

    result = check_fixture(metadata_path=metadata_path)

    assert not result.passed
    failed = {check["id"] for check in result.checks if not check["passed"]}
    assert "metadata.holes.0.x" in failed


def test_ascii_stl_bbox_parser(tmp_path: Path):
    stl_path = tmp_path / "cube.stl"
    stl_path.write_text(
        """solid cube
facet normal 0 0 1
outer loop
vertex -1 -2 0
vertex 3 -2 0
vertex 3 4 5
endloop
endfacet
endsolid cube
""",
        encoding="utf-8",
    )

    bbox = read_stl_bbox(stl_path)

    assert bbox == {"min": [-1.0, -2.0, 0.0], "max": [3.0, 4.0, 5.0], "size": [4.0, 6.0, 5.0]}


def test_fixture_tool_session_writes_auditable_artifacts(tmp_path: Path):
    session = FixtureToolSession(tmp_path)
    session.reset_to_reference()
    export = session.export_openscad()
    score = session.run_checker()

    assert Path(export["path"]).exists()
    assert score["passed"]
    assert session.state_path.exists()
    log_lines = session.log_path.read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(line)["tool"] for line in log_lines] == [
        "reset_to_reference",
        "export_openscad",
        "run_checker",
    ]


def test_adl_openscad_smoke_writes_semantic_source_and_mapping(tmp_path: Path):
    artifacts = write_reference_adl_project(tmp_path)

    result = check_fixture(
        metadata_path=Path(artifacts["metadata_path"]),
        scad_path=Path(artifacts["scad_path"]),
    )

    assert result.passed
    assert Path(artifacts["adl_path"]).exists()
    mapping = json.loads(Path(artifacts["mapping_path"]).read_text(encoding="utf-8"))
    assert mapping["mounting_holes"] == "mounting_interface.fields.holes"


def test_json_stdio_fixture_server_smoke(tmp_path: Path):
    server = Path("src/sd_hwe_bench/representation/mcp_server.py")
    proc = subprocess.Popen(
        [sys.executable, str(server), "--work-dir", str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    requests = [
        {"tool": "reset_to_reference", "arguments": {}},
        {"tool": "export_openscad", "arguments": {}},
        {"tool": "run_checker", "arguments": {}},
    ]
    responses = []
    for request in requests:
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        responses.append(json.loads(proc.stdout.readline()))
    proc.stdin.close()
    proc.wait(timeout=5)

    assert proc.returncode == 0
    assert all(response["ok"] for response in responses)
    assert responses[-1]["result"]["passed"]
