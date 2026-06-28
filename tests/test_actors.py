"""Tests for actor factory and base behavior."""

import pytest

from sd_hwe_bench.actors import (
    CodexActor,
    KimiActor,
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

    def test_unknown_driver(self):
        with pytest.raises(ValueError):
            create_actor("unknown")
