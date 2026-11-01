"""Catalog building: usable sources, duplicate names, skip folders, and failing closed."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from lazy_skills_mcp.catalog import SkillsDirectoryError, load_catalog

from skill_tree import write_skill


def test_a_valid_directory_yields_every_skill_sorted_by_name(skills_dir: Path) -> None:
    catalog = load_catalog([skills_dir])

    assert [entry.name for entry in catalog] == ["embedded-linux-bringup", "nix-flakes"]
    assert catalog[0].description == "Bring up a new embedded Linux board"
    assert catalog[0].directory == skills_dir / "embedded-linux-bringup"


def test_an_invalid_skill_is_left_out_and_the_rest_are_served(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "lazy"
    write_skill(root / "broken-skill", name="another-name")
    write_skill(root / "good-skill")

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([root])

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert "broken-skill" in caplog.text


def test_a_missing_directory_fails_closed_naming_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(SkillsDirectoryError, match=str(missing)):
        load_catalog([missing])


def test_an_empty_directory_fails_closed_naming_the_path(tmp_path: Path) -> None:
    empty = tmp_path / "lazy"
    empty.mkdir()

    with pytest.raises(SkillsDirectoryError, match=str(empty)):
        load_catalog([empty])


def test_a_directory_holding_only_invalid_skills_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    write_skill(root / "broken-skill", name="another-name")

    with pytest.raises(SkillsDirectoryError, match=str(root)):
        load_catalog([root])


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
def test_an_unreadable_directory_fails_closed_naming_the_path(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    root.mkdir()
    try:
        root.chmod(0o000)
        with pytest.raises(SkillsDirectoryError, match=str(root)):
            load_catalog([root])
    finally:
        root.chmod(0o755)


def test_a_folder_without_a_manifest_is_a_silent_group(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A folder without SKILL.md is a group: searched for skills, never logged."""
    root = tmp_path / "lazy"
    not_a_skill = root / "not-a-skill"
    not_a_skill.mkdir(parents=True)
    (not_a_skill / "README.md").write_text("just a stray directory\n", encoding="utf-8")
    write_skill(root / "good-skill")

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([root])

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert caplog.text == ""


def test_a_symlinked_skill_folder_pointing_outside_the_source_is_served(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A skill installed as a symlink to a folder elsewhere is served like a copy, as
    agents that follow symlinked skill folders load it."""
    root = tmp_path / "lazy"
    root.mkdir()
    store = write_skill(tmp_path / "store" / "linked-skill")
    (root / "linked-skill").symlink_to(store)

    with caplog.at_level(logging.WARNING):
        (catalog_entry,) = load_catalog([root])

    assert catalog_entry.name == "linked-skill"
    assert catalog_entry.directory == root / "linked-skill"
    assert caplog.text == ""


def test_a_scan_never_lists_skill_files(skills_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scan reads only each SKILL.md; listing a skill's files is load_skill's job,
    so a scan that walked a skill's files recursively would fail here."""

    def fail(self: Path, pattern: str) -> object:
        raise AssertionError(f"scan walked the files under {self}")

    monkeypatch.setattr(Path, "rglob", fail)

    assert [entry.name for entry in load_catalog([skills_dir])] == [
        "embedded-linux-bringup",
        "nix-flakes",
    ]


def test_the_first_source_wins_a_duplicate_name_and_both_folders_are_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    personal = write_skill(tmp_path / "personal" / "python-style", description="my own rules")
    shared = write_skill(tmp_path / "shared" / "python" / "python-style", description="shared")
    write_skill(tmp_path / "shared" / "python" / "python-testing", description="tests")

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([tmp_path / "personal", tmp_path / "shared"])

    assert [(entry.name, entry.directory) for entry in catalog] == [
        ("python-style", personal),
        ("python-testing", tmp_path / "shared" / "python" / "python-testing"),
    ]
    assert str(personal) in caplog.text
    assert str(shared) in caplog.text


def test_within_one_source_the_first_path_in_walk_order_wins(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    first = write_skill(tmp_path / "source" / "a" / "same-name", description="first")
    second = write_skill(tmp_path / "source" / "b" / "same-name", description="second")

    with caplog.at_level(logging.WARNING):
        (entry,) = load_catalog([tmp_path / "source"])

    assert entry.directory == first
    assert str(first) in caplog.text
    assert str(second) in caplog.text


def test_a_missing_source_among_several_fails_closed_naming_it(skills_dir: Path) -> None:
    missing = skills_dir.parent / "not-there"

    with pytest.raises(SkillsDirectoryError, match=str(missing)):
        load_catalog([skills_dir, missing])


def test_an_empty_source_beside_a_useful_one_is_logged_not_fatal(
    tmp_path: Path, skills_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([empty, skills_dir])

    assert [entry.name for entry in catalog] == ["embedded-linux-bringup", "nix-flakes"]
    assert str(empty) in caplog.text


def test_no_valid_skill_in_any_source_fails_closed_naming_them(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    with pytest.raises(SkillsDirectoryError, match="no valid skill") as excinfo:
        load_catalog([first, second])

    assert str(first) in str(excinfo.value)
    assert str(second) in str(excinfo.value)


def test_a_skill_reached_again_through_a_later_source_is_not_a_duplicate(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The visited set spans every source: a later source linking to a skill an
    earlier source already served is the same skill, not a conflict."""
    first = write_skill(tmp_path / "first" / "shared")
    write_skill(tmp_path / "first" / "other")
    second = tmp_path / "second"
    second.mkdir()
    (second / "shared").symlink_to(first)
    write_skill(second / "own")

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([tmp_path / "first", second])

    assert [entry.name for entry in catalog] == ["other", "own", "shared"]
    assert caplog.text == ""


def test_a_source_nested_in_an_earlier_source_is_not_called_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    write_skill(tmp_path / "skills" / "team" / "team-skill")

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([tmp_path / "skills", tmp_path / "skills" / "team"])

    assert [entry.name for entry in catalog] == ["team-skill"]
    assert caplog.text == ""


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
def test_a_source_under_an_unsearchable_parent_fails_closed_naming_it(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    source = parent / "skills"
    source.mkdir(parents=True)
    parent.chmod(0o000)
    try:
        with pytest.raises(SkillsDirectoryError, match=str(source)):
            load_catalog([source])
    finally:
        parent.chmod(0o755)
