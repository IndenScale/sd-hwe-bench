"""Tests for actor factory and base behavior."""

import pytest

from sd_hwe_bench.actors import (
    CodexActor,
    GeminiActor,
    KimiActor,
    OpenAIActor,
    create_actor,
)


class TestActorFactory:
    def test_create_kimi(self):
        actor = create_actor("kimi")
        assert isinstance(actor, KimiActor)
        assert actor.model == "kimi-code/kimi-for-coding"

    def test_create_kimi_with_model(self):
        actor = create_actor("kimi:kimi-code/other")
        assert isinstance(actor, KimiActor)
        assert actor.model == "kimi-code/other"

    def test_create_codex(self):
        actor = create_actor("codex")
        assert isinstance(actor, CodexActor)
        assert actor.model == "deepseek-chat"

    def test_create_gemini(self):
        actor = create_actor("gemini")
        assert isinstance(actor, GeminiActor)
        assert actor.model == "gemini-2.5-flash"

    def test_create_openai(self):
        actor = create_actor("openai:gpt-4")
        assert isinstance(actor, OpenAIActor)
        assert actor.model == "gpt-4"

    def test_create_deepseek(self):
        actor = create_actor("deepseek:deepseek-v4")
        assert isinstance(actor, OpenAIActor)
        assert actor.model == "deepseek-v4"

    def test_unknown_driver(self):
        with pytest.raises(ValueError):
            create_actor("unknown")
