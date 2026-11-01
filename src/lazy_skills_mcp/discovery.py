"""Walk one skill source and yield the valid skills it holds, in a fixed order.

The layout rule is the only rule, so any skill tool's output works: a folder holding
`SKILL.md` is a skill, and the walk does not search inside it; any other folder is a
group, and the walk searches its child folders in sorted name order. Hidden folders
are skipped. The source itself is depth 0, so a source that is a skill serves that one
skill. Symlinked folders are followed, and each real folder is visited once per scan,
which ends symlink cycles and drops a second path to the same skill.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from lazy_skills_mcp.skill import SkillEntry, is_skill_folder, read_skill

logger = logging.getLogger(__name__)

MAX_DEPTH = 8


def discover_skills(source: Path, visited: set[Path]) -> Iterator[SkillEntry]:
    """Yield the valid skills under `source`, depth first in sorted name order.

    Args:
        source: The folder to walk. The caller has checked that it is a readable folder.
        visited: Real paths already visited in this scan. The walk adds every folder it
            visits and passes over any folder already present, without a log line.

    Yields:
        Each valid skill. Invalid skills, unreadable folders, and groups at the depth
        limit are logged and yield nothing.
    """
    yield from _visit(source, 0, visited)


def _visit(folder: Path, depth: int, visited: set[Path]) -> Iterator[SkillEntry]:
    """Visit one folder at `depth` below its source."""
    try:
        real_path = folder.resolve()
    except OSError as exc:
        logger.warning("skipping %s: cannot resolve its real path (%s)", folder, exc)
        return
    if real_path in visited:
        return
    visited.add(real_path)

    if is_skill_folder(folder):
        entry = read_skill(folder)
        if entry is not None:
            yield entry
        return

    if depth >= MAX_DEPTH:
        logger.warning("not searching %s: depth limit of %d reached", folder, MAX_DEPTH)
        return

    try:
        children = sorted(
            child for child in folder.iterdir() if not child.name.startswith(".") and child.is_dir()
        )
    except OSError as exc:
        logger.warning("skipping %s: cannot list it (%s)", folder, exc)
        return

    for child in children:
        yield from _visit(child, depth + 1, visited)
