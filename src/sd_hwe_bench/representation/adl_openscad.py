"""Tiny semantic ADL-to-OpenSCAD bridge for representation smoke tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from sd_hwe_bench.representation.fixture_checker import (
    DEFAULT_FIXTURE_SPEC,
    export_openscad,
    metadata_from_spec,
    write_metadata,
)


def reference_adl_document() -> dict[str, Any]:
    """Return a minimal semantic fixture document with object/field identities."""
    metadata = metadata_from_spec(DEFAULT_FIXTURE_SPEC)
    return {
        "adl_version": "fixture-smoke-v0",
        "project": {"id": "representation-fixture-smoke", "phase": "single-part-fixture"},
        "objects": {
            "fixture_base": {
                "kind": "part",
                "role": "structural_base",
                "fields": metadata["fixture"],
            },
            "mounting_interface": {
                "kind": "interface",
                "role": "machine_table_mount",
                "fields": {"holes": metadata["mounting_holes"]},
            },
            "clamping_interface": {
                "kind": "interface",
                "role": "workpiece_clamp",
                "fields": {"slot": metadata["clamping_slot"]},
            },
            "locator_interface": {
                "kind": "interface",
                "role": "repeatable_positioning",
                "fields": {"pins": metadata["locator_pins"]},
            },
        },
        "constraints": [
            {
                "id": "fixture.base.dimensions",
                "target": "fixture_base.fields",
                "source": "fixture-smoke-spec",
            },
            {
                "id": "fixture.mounting.edge_clearance",
                "target": "mounting_interface.fields.holes",
                "source": "manufacturing-rule:min-edge-clearance",
            },
            {
                "id": "fixture.clamping.clearance",
                "target": "clamping_interface.fields.slot",
                "source": "workpiece-interface",
            },
        ],
    }


def adl_to_fixture_metadata(adl_doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    objects = adl_doc.get("objects", {})
    metadata = {
        "fixture": objects["fixture_base"]["fields"],
        "mounting_holes": objects["mounting_interface"]["fields"]["holes"],
        "clamping_slot": objects["clamping_interface"]["fields"]["slot"],
        "locator_pins": objects["locator_interface"]["fields"]["pins"],
    }
    mapping = {
        "fixture.length": "fixture_base.fields.length",
        "fixture.width": "fixture_base.fields.width",
        "fixture.height": "fixture_base.fields.height",
        "fixture.material": "fixture_base.fields.material",
        "mounting_holes": "mounting_interface.fields.holes",
        "clamping_slot": "clamping_interface.fields.slot",
        "locator_pins": "locator_interface.fields.pins",
        "generated_scad_modules": {
            "fixture_base": "fixture_base",
            "subtractive_features": "mounting_interface + clamping_interface",
            "additive_features": "locator_interface",
        },
    }
    return metadata, mapping


def write_reference_adl_project(out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    adl_path = out_dir / "design.adl.yaml"
    metadata_path = out_dir / "design.metadata.json"
    scad_path = out_dir / "generated" / "design.scad"
    mapping_path = out_dir / "adl_to_scad_map.json"

    adl_doc = reference_adl_document()
    metadata, mapping = adl_to_fixture_metadata(adl_doc)
    adl_path.write_text(yaml.safe_dump(adl_doc, sort_keys=False), encoding="utf-8")
    write_metadata(metadata, metadata_path)
    export_openscad(metadata, scad_path)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "adl_path": str(adl_path),
        "metadata_path": str(metadata_path),
        "scad_path": str(scad_path),
        "mapping_path": str(mapping_path),
    }
