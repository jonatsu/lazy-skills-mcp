"""Directory resolution precedence, exercised without touching a real filesystem.

`resolve_skills_dir` is a pure computation: it never stats the filesystem, so these
tests only ever check the returned `Path`, with every environment variable it reads
set explicitly by the test rather than inherited from the machine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillserverlib.location import resolve_skills_dir


def test_an_explicit_argument_wins_over_every_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir("/explicit/skills") == Path("/explicit/skills")


def test_xdg_data_home_wins_over_the_bare_home_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/xdg/agent-skills/lazy")


def test_the_home_default_applies_when_neither_argument_nor_xdg_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/home/.local/share/agent-skills/lazy")


def test_an_empty_explicit_argument_is_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert resolve_skills_dir("") == Path("/env/xdg/agent-skills/lazy")


def test_an_empty_xdg_data_home_is_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/home/.local/share/agent-skills/lazy")
