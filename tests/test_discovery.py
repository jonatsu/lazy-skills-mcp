"""Source discovery: the layout rule, the depth limit, hidden folders, and symlinks."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from lazy_skills_mcp.discovery import MAX_DEPTH, discover_skills


def _write_skill(skill_dir: Path, description: str = "does a thing") -> Path:
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_dir.name}\ndescription: {description}\n---\nbody\n",
        encoding="utf-8",
    )
    return skill_dir


def _names(source: Path) -> list[str]:
    return [entry.name for entry in discover_skills(source, set())]


def test_skills_in_nested_groups_are_found_in_sorted_walk_order(tmp_path: Path) -> None:
    """The layout of jonatsu/agent-skills: skills one and two groups deep."""
    source = tmp_path / "agent-skills"
    _write_skill(source / "development" / "python" / "python-testing")
    _write_skill(source / "development" / "python" / "python-style")
    _write_skill(source / "agents" / "ast-grep")
    _write_skill(source / "development" / "just-task-runner")

    assert _names(source) == ["ast-grep", "just-task-runner", "python-style", "python-testing"]


def test_a_skill_is_not_searched_for_further_skills(tmp_path: Path) -> None:
    source = tmp_path / "source"
    outer = _write_skill(source / "outer")
    _write_skill(outer / "examples" / "inner")

    assert _names(source) == ["outer"]


def test_an_invalid_skill_is_logged_and_not_searched(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source = tmp_path / "source"
    broken = source / "broken"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    _write_skill(broken / "hidden-inside")

    with caplog.at_level(logging.WARNING):
        names = _names(source)

    assert names == []
    assert "broken" in caplog.text


def test_a_source_that_is_itself_a_skill_serves_that_skill(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path / "single-skill")

    assert _names(skill) == ["single-skill"]


def test_hidden_folders_are_skipped(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_skill(source / ".git" / "not-served")
    _write_skill(source / "group" / ".cache" / "not-served-either")
    _write_skill(source / "served")

    assert _names(source) == ["served"]


def _nest(source: Path, levels: int) -> Path:
    """The folder `levels` below `source`, through groups named g1, g2, and so on."""
    folder = source
    for level in range(1, levels + 1):
        folder = folder / f"g{level}"
    return folder


def test_a_skill_at_the_depth_limit_is_found(tmp_path: Path) -> None:
    source = tmp_path / "source"
    deepest = _nest(source, MAX_DEPTH - 1) / "deep-skill"
    _write_skill(deepest)

    assert _names(source) == ["deep-skill"]


def test_a_group_at_the_depth_limit_is_not_searched_and_is_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source = tmp_path / "source"
    group_at_limit = _nest(source, MAX_DEPTH)
    _write_skill(group_at_limit / "too-deep")

    with caplog.at_level(logging.WARNING):
        names = _names(source)

    assert names == []
    assert "depth limit" in caplog.text
    assert str(group_at_limit) in caplog.text


def test_a_symlink_cycle_ends_without_a_log_line(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source = tmp_path / "source"
    _write_skill(source / "group" / "real-skill")
    (source / "group" / "loop").symlink_to(source)

    with caplog.at_level(logging.WARNING):
        names = _names(source)

    assert names == ["real-skill"]
    assert caplog.text == ""


def test_one_real_skill_reached_through_two_paths_appears_once(tmp_path: Path) -> None:
    source = tmp_path / "source"
    real = _write_skill(source / "a" / "shared-skill")
    (source / "b").mkdir()
    (source / "b" / "shared-skill").symlink_to(real)

    entries = list(discover_skills(source, set()))

    assert [entry.directory for entry in entries] == [real]


def test_a_symlinked_group_is_searched(tmp_path: Path) -> None:
    store = tmp_path / "store"
    _write_skill(store / "stored-skill")
    source = tmp_path / "source"
    source.mkdir()
    (source / "linked-group").symlink_to(store)

    assert _names(source) == ["stored-skill"]


def test_the_walk_order_does_not_depend_on_creation_order(tmp_path: Path) -> None:
    paths = ["zeta/one", "alpha/two", "mid/three/four", "alpha/five"]

    first = tmp_path / "first"
    for relative in paths:
        _write_skill(first / relative)
    second = tmp_path / "second"
    for relative in reversed(paths):
        _write_skill(second / relative)

    assert _names(first) == _names(second) == ["five", "two", "four", "one"]
