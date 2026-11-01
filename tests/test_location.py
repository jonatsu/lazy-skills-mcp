"""Directory resolution precedence, exercised without touching a real filesystem.

`resolve_skills_dir` is a pure computation: it never stats the filesystem, so these
tests only ever check the returned `Path`, with every environment variable it reads
set explicitly by the test rather than inherited from the machine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lazy_skills_mcp.location import resolve_skills_dir


def test_an_explicit_argument_wins_over_every_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir("/explicit/skills") == Path("/explicit/skills")


def test_the_env_var_wins_over_xdg_data_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/skills-dir")


def test_the_env_var_wins_over_the_bare_home_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/skills-dir")


def test_an_empty_env_var_is_treated_as_absent_and_xdg_data_home_applies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "")
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/xdg/lazy-skills-mcp/skills")


def test_xdg_data_home_wins_over_the_bare_home_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/xdg/lazy-skills-mcp/skills")


def test_the_home_default_applies_when_nothing_else_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/home/.local/share/lazy-skills-mcp/skills")


def test_an_empty_explicit_argument_is_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert resolve_skills_dir("") == Path("/env/xdg/lazy-skills-mcp/skills")


def test_an_empty_xdg_data_home_is_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", "")
    monkeypatch.setenv("HOME", "/env/home")

    assert resolve_skills_dir(None) == Path("/env/home/.local/share/lazy-skills-mcp/skills")


def test_the_result_does_not_depend_on_the_current_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The design requires the resolved directory to never come from this
    package's own location (`__file__`) or from where it happens to run. Changing
    the working directory, with every input held fixed, must not change the
    result; a `__file__`- or cwd-relative computation would fail this."""
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", "/env/home")
    before = resolve_skills_dir(None)

    monkeypatch.chdir(tmp_path)
    after = resolve_skills_dir(None)

    assert before == after == Path("/env/home/.local/share/lazy-skills-mcp/skills")
