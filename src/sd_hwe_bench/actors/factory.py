"""Factory for creating actors from CLI strings."""

from __future__ import annotations

from sd_hwe_bench.actors.base import Actor
from sd_hwe_bench.actors.codex import CodexActor
from sd_hwe_bench.actors.kimi import KimiActor


def create_actor(spec: str, timeout: int | None = None) -> Actor:
    """Create an actor from a specification string.

    Supported specs:
    - 'kimi[:model]'
    - 'codex[:model]'

    Example:
        create_actor("kimi")
        create_actor("codex:gpt-5.1-codex")
    """
    if ":" in spec:
        driver, model = spec.split(":", 1)
    else:
        driver, model = spec, None

    driver = driver.lower()

    if driver == "kimi":
        return KimiActor(model=model, timeout=timeout)
    if driver == "codex":
        return CodexActor(model=model, timeout=timeout)

    raise ValueError(
        f"Unknown actor driver: {driver}. "
        "Supported: kimi, codex"
    )
