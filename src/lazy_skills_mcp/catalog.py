"""Build the catalog of skills the server serves, rescanned on every call.

Nothing here caches between calls, so a skill added or changed during a session is
visible at the next tool call without a restart. Discovery (`discovery.py`) walks the
source; this module checks that the source is usable and fails closed when it is not,
so the agent reports a failed server rather than an empty catalog.
"""

from __future__ import annotations

from pathlib import Path

from lazy_skills_mcp.discovery import discover_skills
from lazy_skills_mcp.skill import SkillEntry


class SkillsDirectoryError(RuntimeError):
    """The skills directory cannot serve any skill.

    Raised when the directory is missing, is not a readable directory, or holds no
    valid skill. The message always names the path that was tried, so the server's
    fail-closed start message points the operator at it directly.
    """


def load_catalog(skills_dir: Path) -> tuple[SkillEntry, ...]:
    """Scan `skills_dir` into a catalog sorted by name.

    Args:
        skills_dir: The skills directory, flat or grouped; `discover_skills` applies
            the layout rule.

    Returns:
        Every valid skill found, sorted by name.

    Raises:
        SkillsDirectoryError: `skills_dir` is missing, is not a readable directory,
            or holds no valid skill. The message names `skills_dir`.
    """
    if not skills_dir.is_dir():
        raise SkillsDirectoryError(f"lazy skills directory not found: {skills_dir}")

    try:
        _ = next(skills_dir.iterdir(), None)
    except OSError as exc:
        raise SkillsDirectoryError(
            f"lazy skills directory unreadable: {skills_dir} ({exc})"
        ) from exc

    entries = list(discover_skills(skills_dir, set()))
    if not entries:
        raise SkillsDirectoryError(f"lazy skills directory holds no valid skill: {skills_dir}")

    return tuple(sorted(entries, key=lambda entry: entry.name))
