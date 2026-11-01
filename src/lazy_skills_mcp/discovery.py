"""Walk one skill source and yield the valid skills it holds, in a fixed order.

The layout rule is the only rule, so any skill tool's output works: a folder holding
`SKILL.md` is a skill, and the walk does not search inside it; any other folder is a
group, and the walk searches its child folders in sorted name order. Hidden folders
are skipped. The source itself is depth 0, so a source that is a skill serves that one
skill. Symlinked folders are followed. Each real folder is searched once per scan, unless
a shorter path reaches it again; this ends symlink cycles and yields each skill once.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from lazy_skills_mcp.skill import SkillEntry, is_child_folder, is_skill_folder, read_skill

logger = logging.getLogger(__name__)

MAX_DEPTH = 8


def discover_skills(source: Path, visited: dict[Path, int]) -> Iterator[SkillEntry]:
    """Yield the valid skills under `source`, depth first in sorted name order.

    Args:
        source: The folder to walk. The caller has checked that it is a readable folder.
        visited: Real paths already visited in this scan, mapped to the shallowest depth
            at which each was reached. The walk passes over a skill folder it has seen
            at any depth, and a group it has already reached at the same or a shallower
            depth, without a log line. A group reached again by a shorter path is
            searched again, so the depth limit never hides a skill that a shorter path
            reaches.

    Yields:
        Each valid skill once. Invalid skills, unreadable folders, and groups at the
        depth limit are logged and yield nothing.
    """
    yield from _visit(source, 0, visited)


def _visit(folder: Path, depth: int, visited: dict[Path, int]) -> Iterator[SkillEntry]:
    """Visit one folder at `depth` below its source."""
    try:
        real_path = folder.resolve()
    except OSError as exc:
        logger.warning("skipping %s: cannot resolve its real path (%s)", folder, exc)
        return
    seen_at = visited.get(real_path)
    if seen_at is not None and seen_at <= depth:
        return
    visited[real_path] = depth

    if is_skill_folder(folder):
        if seen_at is None:
            entry = read_skill(folder)
            if entry is not None:
                yield entry
        return

    if depth >= MAX_DEPTH:
        logger.warning("not searching %s: depth limit of %d reached", folder, MAX_DEPTH)
        return

    try:
        children = sorted(
            child
            for child in folder.iterdir()
            if not child.name.startswith(".") and is_child_folder(child)
        )
    except OSError as exc:
        logger.warning("skipping %s: cannot list it (%s)", folder, exc)
        return

    for child in children:
        yield from _visit(child, depth + 1, visited)
