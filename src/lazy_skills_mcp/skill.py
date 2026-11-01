"""Read one skill folder: its `SKILL.md` frontmatter, its validity, and its other files.

A skill folder holds a `SKILL.md` whose YAML frontmatter carries a string `name` and
`description`, and `name` must equal the folder's name. Every check that rejects a skill
logs its reason to stderr through the standard `logging` module and never raises, since
one bad skill must not take down the rest.
"""

from __future__ import annotations

import logging
from pathlib import Path

import attrs
import yaml

logger = logging.getLogger(__name__)

SKILL_MANIFEST_NAME = "SKILL.md"
_FRONTMATTER_DELIMITER = "---"


@attrs.frozen
class SkillEntry:
    """One valid skill, as found on disk."""

    name: str
    description: str
    directory: Path


def manifest_path(skill_dir: Path) -> Path:
    """The `SKILL.md` path for a skill folder, named once so it is not repeated."""
    return skill_dir / SKILL_MANIFEST_NAME


def is_skill_folder(folder: Path) -> bool:
    """Whether `folder` holds a `SKILL.md` file, which makes it a skill rather than a group."""
    return manifest_path(folder).is_file()


def read_skill(skill_dir: Path) -> SkillEntry | None:
    """Read and validate one skill folder.

    Args:
        skill_dir: A folder holding a `SKILL.md`.

    Returns:
        The skill, or None, with the reason logged, when its `SKILL.md` is unreadable,
        its frontmatter is missing or unparsable, it lacks a string `name` or
        `description`, or its `name` differs from the folder's name.
    """
    try:
        text = manifest_path(skill_dir).read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("skipping %s: cannot read %s (%s)", skill_dir, SKILL_MANIFEST_NAME, exc)
        return None

    frontmatter = parse_frontmatter(text)
    if frontmatter is None:
        logger.warning(
            "skipping %s: no parsable YAML frontmatter in %s", skill_dir, SKILL_MANIFEST_NAME
        )
        return None

    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        logger.warning("skipping %s: frontmatter missing 'name' or 'description'", skill_dir)
        return None

    if name != skill_dir.name:
        logger.warning(
            "skipping %s: frontmatter name %r does not match its directory name",
            skill_dir,
            name,
        )
        return None

    return SkillEntry(name=name, description=description, directory=skill_dir)


def parse_frontmatter(text: str) -> dict[str, object] | None:
    """Parse the YAML block between the leading `---` delimiters, or None."""
    if not text.startswith(_FRONTMATTER_DELIMITER):
        return None
    remainder = text[len(_FRONTMATTER_DELIMITER) :]
    end = remainder.find(f"\n{_FRONTMATTER_DELIMITER}")
    if end == -1:
        return None

    try:
        parsed = yaml.safe_load(remainder[:end])
    except yaml.YAMLError:
        return None

    return parsed if isinstance(parsed, dict) else None


def list_skill_files(skill_dir: Path) -> tuple[str, ...]:
    """List every file under `skill_dir` other than its own `SKILL.md`.

    A path whose resolved target leaves `skill_dir`'s real folder, such as a symlink
    pointing outside, is left out, so a skill cannot serve something it does not own.
    """
    resolved_root = skill_dir.resolve()
    other: list[str] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        if path == manifest_path(skill_dir):
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if not resolved.is_relative_to(resolved_root):
            continue
        other.append(str(path.relative_to(skill_dir)))
    return tuple(other)
