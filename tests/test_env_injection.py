"""Tests for sandbox environment-variable injection."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sd_hwe_bench.cli_common import build_env_vars, load_env_file
from sd_hwe_bench.sandbox.runner import SandboxRunner
from sd_hwe_bench.settings import settings


class TestLoadEnvFile:
    def test_loads_simple_key_values(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "test.env"
            env_path.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")
            assert load_env_file(env_path) == {"FOO": "bar", "BAZ": "qux"}

    def test_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "test.env"
            env_path.write_text("# comment\n\nKEY=value\n  # indented comment\n", encoding="utf-8")
            assert load_env_file(env_path) == {"KEY": "value"}

    def test_strips_quotes(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "test.env"
            env_path.write_text("DOUBLE=\"quoted\"\nSINGLE='quoted'\n", encoding="utf-8")
            assert load_env_file(env_path) == {
                "DOUBLE": "quoted",
                "SINGLE": "quoted",
            }

    def test_missing_file_returns_empty_dict(self):
        assert load_env_file(Path("/nonexistent/env.file")) == {}


class TestBuildEnvVars:
    def test_env_options_take_precedence_over_file(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "test.env"
            env_path.write_text("KEY=file\nOTHER=keep\n", encoding="utf-8")
            result = build_env_vars(
                env_options=["KEY=override"],
                env_file=env_path,
            )
            assert result == {"KEY": "override", "OTHER": "keep"}

    def test_invalid_env_option_raises(self):
        with pytest.raises(ValueError):
            build_env_vars(env_options=["NO_EQUALS"])


class TestSandboxRunnerEnvInjection:
    def test_host_mode_merges_env_vars(self):
        runner = SandboxRunner(
            backend="none",
            env_vars={"SD_HWE_BENCH_TEST": "injected"},
        )
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td)
            (project_dir / "piki.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
            with patch("sd_hwe_bench.sandbox.runner.SandboxRunner._resolve_python") as mock_resolve:
                mock_resolve.return_value = "python"
                with patch("sd_hwe_bench.sandbox.runner.subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = "{}"
                    mock_run.return_value.stderr = ""
                    runner.check(project_dir)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"]["SD_HWE_BENCH_TEST"] == "injected"

    def test_container_command_includes_env_flags(self):
        runner = SandboxRunner(
            backend="docker",
            env_vars={"KEY1": "value1", "KEY2": "value2"},
        )
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td)
            with patch("sd_hwe_bench.sandbox.runner.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "{}"
                mock_run.return_value.stderr = ""
                runner.check(project_dir)

        cmd = mock_run.call_args.args[0]
        assert "-e" in cmd
        assert "KEY1=value1" in cmd
        assert "KEY2=value2" in cmd
        # Ensure env vars appear after the workspace mount and before the image.
        mount_idx = cmd.index("-v")
        key1_idx = cmd.index("KEY1=value1")
        image_idx = cmd.index(settings.DEFAULT_SANDBOX_IMAGE)
        assert mount_idx < key1_idx < image_idx
