"""Tests for workspace and sandbox modules."""

import tempfile
from pathlib import Path

import pytest

from sd_hwe_bench.sandbox.parser import YamlBlockParser
from sd_hwe_bench.sandbox.workspace import Workspace


class TestWorkspace:
    def test_create_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            scaffold = Path(td) / "scaffold"
            scaffold.mkdir()
            (scaffold / "piki.toml").write_text("[project]\nname = 'test'\n")

            ws = Workspace.create(
                run_root=Path(td) / "runs",
                task_id="telecom/test-001",
                actor_name="kimi",
                scaffold_dir=scaffold,
            )

            assert ws.project_dir.exists()
            assert (ws.project_dir / "piki.toml").exists()
            assert ws.manifest_path.exists()
            assert ws.read_manifest()["task_id"] == "telecom/test-001"

    def test_write_prompt_and_trajectory(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace.create(
                run_root=Path(td) / "runs",
                task_id="telecom/test-001",
                actor_name="kimi",
            )
            ws.write_prompt("test prompt")
            assert ws.prompt_path.read_text() == "test prompt"

            ws.log_trajectory({"event": "test"})
            lines = ws.trajectory_path.read_text().strip().split("\n")
            assert len(lines) == 1
            assert '"event": "test"' in lines[0]


class TestYamlBlockParser:
    def test_parse_with_path_comments(self):
        with tempfile.TemporaryDirectory() as td:
            text = """
```yaml
# instances/devices/SRV-01.yaml
id: SRV-01
model: generic-server
```
"""
            parser = YamlBlockParser(Path(td))
            written, errors = parser.parse_and_write(text)
            assert written == 1
            assert not errors
            assert (Path(td) / "instances" / "devices" / "SRV-01.yaml").exists()

    def test_parse_without_path_comments(self):
        with tempfile.TemporaryDirectory() as td:
            text = """
```yaml
id: SRV-01
model: generic-server
height_u: 2
tdp_w: 300
```
"""
            parser = YamlBlockParser(Path(td))
            written, errors = parser.parse_and_write(text)
            assert written == 1
            assert not errors
            assert (Path(td) / "instances" / "devices" / "SRV-01.yaml").exists()

    def test_parse_layout_list(self):
        with tempfile.TemporaryDirectory() as td:
            text = """
```yaml
# layouts/layout.yaml
- instance: SRV-01
  rack: RACK-A01
  ru_position: 10
```
"""
            parser = YamlBlockParser(Path(td))
            written, errors = parser.parse_and_write(text)
            assert written == 1
            assert (Path(td) / "layouts" / "layout.yaml").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
