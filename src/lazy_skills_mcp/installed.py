"""Read the skip folders: the names of the skills an agent already loads natively.

A skip folder is read flat, one skill per child folder, because that is the layout
agents document for their own skill folders. A child counts as installed under its
folder name, and also under its frontmatter `name` when that parses, so a skill stays
out of the catalog when either name matches. Anything unparsable is ignored silently:
the folder name alone still counts.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from lazy_skills_mcp.skill import manifest_path, parse_frontmatter

logger = logging.getLogger(__name__)


def installed_names(skip_dirs: Sequence[Path]) -> frozenset[str]:
    """Collect the installed skill names from every skip folder.

    Args:
        skip_dirs: The folders the agent loads skills from natively.

    Returns:
        Every child folder's name and every parsable frontmatter `name` found. A
        missing or unreadable skip folder contributes nothing and logs one warning
        naming it, since every skip folder is named explicitly and a missing one is
        most likely a typo.
    """
    names: set[str] = set()
    for skip_dir in skip_dirs:
        if not skip_dir.is_dir():
            logger.warning("skip folder not found, nothing skipped from it: %s", skip_dir)
            continue
        try:
            children = [child for child in skip_dir.iterdir() if child.is_dir()]
        except OSError as exc:
            logger.warning(
                "skip folder unreadable, nothing skipped from it: %s (%s)", skip_dir, exc
            )
            continue
        for child in children:
            names.add(child.name)
            frontmatter_name = _frontmatter_name(child)
            if frontmatter_name is not None:
                names.add(frontmatter_name)
    return frozenset(names)


def _frontmatter_name(skill_dir: Path) -> str | None:
    """The `name` in `skill_dir`'s SKILL.md frontmatter, or None when it does not parse."""
    try:
        text = manifest_path(skill_dir).read_text(encoding="utf-8")
    except OSError:
        return None
    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name") if frontmatter is not None else None
    return name if isinstance(name, str) else None
