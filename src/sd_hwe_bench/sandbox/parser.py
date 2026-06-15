"""Parse YAML code blocks from agent responses and write them into a workspace."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class YamlBlockParser:
    """Extract ```yaml ... ``` blocks and write them to disk."""

    # Matches ```yaml ... ``` blocks (non-greedy)
    BLOCK_RE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)

    def parse_and_write(self, text: str) -> tuple[int, list[str]]:
        """Parse all YAML blocks in text and write them to project_dir.

        Returns (files_written, errors).
        """
        blocks = list(self.BLOCK_RE.finditer(text))
        written = 0
        errors: list[str] = []

        for match in blocks:
            block = match.group(1).strip()
            if not block:
                continue

            filepath, yaml_content, err = self._extract_block(block)
            if err:
                errors.append(err)
                continue
            if not filepath:
                errors.append("Could not determine file path for a YAML block")
                continue

            try:
                fpath = self.project_dir / filepath
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(yaml_content, encoding="utf-8")
                written += 1
            except Exception as exc:
                errors.append(f"Failed to write {filepath}: {exc}")

        return written, errors

    def _extract_block(self, block: str) -> tuple[str | None, str, str | None]:
        """Extract (filepath, yaml_content, error) from one YAML block."""
        lines = block.split("\n")

        # First line can be a file path comment
        if lines and lines[0].strip().startswith("#"):
            filepath = lines[0].lstrip("#").strip()
            yaml_content = "\n".join(lines[1:]).strip()
            if filepath:
                return filepath, yaml_content, None

        # No path comment: infer from content
        yaml_content = block
        inferred = self._infer_path(block)
        if inferred:
            return inferred, yaml_content, None

        return None, yaml_content, None

    def _infer_path(self, content: str) -> str | None:
        """Infer file path from YAML content heuristics."""
        id_match = re.search(r"^id:\s*(\S+)", content, re.MULTILINE)
        if not id_match:
            # Maybe a layout list
            if content.strip().startswith("-"):
                return "layouts/layout.yaml"
            return None

        yaml_id = id_match.group(1)

        if "mate:" in content:
            mate_m = re.search(r"mate:\s*(\S+)", content)
            mate_type = mate_m.group(1) if mate_m else "unknown"
            return f"mates/{mate_type}/{yaml_id}.yaml"

        if "rack:" in content or "ru_position:" in content or "position_u:" in content:
            if yaml_id == "layout" or content.strip().startswith("-"):
                return "layouts/layout.yaml"
            return f"instances/racks/{yaml_id}.yaml"

        if "from_port:" in content or "to_port:" in content:
            if "fiber_type:" in content:
                return f"instances/fibers/{yaml_id}.yaml"
            return f"instances/port_connections/{yaml_id}.yaml"

        if "port_type:" in content or ("port_name:" in content and "device_id:" in content):
            return f"instances/ports/{yaml_id}.yaml"

        if "interface" in content or "tdp_w:" in content or "height_u:" in content:
            return f"instances/devices/{yaml_id}.yaml"

        if "capacity_w:" in content or "phase:" in content:
            return f"instances/pdus/{yaml_id}.yaml"

        if "model:" in content and ("sfp" in yaml_id.lower() or "transceiver" in yaml_id.lower()):
            return f"instances/transceivers/{yaml_id}.yaml"

        return f"instances/{yaml_id}.yaml"
