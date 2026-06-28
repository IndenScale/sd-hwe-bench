"""Tests for centralized settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from sd_hwe_bench.settings import CONFIG_DIR, Settings, settings


class TestSettingsDefaults:
    def test_default_actor_timeout_is_positive(self):
        assert settings.DEFAULT_ACTOR_TIMEOUT_S > 0

    def test_default_sandbox_image(self):
        assert settings.DEFAULT_SANDBOX_IMAGE == "sd-hwe-bench-piki:latest"

    def test_layer_weights_sum_sensible(self):
        non_gate = sum(w for k, w in settings.LAYER_WEIGHTS.items() if k != "L0")
        assert non_gate == pytest.approx(1.0)
        assert settings.LAYER_WEIGHTS["L0"] == 0.0

    def test_default_run_dir_is_relative_runs(self):
        assert settings.RUN_DIR == Path("runs")

    def test_config_files_exist(self):
        assert CONFIG_DIR.exists()
        assert (CONFIG_DIR / "rule_layers.yaml").exists()
        assert (CONFIG_DIR / "deliverables.yaml").exists()


class TestSettingsEnvOverride:
    def test_env_overrides_default_actor_timeout(self, monkeypatch):
        monkeypatch.setenv("SD_HWE_ACTOR_TIMEOUT_S", "1234")
        fresh = Settings()
        assert fresh.DEFAULT_ACTOR_TIMEOUT_S == 1234

    def test_env_overrides_default_sandbox_image(self, monkeypatch):
        monkeypatch.setenv("SD_HWE_SANDBOX_IMAGE", "custom/image:tag")
        fresh = Settings()
        assert fresh.DEFAULT_SANDBOX_IMAGE == "custom/image:tag"

    def test_env_overrides_layer_weights(self, monkeypatch):
        monkeypatch.setenv("SD_HWE_LAYER_WEIGHTS", '{"L1": 0.2, "L2": 0.3}')
        fresh = Settings()
        assert fresh.LAYER_WEIGHTS["L1"] == 0.2

    def test_invalid_int_env_raises(self, monkeypatch):
        monkeypatch.setenv("SD_HWE_ACTOR_TIMEOUT_S", "not-an-int")
        with pytest.raises(ValueError):
            Settings()

    def test_piki_python_env_resolution(self, monkeypatch):
        monkeypatch.setenv("SD_HWE_PIKI_PYTHON", "/tmp/custom-python")
        fresh = Settings()
        assert fresh.PIKI_PYTHON == "/tmp/custom-python"

    def test_pikipath_legacy_env_still_supported(self, monkeypatch):
        monkeypatch.setenv("PIPKIPATH", "/tmp/pikipath-python")
        fresh = Settings()
        assert fresh.PIKI_PYTHON == "/tmp/pikipath-python"


class TestRuleLayersConfig:
    def test_exact_rule_layers_loaded(self):
        config = settings.RULE_LAYERS_CONFIG
        assert "exact" in config
        assert config["exact"]["SCHEMA-001"] == "L1"

    def test_prefixes_loaded(self):
        config = settings.RULE_LAYERS_CONFIG
        prefixes = {entry["prefix"] for entry in config["prefixes"]}
        assert "SCHEMA-" in prefixes


class TestDeliverablesConfig:
    def test_deliverables_loaded(self):
        config = settings.DELIVERABLES_CONFIG
        assert "bom-csv" in config
        assert config["bom-csv"]["filename_pattern"] == "bom.csv"
