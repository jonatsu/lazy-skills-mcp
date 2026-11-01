"""Source and skip-folder resolution, exercised without touching a real filesystem.

`resolve_skill_sources` is a pure computation: it never stats the filesystem, so these
tests only ever check the returned paths, with every environment variable it reads
set explicitly by the test rather than inherited from the machine.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lazy_skills_mcp.location import HomeFolderError, resolve_skill_sources


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", "/env/home")


def _sources(skills_dirs: list[str]) -> tuple[Path, ...]:
    return resolve_skill_sources(skills_dirs, []).sources


def test_explicit_arguments_win_over_every_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert _sources(["/explicit/skills"]) == (Path("/explicit/skills"),)


def test_repeated_arguments_keep_their_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/ignored")

    assert _sources(["/second-first", "/first-second"]) == (
        Path("/second-first"),
        Path("/first-second"),
    )


def test_the_env_var_wins_over_xdg_data_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert _sources([]) == (Path("/env/skills-dir"),)


def test_the_env_var_is_split_like_path_and_drops_empty_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = os.pathsep.join(["/env/one", "", "/env/two", ""])
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", raw)

    assert _sources([]) == (Path("/env/one"), Path("/env/two"))


def test_an_empty_env_var_is_treated_as_absent_and_xdg_data_home_applies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "")
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert _sources([]) == (Path("/env/xdg/lazy-skills-mcp/skills"),)


def test_an_env_var_of_only_separators_is_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", os.pathsep * 2)
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert _sources([]) == (Path("/env/xdg/lazy-skills-mcp/skills"),)


def test_xdg_data_home_wins_over_the_bare_home_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert _sources([]) == (Path("/env/xdg/lazy-skills-mcp/skills"),)


def test_the_home_default_applies_when_nothing_else_is_set() -> None:
    assert _sources([]) == (Path("/env/home/.local/share/lazy-skills-mcp/skills"),)


def test_empty_explicit_arguments_are_treated_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")

    assert _sources(["", ""]) == (Path("/env/xdg/lazy-skills-mcp/skills"),)


def test_an_empty_xdg_data_home_is_treated_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "")

    assert _sources([]) == (Path("/env/home/.local/share/lazy-skills-mcp/skills"),)


def test_a_leading_tilde_is_expanded_in_arguments_the_env_var_and_skip_folders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agents start MCP servers without a shell, so nothing else expands it."""
    assert _sources(["~/skills", "~"]) == (Path("/env/home/skills"), Path("/env/home"))

    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "~/from-env")
    assert _sources([]) == (Path("/env/home/from-env"),)

    skip = resolve_skill_sources([], ["~/.codex/skills"]).skip_dirs
    assert skip == (Path("/env/home/.codex/skills"),)


def test_only_a_leading_tilde_is_expanded() -> None:
    assert _sources(["/data/~/skills", "~other/skills"]) == (
        Path("/data/~/skills"),
        Path("~other/skills"),
    )


def test_skip_folders_keep_their_order_and_drop_empty_values() -> None:
    config = resolve_skill_sources([], ["/b", "", "/a"])

    assert config.skip_dirs == (Path("/b"), Path("/a"))


def test_there_are_no_skip_folders_unless_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")

    assert resolve_skill_sources([], []).skip_dirs == ()


def test_the_result_does_not_depend_on_the_current_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The resolved sources never come from this package's own location (`__file__`)
    or from where it happens to run. Changing the working directory, with every input
    held fixed, must not change the result."""
    before = _sources([])

    monkeypatch.chdir(tmp_path)
    after = _sources([])

    assert before == after == (Path("/env/home/.local/share/lazy-skills-mcp/skills"),)


def test_a_relative_xdg_data_home_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """The XDG Base Directory specification says to ignore a relative path."""
    monkeypatch.setenv("XDG_DATA_HOME", "relative/data")

    assert _sources([]) == (Path("/env/home/.local/share/lazy-skills-mcp/skills"),)


def _no_home_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the home folder unknowable, as with no HOME and no account entry."""

    def fail() -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.delenv("HOME")
    monkeypatch.setattr(Path, "home", staticmethod(fail))


def test_without_a_home_folder_the_default_source_fails_with_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_home_folder(monkeypatch)

    with pytest.raises(HomeFolderError, match="set HOME"):
        _sources([])


def test_without_a_home_folder_a_tilde_path_fails_with_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_home_folder(monkeypatch)

    with pytest.raises(HomeFolderError):
        _sources(["~/skills"])


def test_absolute_paths_and_xdg_data_home_need_no_home_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_home_folder(monkeypatch)

    assert _sources(["/explicit/skills"]) == (Path("/explicit/skills"),)
    monkeypatch.setenv("XDG_DATA_HOME", "/env/xdg")
    assert _sources([]) == (Path("/env/xdg/lazy-skills-mcp/skills"),)
