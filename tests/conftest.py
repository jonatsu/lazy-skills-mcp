"""Shared fixture skill trees, built under `tmp_path` so no test touches a real
skills directory."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_tree import write_skill


@pytest.fixture
def anyio_backend() -> str:
    """Pin anyio's parametrized backend to asyncio; trio is not installed."""
    return "asyncio"


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """A directory holding two valid, unrelated skills."""
    root = tmp_path / "lazy"
    write_skill(root / "embedded-linux-bringup", description="Bring up a new embedded Linux board")
    write_skill(root / "nix-flakes", description="Author and debug Nix flakes")
    return root
