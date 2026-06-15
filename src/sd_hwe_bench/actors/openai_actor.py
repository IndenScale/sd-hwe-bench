"""OpenAI-compatible API actor (DeepSeek, etc.)."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from openai import OpenAI

from sd_hwe_bench.actors.base import Actor, ActorResult
from sd_hwe_bench.sandbox.parser import YamlBlockParser

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a hardware engineering design agent. You must produce piki YAML design declarations.
Follow the piki directory conventions exactly:
- instances/devices/ — device instances
- instances/racks/ — rack instances
- instances/pdus/ — PDU instances
- instances/ports/ — port instances
- instances/transceivers/ — transceiver instances
- instances/fibers/ — fiber instances
- instances/port_connections/ — port connection instances
- layouts/layout.yaml — rack layout
- mates/rack-mount/ — rack mount mates
- mates/power-iec/ — power IEC mates
- mates/sfp28-cage/ — SFP28 cage mates
- mates/lc-connector/ — LC connector mates
Output each file as a separate ```yaml code block with file path as comment on first line.
After writing files, run `piki check` and `piki generate` in your workspace."""


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

        return ActorResult(
            success=True,
            raw_output=raw,
            files_written=written,
            elapsed_s=elapsed,
        )
