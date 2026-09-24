"""Catalog scanning: frontmatter parsing, name validation, and file confinement."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from skillserverlib.catalog import SkillsDirectoryError, load_catalog


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

    assert sorted(catalog_entry.files) == [
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

    assert sorted(catalog_entry.files) == ["references/inside.md"]


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
