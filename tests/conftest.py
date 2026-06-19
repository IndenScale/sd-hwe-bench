"""Shared pytest fixtures and hooks for sd-hwe-bench."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def pytest_sessionstart(session):
    """Log piki/adl versions at the start of the test session."""
    versions = []
    for package in ("piki", "adl"):
        try:
            from importlib.metadata import version

            versions.append(f"{package}=={version(package)}")
        except Exception:
            versions.append(f"{package}=not-installed")
    logger.info("SD-HWE-Bench test session starting. Engines: %s", ", ".join(versions))
