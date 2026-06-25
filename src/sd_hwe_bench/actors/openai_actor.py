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

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a hardware engineering design agent. You must produce piki YAML design declarations.
Follow the piki directory conventions exactly.
Output each file as a separate ```yaml code block with the file path as a comment on the first line."""


class OpenAIActor(Actor):
    """Run any OpenAI-compatible API (DeepSeek, OpenAI, etc.)."""

    name = "openai"

    def __init__(
        self,
        model: str | None = None,
        timeout: int = 600,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(model=model or "deepseek-chat", timeout=timeout)
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client: OpenAI | None = None
        self.prompt_builder = PromptBuilder()
        # Use host piki directly to avoid Docker auto-detection overhead and
        # warnings in environments without a running container runtime.
        self.runner = SandboxRunner(backend="none")

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY not set and no api_key provided")
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
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=8192,
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
