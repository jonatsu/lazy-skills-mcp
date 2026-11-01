"""Build the catalog of skills the server serves, rescanned on every call.

Nothing here caches between calls, so a skill added or changed during a session is
visible at the next tool call without a restart. Discovery (`discovery.py`) walks each
source; this module checks that every source is usable, keeps the first skill found
under each name, and fails closed when nothing can be served, so the agent reports a
failed server rather than an empty catalog.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from lazy_skills_mcp.discovery import discover_skills
from lazy_skills_mcp.installed import installed_names
from lazy_skills_mcp.skill import SkillEntry

logger = logging.getLogger(__name__)


class SkillsDirectoryError(RuntimeError):
    """The configured sources cannot serve any skill.

    Raised when a source is missing, is not a readable folder, or when no source holds
    a valid skill. The message always names the paths involved, so the server's
    fail-closed start message points the operator at them directly.
    """


def load_catalog(sources: Sequence[Path], skip_dirs: Sequence[Path] = ()) -> tuple[SkillEntry, ...]:
    """Scan every source, in order, into a catalog sorted by name.

    Candidates are ordered by source, then by each source's walk order. The first
    candidate under a name is kept; each later one is dropped with a warning naming
    both folders. Then every skill whose name is installed in a skip folder is left
    out, since the agent already loads it natively.

    Args:
        sources: The skill sources, in priority order.
        skip_dirs: The folders the agent loads skills from natively.

    Returns:
        The served skills, sorted by name.

    Raises:
        SkillsDirectoryError: A source is missing, is not a folder, or is unreadable;
            no source holds a valid skill; or every valid skill is installed in a
            skip folder. The message names the paths.
    """
    for source in sources:
        _require_usable_source(source)

    kept = _first_skill_per_name(sources)
    if not kept:
        listed = ", ".join(str(source) for source in sources)
        raise SkillsDirectoryError(f"no valid skill found in: {listed}")

    installed = installed_names(skip_dirs)
    served = [entry for entry in kept if entry.name not in installed]
    if not served:
        listed = ", ".join(str(skip_dir) for skip_dir in skip_dirs)
        raise SkillsDirectoryError(
            f"all {len(kept)} skills found are installed in a skip folder: {listed}"
        )

    return tuple(sorted(served, key=lambda entry: entry.name))


def _first_skill_per_name(sources: Sequence[Path]) -> list[SkillEntry]:
    """Discover every source in order and keep the first skill under each name."""
    visited: set[Path] = set()
    kept: dict[str, SkillEntry] = {}
    for source in sources:
        found_any = False
        for entry in discover_skills(source, visited):
            found_any = True
            first = kept.get(entry.name)
            if first is None:
                kept[entry.name] = entry
            else:
                logger.warning(
                    "skipping %s: skill %r is already served from %s",
                    entry.directory,
                    entry.name,
                    first.directory,
                )
        if not found_any and len(sources) > 1:
            logger.warning("skills source holds no valid skill: %s", source)
    return list(kept.values())


def _require_usable_source(source: Path) -> None:
    """Raise unless `source` is a folder the server can list."""
    if not source.is_dir():
        raise SkillsDirectoryError(f"skills source not found: {source}")
    try:
        _ = next(source.iterdir(), None)
    except OSError as exc:
        raise SkillsDirectoryError(f"skills source unreadable: {source} ({exc})") from exc
