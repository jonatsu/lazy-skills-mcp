"""Scan the lazy skills directory into a catalog of valid skills.

The catalog is rescanned by calling `load_catalog` again; nothing here caches
between calls, matching the design's choice to keep a Kasetto sync visible without a
restart. Every check that skips a skill logs its reason to stderr through the
standard `logging` module and never raises for it, since one bad skill must not take
down the rest.
"""

from __future__ import annotations

import logging
from pathlib import Path

import attrs
import yaml

logger = logging.getLogger(__name__)

SKILL_MANIFEST_NAME = "SKILL.md"
_FRONTMATTER_DELIMITER = "---"


class SkillsDirectoryError(RuntimeError):
    """The lazy skills directory cannot serve any skill.

    Raised when the directory is missing, is not a readable directory, or holds no
    valid skill. The message always names the path that was tried, so the server's
    fail-closed start message points the operator at it directly.
    """


@attrs.frozen
class SkillEntry:
    """One valid lazy skill, as found on disk."""

    name: str
    description: str
    directory: Path
    files: tuple[str, ...]


def load_catalog(skills_dir: Path) -> tuple[SkillEntry, ...]:
    """Scan `skills_dir` one level deep into a catalog sorted by name.

    Args:
        skills_dir: The resolved lazy skills directory, following the Kasetto flat
            layout: each immediate child is a skill directory holding its own
            ``SKILL.md``.

    Returns:
        Every valid skill found, sorted by name.

    Raises:
        SkillsDirectoryError: `skills_dir` is missing, is not a readable directory,
            or holds no valid skill. The message names `skills_dir`.
    """
    if not skills_dir.is_dir():
        raise SkillsDirectoryError(f"lazy skills directory not found: {skills_dir}")

    try:
        children = sorted(skills_dir.iterdir())
    except OSError as exc:
        raise SkillsDirectoryError(
            f"lazy skills directory unreadable: {skills_dir} ({exc})"
        ) from exc

    entries = [
        entry
        for child in children
        if child.is_dir()
        for entry in (_load_skill_entry(child),)
        if entry is not None
    ]

    if not entries:
        raise SkillsDirectoryError(f"lazy skills directory holds no valid skill: {skills_dir}")

    return tuple(sorted(entries, key=lambda entry: entry.name))


def _load_skill_entry(skill_dir: Path) -> SkillEntry | None:
    """Load one skill directory, or None (logged) when it is not a valid skill."""
    manifest = skill_dir / SKILL_MANIFEST_NAME
    if not manifest.is_file():
        logger.warning("skipping %s: no %s", skill_dir, SKILL_MANIFEST_NAME)
        return None

    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("skipping %s: cannot read %s (%s)", skill_dir, SKILL_MANIFEST_NAME, exc)
        return None

    frontmatter = _parse_frontmatter(text)
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

    return SkillEntry(
        name=name,
        description=description,
        directory=skill_dir,
        files=_list_other_files(skill_dir),
    )


def _parse_frontmatter(text: str) -> dict[str, object] | None:
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


def _list_other_files(skill_dir: Path) -> tuple[str, ...]:
    """List every file under `skill_dir` other than its own `SKILL.md`.

    A path whose resolved target leaves `skill_dir` — a symlink pointing outside —
    is left out, so a skill cannot serve something it does not own.
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


def manifest_path(skill_dir: Path) -> Path:
    """The `SKILL.md` path for a skill directory, named once so it is not repeated."""
    return skill_dir / SKILL_MANIFEST_NAME
