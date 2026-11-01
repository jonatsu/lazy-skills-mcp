"""One skill folder: frontmatter parsing, name validation, and file confinement."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from lazy_skills_mcp.skill import SkillEntry, list_skill_files, read_skill

from skill_tree import write_skill


def _write_manifest(skill_dir: Path, text: str) -> Path:
    """A skill folder whose SKILL.md holds exactly `text`, valid or not."""
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    return skill_dir


def test_a_valid_skill_reads_its_name_description_and_folder(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path / "my-skill", description="does a thing")

    assert read_skill(skill_dir) == SkillEntry("my-skill", "does a thing", skill_dir)


@pytest.mark.parametrize(
    ("folder", "manifest"),
    [
        ("unparsable", "---\nname: unparsable\n  bad indent: [unclosed\n---\nbody\n"),
        ("no-frontmatter", "# Just a heading, no frontmatter\n"),
        ("no-description", "---\nname: no-description\n---\nbody\n"),
        ("on-disk-name", "---\nname: a-different-name\ndescription: fine\n---\nbody\n"),
    ],
)
def test_an_invalid_skill_is_rejected_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, folder: str, manifest: str
) -> None:
    skill_dir = _write_manifest(tmp_path / folder, manifest)

    with caplog.at_level(logging.WARNING):
        entry = read_skill(skill_dir)

    assert entry is None
    assert folder in caplog.text


def test_a_manifest_that_is_not_utf8_is_rejected_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    skill_dir = tmp_path / "latin1-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_bytes(b"---\nname: latin1-skill\ndescription: caf\xe9\n---\n")

    with caplog.at_level(logging.WARNING):
        entry = read_skill(skill_dir)

    assert entry is None
    assert "latin1-skill" in caplog.text


def test_other_files_are_listed_as_relative_paths(tmp_path: Path) -> None:
    skill_dir = write_skill(tmp_path / "my-skill")
    (skill_dir / "references").mkdir()
    (skill_dir / "scripts").mkdir()
    (skill_dir / "references" / "notes.md").write_text("notes", encoding="utf-8")
    (skill_dir / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    assert list_skill_files(skill_dir) == ("references/notes.md", "scripts/run.sh")


def _skill_with_kept_reference(tmp_path: Path) -> Path:
    skill_dir = write_skill(tmp_path / "lazy" / "my-skill")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "inside.md").write_text("kept", encoding="utf-8")
    return skill_dir


def _outside_secret(tmp_path: Path) -> Path:
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("must not be reachable", encoding="utf-8")
    return secret


def test_a_symlink_leaving_the_skill_folder_is_excluded(tmp_path: Path) -> None:
    skill_dir = _skill_with_kept_reference(tmp_path)
    (skill_dir / "references" / "escape.md").symlink_to(_outside_secret(tmp_path))

    assert list_skill_files(skill_dir) == ("references/inside.md",)


def test_a_symlink_chain_leaving_the_skill_folder_is_excluded(tmp_path: Path) -> None:
    skill_dir = _skill_with_kept_reference(tmp_path)
    middle_link = tmp_path / "middle-link.txt"
    middle_link.symlink_to(_outside_secret(tmp_path))
    (skill_dir / "references" / "escape.md").symlink_to(middle_link)

    assert list_skill_files(skill_dir) == ("references/inside.md",)


def test_a_relative_dotdot_symlink_that_escapes_is_excluded(tmp_path: Path) -> None:
    skill_dir = _skill_with_kept_reference(tmp_path)
    secret = _outside_secret(tmp_path)
    (skill_dir / "references" / "escape.md").symlink_to(Path("..") / ".." / ".." / secret.name)

    assert list_skill_files(skill_dir) == ("references/inside.md",)


def test_a_symlinked_subfolder_leaving_the_skill_folder_excludes_its_files(
    tmp_path: Path,
) -> None:
    skill_dir = write_skill(tmp_path / "lazy" / "my-skill")
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("must not be reachable", encoding="utf-8")
    (skill_dir / "linked-out").symlink_to(outside_dir)

    assert list_skill_files(skill_dir) == ()


def test_a_symlinked_skill_folder_lists_the_files_of_its_real_folder(tmp_path: Path) -> None:
    """A skill installed as a symlink to a folder elsewhere keeps its own files."""
    store = write_skill(tmp_path / "store" / "linked-skill")
    (store / "notes.md").write_text("kept", encoding="utf-8")
    linked = tmp_path / "lazy" / "linked-skill"
    linked.parent.mkdir()
    linked.symlink_to(store)

    assert list_skill_files(linked) == ("notes.md",)


@pytest.mark.parametrize(
    ("manifest", "reason"),
    [
        ("---\nname: my-skill\n---\nbody\n", "has no 'description'"),
        ("---\nname: my-skill\ndescription: 123\n---\nbody\n", "has a non-string 'description'"),
        ("---\nname: [a, b]\ndescription: fine\n---\nbody\n", "has a non-string 'name'"),
    ],
)
def test_the_logged_reason_names_the_field_and_its_problem(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, manifest: str, reason: str
) -> None:
    skill_dir = _write_manifest(tmp_path / "my-skill", manifest)

    with caplog.at_level(logging.WARNING):
        assert read_skill(skill_dir) is None

    assert reason in caplog.text
