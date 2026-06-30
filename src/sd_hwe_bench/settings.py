"""Centralized settings for SD-HWE-Bench.

All magic numbers and hardcoded defaults live here. Each value can be
overridden via an environment variable prefixed with ``SD_HWE_``.
Credentials (API keys) are intentionally **not** stored here; only the
environment variable names or file paths used to retrieve them are configured.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a float, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_json(name: str, default: Any) -> Any:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Environment variable {name} must be valid JSON, got {raw!r}") from exc


def _resolve_llm_judge_model() -> str:
    """Default judge model: env override, then DeepSeek if key present, else GPT."""
    env_model = os.environ.get("SD_HWE_LLM_JUDGE_MODEL")
    if env_model:
        return env_model
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek-chat"
    return "gpt-4.1-mini"


# Path to the bundled YAML config files (rule_layers.yaml, deliverables.yaml, ...)
CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _load_yaml_config(name: str) -> Any:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing bundled config file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    # ------------------------------------------------------------------
    # General CLI / workflow defaults
    # ------------------------------------------------------------------
    DEFAULT_ACTOR: str = field(default_factory=lambda: _env_str("SD_HWE_DEFAULT_ACTOR", "kimi"))
    DEFAULT_PASSES: int = field(default_factory=lambda: _env_int("SD_HWE_DEFAULT_PASSES", 1))
    MAX_AUTO_JOBS: int = field(default_factory=lambda: _env_int("SD_HWE_MAX_AUTO_JOBS", 4))
    RUN_DIR: Path = field(default_factory=lambda: Path(_env_str("SD_HWE_RUN_DIR", "runs")))
    LEADERBOARD_DIR: Path = field(
        default_factory=lambda: Path(_env_str("SD_HWE_LEADERBOARD_DIR", "leaderboard"))
    )
    DEFAULT_ACTOR_TIMEOUT_S: int = field(
        default_factory=lambda: _env_int("SD_HWE_ACTOR_TIMEOUT_S", 600)
    )
    DEFAULT_MAX_REPAIR: int = field(
        default_factory=lambda: _env_int("SD_HWE_DEFAULT_MAX_REPAIR", 20)
    )
    LOG_PREVIEW_CHARS: int = field(
        default_factory=lambda: _env_int("SD_HWE_LOG_PREVIEW_CHARS", 2000)
    )

    # ------------------------------------------------------------------
    # Sandbox / container
    # ------------------------------------------------------------------
    DEFAULT_SANDBOX_BACKEND: str = field(
        default_factory=lambda: _env_str("SD_HWE_SANDBOX_BACKEND", "auto")
    )
    DEFAULT_SANDBOX_IMAGE: str = field(
        default_factory=lambda: _env_str("SD_HWE_SANDBOX_IMAGE", "sd-hwe-bench-piki:latest")
    )
    CONTAINER_WORKDIR: str = field(
        default_factory=lambda: _env_str("SD_HWE_CONTAINER_WORKDIR", "/work")
    )
    PIKI_TIMEOUT_S: int = field(default_factory=lambda: _env_int("SD_HWE_PIKI_TIMEOUT_S", 120))
    CONTAINER_TIMEOUT_S: int = field(
        default_factory=lambda: _env_int("SD_HWE_CONTAINER_TIMEOUT_S", 180)
    )
    PIKI_PYTHON: str | None = field(
        default_factory=lambda: os.environ.get("SD_HWE_PIKI_PYTHON") or os.environ.get("PIPKIPATH")
    )

    # ------------------------------------------------------------------
    # Actor defaults
    # ------------------------------------------------------------------
    KIMI_BIN: str = field(default_factory=lambda: _env_str("SD_HWE_KIMI_BIN", "kimi"))
    DEFAULT_KIMI_MODEL: str = field(
        default_factory=lambda: _env_str("SD_HWE_KIMI_MODEL", "kimi-code/kimi-for-coding")
    )

    CLAUDE_BIN: str = field(default_factory=lambda: _env_str("SD_HWE_CLAUDE_BIN", "claude"))
    DEFAULT_CLAUDE_MODEL: str = field(
        default_factory=lambda: _env_str("SD_HWE_CLAUDE_MODEL", "deepseek-v4-flash")
    )
    CLAUDE_EFFORT_LEVEL: str = field(
        default_factory=lambda: _env_str("SD_HWE_CLAUDE_EFFORT_LEVEL", "max")
    )
    CLAUDE_BASE_URL: str = field(
        default_factory=lambda: _env_str(
            "SD_HWE_CLAUDE_BASE_URL", "https://api.deepseek.com/anthropic"
        )
    )
    CLAUDE_DEFAULT_OPUS_MODEL: str = field(
        default_factory=lambda: _env_str(
            "SD_HWE_CLAUDE_DEFAULT_OPUS_MODEL", "deepseek-v4-pro[1m]"
        )
    )
    CLAUDE_DEFAULT_SONNET_MODEL: str = field(
        default_factory=lambda: _env_str(
            "SD_HWE_CLAUDE_DEFAULT_SONNET_MODEL", "deepseek-v4-pro[1m]"
        )
    )
    CLAUDE_DEFAULT_HAIKU_MODEL: str = field(
        default_factory=lambda: _env_str("SD_HWE_CLAUDE_DEFAULT_HAIKU_MODEL", "deepseek-v4-flash")
    )
    CLAUDE_EXTRA_ARGS: list[str] = field(
        default_factory=lambda: _env_list(
            "SD_HWE_CLAUDE_EXTRA_ARGS",
            ["--permission-mode", "bypassPermissions"],
        )
    )

    CODEX_BIN: str = field(default_factory=lambda: _env_str("SD_HWE_CODEX_BIN", "codex"))
    DEFAULT_CODEX_MODEL: str = field(
        default_factory=lambda: _env_str("SD_HWE_CODEX_MODEL", "deepseek-chat")
    )
    CODEX_EXTRA_ARGS: list[str] = field(
        default_factory=lambda: _env_list(
            "SD_HWE_CODEX_EXTRA_ARGS",
            ["--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox"],
        )
    )

    OPENAI_BASE_URL: str = field(
        default_factory=lambda: _env_str("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    )
    DEFAULT_OPENAI_MODEL: str = field(
        default_factory=lambda: _env_str("SD_HWE_OPENAI_MODEL", "deepseek-chat")
    )
    OPENAI_API_KEY_ENV: str = field(
        default_factory=lambda: _env_str("SD_HWE_OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
    )
    OPENAI_TEMPERATURE: float = field(
        default_factory=lambda: _env_float("SD_HWE_OPENAI_TEMPERATURE", 0.0)
    )
    OPENAI_MAX_TOKENS: int = field(
        default_factory=lambda: _env_int("SD_HWE_OPENAI_MAX_TOKENS", 8192)
    )
    SYSTEM_PROMPT: str | None = field(
        default_factory=lambda: os.environ.get("SD_HWE_SYSTEM_PROMPT")
    )

    # ------------------------------------------------------------------
    # LLM judge
    # ------------------------------------------------------------------
    LLM_JUDGE_TIMEOUT_S: int = field(
        default_factory=lambda: _env_int("SD_HWE_LLM_JUDGE_TIMEOUT_S", 120)
    )
    LLM_JUDGE_MODEL: str = field(default_factory=_resolve_llm_judge_model)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    LAYER_WEIGHTS: dict[str, float] = field(
        default_factory=lambda: _env_json(
            "SD_HWE_LAYER_WEIGHTS",
            {
                # L0-L5: unified QA layers. L6 reserved for future FEM/CFD.
                "L0": 0.0,
                "L1": 0.10,
                "L2": 0.15,
                "L3": 0.40,
                "L4": 0.15,
                "L5": 0.20,
                "L6": 0.0,
            },
        )
    )
    DELIVERABLE_WEIGHT: float = field(
        default_factory=lambda: _env_float("SD_HWE_DELIVERABLE_WEIGHT", 0.0)
    )
    RUBRIC_WEIGHT: float = field(default_factory=lambda: _env_float("SD_HWE_RUBRIC_WEIGHT", 0.0))
    CRITICAL_LAYERS: list[str] = field(
        default_factory=lambda: _env_list("SD_HWE_CRITICAL_LAYERS", ["L0", "L1", "L2", "L3", "L4", "L5"])
    )
    SYNTAX_PENALTY_PER_ERROR: float = field(
        default_factory=lambda: _env_float("SD_HWE_SYNTAX_PENALTY_PER_ERROR", 0.1)
    )
    PIKI_CRITIC_MAX_ERRORS: int = field(
        default_factory=lambda: _env_int("SD_HWE_PIKI_CRITIC_MAX_ERRORS", 5)
    )
    DEFAULT_RUBRIC_THRESHOLD: float = field(
        default_factory=lambda: _env_float("SD_HWE_DEFAULT_RUBRIC_THRESHOLD", 0.6)
    )
    DEFAULT_PLUGINS: list[str] = field(
        default_factory=lambda: _env_list("SD_HWE_DEFAULT_PLUGINS", ["telecom"])
    )
    DEFAULT_SCORING_LAYERS: list[str] = field(
        default_factory=lambda: _env_list("SD_HWE_DEFAULT_SCORING_LAYERS", ["L0", "L1", "L2", "L3"])
    )

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------
    SCAFFOLD_INLINE_MAX_BYTES: int = field(
        default_factory=lambda: _env_int("SD_HWE_SCAFFOLD_INLINE_MAX_BYTES", 4096)
    )
    REPAIR_PROMPT_MAX_DIAGNOSTICS: int = field(
        default_factory=lambda: _env_int("SD_HWE_REPAIR_PROMPT_MAX_DIAGNOSTICS", 20)
    )
    REPAIR_PROMPT_MAX_ERRORS_PER_LAYER: int = field(
        default_factory=lambda: _env_int("SD_HWE_REPAIR_PROMPT_MAX_ERRORS_PER_LAYER", 10)
    )

    # ------------------------------------------------------------------
    # Console / reporting
    # ------------------------------------------------------------------
    CONSOLE_MAX_ERRORS: int = field(
        default_factory=lambda: _env_int("SD_HWE_CONSOLE_MAX_ERRORS", 3)
    )
    CONSOLE_MAX_COMMENTS: int = field(
        default_factory=lambda: _env_int("SD_HWE_CONSOLE_MAX_COMMENTS", 5)
    )

    # ------------------------------------------------------------------
    # Self-check hook
    # ------------------------------------------------------------------
    SELF_CHECK_ENABLED: bool = field(
        default_factory=lambda: _env_bool("SD_HWE_SELF_CHECK_ENABLED", True)
    )
    SELF_CHECK_MAX_ROUNDS: int = field(
        default_factory=lambda: _env_int("SD_HWE_SELF_CHECK_MAX_ROUNDS", 3)
    )

    # ------------------------------------------------------------------
    # Bundled YAML config accessors
    # ------------------------------------------------------------------
    @property
    def RULE_LAYERS_CONFIG(self) -> dict[str, Any]:
        return _load_yaml_config("rule_layers.yaml")

    @property
    def DELIVERABLES_CONFIG(self) -> dict[str, Any]:
        return _load_yaml_config("deliverables.yaml")


    # Diagnostic-only weight for the optional performance-improvement score.
    # This does NOT affect pass/fail and is not a scoring layer weight.
    PERFORMANCE_SCORE_WEIGHT: float = field(
        default_factory=lambda: _env_float("SD_HWE_PERFORMANCE_SCORE_WEIGHT", 0.25)
    )


settings = Settings()
