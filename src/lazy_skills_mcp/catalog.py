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
from lazy_skills_mcp.skill import SkillEntry

logger = logging.getLogger(__name__)


class SkillsDirectoryError(RuntimeError):
    """The configured sources cannot serve any skill.

    Raised when a source is missing, is not a readable folder, or when no source holds
    a valid skill. The message always names the paths involved, so the server's
    fail-closed start message points the operator at them directly.
    """


def load_catalog(sources: Sequence[Path]) -> tuple[SkillEntry, ...]:
    """Scan every source, in order, into a catalog sorted by name.

    Candidates are ordered by source, then by each source's walk order. The first
    candidate under a name is kept; each later one is dropped with a warning naming
    both folders.

    Args:
        sources: The skill sources, in priority order.

    Returns:
        The kept skills, sorted by name.

    Raises:
        SkillsDirectoryError: A source is missing, is not a folder, or is unreadable;
            or no source holds a valid skill. The message names the paths.
    """
    for source in sources:
        _require_usable_source(source)

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

    if not kept:
        listed = ", ".join(str(source) for source in sources)
        raise SkillsDirectoryError(f"no valid skill found in: {listed}")

    return tuple(sorted(kept.values(), key=lambda entry: entry.name))


def _require_usable_source(source: Path) -> None:
    """Raise unless `source` is a folder the server can list."""
    if not source.is_dir():
        raise SkillsDirectoryError(f"skills source not found: {source}")
    try:
        _ = next(source.iterdir(), None)
    except OSError as exc:
        raise SkillsDirectoryError(f"skills source unreadable: {source} ({exc})") from exc
