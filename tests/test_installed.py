"""Skip folders: which skills count as installed natively, and how failures read."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from lazy_skills_mcp.catalog import SkillsDirectoryError, load_catalog
from lazy_skills_mcp.installed import installed_names

from skill_tree import write_skill


def test_a_skill_counts_as_installed_by_folder_name_and_by_frontmatter_name(
    tmp_path: Path,
) -> None:
    native = tmp_path / "native"
    write_skill(native / "renamed-folder", name="real-name")
    (native / "no-manifest").mkdir()

    assert installed_names([native]) == {"renamed-folder", "real-name", "no-manifest"}


def test_skip_folders_are_read_flat(tmp_path: Path) -> None:
    native = tmp_path / "native"
    write_skill(native / "group" / "nested-skill")

    assert installed_names([native]) == {"group"}


def test_a_missing_skip_folder_counts_as_empty_and_is_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "typo"

    with caplog.at_level(logging.WARNING):
        names = installed_names([missing])

    assert names == frozenset()
    assert str(missing) in caplog.text


def test_a_skill_installed_under_its_frontmatter_name_is_not_served(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_skill(source / "python-style")
    write_skill(source / "python-testing")
    native = tmp_path / "native"
    write_skill(native / "prefixed-python-style", name="python-style")

    catalog = load_catalog([source], [native])

    assert [entry.name for entry in catalog] == ["python-testing"]


def test_every_skill_installed_natively_fails_closed_naming_the_skip_folders(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    write_skill(source / "only-skill")
    native = tmp_path / "native"
    write_skill(native / "only-skill")

    with pytest.raises(SkillsDirectoryError, match="installed in a skip folder") as excinfo:
        load_catalog([source], [native])

    assert str(native) in str(excinfo.value)


def test_a_duplicate_is_reported_even_when_its_name_is_installed(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    first = write_skill(tmp_path / "first" / "dup")
    second = write_skill(tmp_path / "second" / "dup")
    write_skill(tmp_path / "first" / "kept")
    native = tmp_path / "native"
    write_skill(native / "dup")

    with caplog.at_level(logging.WARNING):
        catalog = load_catalog([tmp_path / "first", tmp_path / "second"], [native])

    assert [entry.name for entry in catalog] == ["kept"]
    assert str(first) in caplog.text
    assert str(second) in caplog.text


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
def test_a_skip_folder_under_an_unsearchable_parent_counts_as_empty_and_is_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    parent = tmp_path / "parent"
    skip_dir = parent / "native"
    skip_dir.mkdir(parents=True)
    parent.chmod(0o000)
    try:
        with caplog.at_level(logging.WARNING):
            names = installed_names([skip_dir])
    finally:
        parent.chmod(0o755)

    assert names == frozenset()
    assert str(skip_dir) in caplog.text


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
def test_a_readable_but_unsearchable_skip_folder_is_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    native = tmp_path / "native"
    write_skill(native / "ast-grep")
    native.chmod(0o644)
    try:
        with caplog.at_level(logging.WARNING):
            names = installed_names([native])
    finally:
        native.chmod(0o755)

    assert names == frozenset()
    assert str(native) in caplog.text


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permission bits")
def test_a_skip_folder_child_with_an_unreachable_target_skips_only_that_child(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    native = tmp_path / "native"
    write_skill(native / "ast-grep")
    locked = tmp_path / "locked"
    write_skill(locked / "behind")
    (native / "unreachable").symlink_to(locked / "behind")
    locked.chmod(0o000)
    try:
        with caplog.at_level(logging.WARNING):
            names = installed_names([native])
    finally:
        locked.chmod(0o755)

    assert "ast-grep" in names
    assert "unreachable" in caplog.text


def test_a_skip_folder_manifest_that_is_not_utf8_still_counts_by_folder_name(
    tmp_path: Path,
) -> None:
    native = tmp_path / "native"
    bad = native / "latin1-skill"
    bad.mkdir(parents=True)
    (bad / "SKILL.md").write_bytes(b"---\nname: other\ndescription: caf\xe9\n---\n")

    assert installed_names([native]) == {"latin1-skill"}
