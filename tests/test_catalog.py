"""Catalog scanning: frontmatter parsing, name validation, and file confinement."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from lazy_skills_mcp.catalog import SkillsDirectoryError, load_catalog
from lazy_skills_mcp.skill import list_skill_files


def test_a_valid_directory_yields_every_skill_sorted_by_name(skills_dir: Path) -> None:
    catalog = load_catalog(skills_dir)

    assert [entry.name for entry in catalog] == ["embedded-linux-bringup", "nix-flakes"]
    assert catalog[0].description == "Bring up a new embedded Linux board"
    assert catalog[0].directory == skills_dir / "embedded-linux-bringup"


def test_other_files_are_listed_as_relative_paths(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody\n", encoding="utf-8"
    )
    (skill_dir / "references" / "notes.md").write_text("notes", encoding="utf-8")
    (skill_dir / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    (catalog_entry,) = load_catalog(root)

    assert sorted(list_skill_files(catalog_entry.directory)) == [
        "references/notes.md",
        "scripts/run.sh",
    ]


def test_a_skill_with_unparsable_frontmatter_is_skipped_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "lazy"
    broken = root / "broken-skill"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text(
        "---\nname: broken-skill\n  bad indent: [unclosed\n---\nbody\n", encoding="utf-8"
    )
    good = root / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: fine\n---\nbody\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog(root)

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert "broken-skill" in caplog.text


def test_a_skill_with_missing_frontmatter_is_skipped_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "lazy"
    plain = root / "plain-skill"
    plain.mkdir(parents=True)
    (plain / "SKILL.md").write_text("# Just a heading, no frontmatter\n", encoding="utf-8")
    good = root / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: fine\n---\nbody\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog(root)

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert "plain-skill" in caplog.text


def test_a_skill_whose_frontmatter_name_does_not_match_its_directory_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "lazy"
    mismatched = root / "on-disk-name"
    mismatched.mkdir(parents=True)
    (mismatched / "SKILL.md").write_text(
        "---\nname: a-different-name\ndescription: fine\n---\nbody\n", encoding="utf-8"
    )
    good = root / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: fine\n---\nbody\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog(root)

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert "on-disk-name" in caplog.text


def test_a_symlink_leaving_the_skill_directory_is_excluded_from_its_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody\n", encoding="utf-8"
    )
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "inside.md").write_text("kept", encoding="utf-8")

    outside_secret = tmp_path / "outside-secret.txt"
    outside_secret.write_text("must not be reachable", encoding="utf-8")
    (skill_dir / "references" / "escape.md").symlink_to(outside_secret)

    (catalog_entry,) = load_catalog(root)

    assert sorted(list_skill_files(catalog_entry.directory)) == ["references/inside.md"]


def test_a_missing_directory_fails_closed_naming_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(SkillsDirectoryError, match=str(missing)):
        load_catalog(missing)


def test_an_empty_directory_fails_closed_naming_the_path(tmp_path: Path) -> None:
    empty = tmp_path / "lazy"
    empty.mkdir()

    with pytest.raises(SkillsDirectoryError, match=str(empty)):
        load_catalog(empty)


def test_a_directory_holding_only_invalid_skills_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    broken = root / "broken-skill"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")

    with pytest.raises(SkillsDirectoryError, match=str(root)):
        load_catalog(root)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
def test_an_unreadable_directory_fails_closed_naming_the_path(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    root.mkdir()
    try:
        root.chmod(0o000)
        with pytest.raises(SkillsDirectoryError, match=str(root)):
            load_catalog(root)
    finally:
        root.chmod(0o755)


def test_a_skill_with_frontmatter_missing_the_description_is_skipped_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "lazy"
    incomplete = root / "incomplete-skill"
    incomplete.mkdir(parents=True)
    (incomplete / "SKILL.md").write_text(
        "---\nname: incomplete-skill\n---\nbody\n", encoding="utf-8"
    )
    good = root / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: fine\n---\nbody\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog(root)

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert "incomplete-skill" in caplog.text


def test_a_folder_without_a_manifest_is_a_silent_group(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A folder without SKILL.md is a group: searched for skills, never logged."""
    root = tmp_path / "lazy"
    not_a_skill = root / "not-a-skill"
    not_a_skill.mkdir(parents=True)
    (not_a_skill / "README.md").write_text("just a stray directory\n", encoding="utf-8")
    good = root / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: fine\n---\nbody\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog(root)

    assert [entry.name for entry in catalog] == ["good-skill"]
    assert caplog.text == ""


def test_a_symlink_chain_leaving_the_skill_directory_is_excluded_from_its_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody\n", encoding="utf-8"
    )
    (skill_dir / "references" / "inside.md").write_text("kept", encoding="utf-8")

    outside_secret = tmp_path / "outside-secret.txt"
    outside_secret.write_text("must not be reachable", encoding="utf-8")
    middle_link = tmp_path / "middle-link.txt"
    middle_link.symlink_to(outside_secret)
    (skill_dir / "references" / "escape.md").symlink_to(middle_link)

    (catalog_entry,) = load_catalog(root)

    assert sorted(list_skill_files(catalog_entry.directory)) == ["references/inside.md"]


def test_a_relative_dotdot_symlink_target_that_escapes_is_excluded(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody\n", encoding="utf-8"
    )
    (skill_dir / "references" / "inside.md").write_text("kept", encoding="utf-8")

    outside_secret = tmp_path / "outside-secret.txt"
    outside_secret.write_text("must not be reachable", encoding="utf-8")
    escape_link = skill_dir / "references" / "escape.md"
    escape_link.symlink_to(Path("..") / ".." / ".." / outside_secret.name)

    (catalog_entry,) = load_catalog(root)

    assert sorted(list_skill_files(catalog_entry.directory)) == ["references/inside.md"]


def test_a_symlinked_subdirectory_leaving_the_skill_directory_excludes_its_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody\n", encoding="utf-8"
    )

    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("must not be reachable", encoding="utf-8")
    (skill_dir / "linked-out").symlink_to(outside_dir)

    (catalog_entry,) = load_catalog(root)

    assert list_skill_files(catalog_entry.directory) == ()


def test_a_symlinked_skill_folder_pointing_outside_the_source_is_served(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A skill installed as a symlink to a folder elsewhere is served like a copy, as
    agents that follow symlinked skill folders load it. Its files are still confined to
    the skill's real folder."""
    root = tmp_path / "lazy"
    root.mkdir()
    store = tmp_path / "store" / "linked-skill"
    store.mkdir(parents=True)
    (store / "SKILL.md").write_text(
        "---\nname: linked-skill\ndescription: installed by symlink\n---\nbody\n",
        encoding="utf-8",
    )
    (store / "notes.md").write_text("kept", encoding="utf-8")
    (root / "linked-skill").symlink_to(store)

    with caplog.at_level(logging.WARNING):
        (catalog_entry,) = load_catalog(root)

    assert catalog_entry.name == "linked-skill"
    assert list_skill_files(catalog_entry.directory) == ("notes.md",)
    assert caplog.text == ""


def test_a_scan_never_lists_skill_files(skills_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scan reads only each SKILL.md; listing a skill's files is load_skill's job,
    so a scan that walked a skill's files recursively would fail here."""

    def fail(self: Path, pattern: str) -> object:
        raise AssertionError(f"scan walked the files under {self}")

    monkeypatch.setattr(Path, "rglob", fail)

    assert [entry.name for entry in load_catalog(skills_dir)] == [
        "embedded-linux-bringup",
        "nix-flakes",
    ]
