"""OpenAI-compatible API actor (DeepSeek, OpenAI, etc.)."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from openai import OpenAI

from sd_hwe_bench.actors.base import Actor, ActorResult, list_yaml_files
from sd_hwe_bench.prompts import PromptBuilder
from sd_hwe_bench.sandbox.parser import YamlBlockParser
from sd_hwe_bench.sandbox.runner import SandboxRunner
from sd_hwe_bench.settings import settings

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = """You are a hardware engineering design agent. You must produce piki YAML design declarations.
Follow the piki directory conventions exactly.
Output each file as a separate ```yaml code block with the file path as a comment on the first line."""


class OpenAIActor(Actor):
    """Run any OpenAI-compatible API (DeepSeek, OpenAI, etc.)."""

    name = "openai"

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        runner: SandboxRunner | None = None,
    ):
        super().__init__(model=model or settings.DEFAULT_OPENAI_MODEL, timeout=timeout)
        self.base_url = base_url or settings.OPENAI_BASE_URL
        api_key_env = settings.OPENAI_API_KEY_ENV
        self.api_key = api_key or os.environ.get(api_key_env)
        self._client: OpenAI | None = None
        self.prompt_builder = PromptBuilder()
        # Respect the global sandbox configuration by default. Callers may
        # inject a specific runner (e.g. host-only for fast paths).
        self.runner = runner or SandboxRunner()
        self.system_prompt = settings.SYSTEM_PROMPT or _DEFAULT_SYSTEM_PROMPT

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(f"{settings.OPENAI_API_KEY_ENV} not set and no api_key provided")
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        workspace_root = Path(workspace_root).resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)

        before = list_yaml_files(workspace_root)

        start = time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )
            elapsed = time.time() - start
            raw = resp.choices[0].message.content or ""
        except Exception as exc:
            return ActorResult(
                success=False,
                raw_output="",
                files_written=0,
                elapsed_s=0.0,
                error=str(exc),
            )

        parser = YamlBlockParser(workspace_root)
        written, errors = parser.parse_and_write(raw)
        if errors:
            logger.debug("OpenAI parse errors: %s", errors)

        # Run piki check and generate inside the workspace so deliverables exist.
        check_result = self.runner.check(workspace_root)
        if not check_result.success:
            logger.warning(
                "piki check failed for %s: %s", workspace_root, check_result.stderr[:500]
            )
        else:
            generate_result = self.runner.generate(workspace_root)
            if not generate_result.success:
                logger.warning(
                    "piki generate failed for %s: %s",
                    workspace_root,
                    generate_result.stderr[:500],
                )

        after = list_yaml_files(workspace_root)
        new_files = after - before

        return ActorResult(
            success=True,
            raw_output=raw,
            files_written=len(new_files),
            elapsed_s=elapsed,
        )
