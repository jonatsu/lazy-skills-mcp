"""Shared fixture skill trees, built under `tmp_path` so no test touches a real
skills directory."""

from __future__ import annotations

from pathlib import Path

import pytest

VALID_SKILL_MD = """\
---
name: {name}
description: {description}
---

# {name}

Body text for {name}.
"""


def _write_skill(root: Path, name: str, description: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        VALID_SKILL_MD.format(name=name, description=description), encoding="utf-8"
    )
    return skill_dir


@pytest.fixture
def anyio_backend() -> str:
    """Pin anyio's parametrized backend to asyncio; trio is not installed."""
    return "asyncio"


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """A directory holding two valid, unrelated skills."""
    root = tmp_path / "lazy"
    root.mkdir()
    _write_skill(root, "embedded-linux-bringup", "Bring up a new embedded Linux board")
    _write_skill(root, "nix-flakes", "Author and debug Nix flakes")
    return root
