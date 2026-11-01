"""Resolve where the server reads skills from and which folders it skips.

Sources come from the first of these that yields a path, and a layer never merges with
a lower one: every non-empty ``--skills-dir`` value, in order; then the
``LAZY_SKILLS_MCP_SKILLS_DIR`` environment variable, split like ``PATH``; then
``$XDG_DATA_HOME/lazy-skills-mcp/skills``; then ``~/.local/share/lazy-skills-mcp/skills``.
Skip folders come only from ``--skip-installed-in``. A leading ``~`` is expanded in
every path, because agents start MCP servers without a shell to expand it.

Resolution is a pure computation over its arguments and the environment; it never
touches the filesystem, so callers decide separately whether the paths exist.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import attrs

SKILLS_DIR_ENV_VAR = "LAZY_SKILLS_MCP_SKILLS_DIR"
XDG_DATA_HOME_VAR = "XDG_DATA_HOME"
DEFAULT_RELATIVE_PATH = ("lazy-skills-mcp", "skills")


@attrs.frozen
class SkillSources:
    """The resolved configuration: where to read skills, and which folders to skip."""

    sources: tuple[Path, ...]
    skip_dirs: tuple[Path, ...]


def resolve_skill_sources(skills_dirs: Sequence[str], skip_dirs: Sequence[str]) -> SkillSources:
    """Resolve the sources and skip folders by the documented precedence.

    Args:
        skills_dirs: The ``--skills-dir`` values in command-line order; empty values
            are ignored.
        skip_dirs: The ``--skip-installed-in`` values in command-line order; empty
            values are ignored.

    Returns:
        The sources from the first layer that yields at least one path, and the skip
        folders, each with a leading ``~`` expanded.
    """
    sources = _non_empty_paths(skills_dirs) or _sources_from_environment() or (_default_source(),)
    return SkillSources(sources=sources, skip_dirs=_non_empty_paths(skip_dirs))


def _sources_from_environment() -> tuple[Path, ...]:
    """The variable's entries split on ``os.pathsep``, or an empty tuple when unset."""
    raw = os.environ.get(SKILLS_DIR_ENV_VAR, "")
    return _non_empty_paths(raw.split(os.pathsep))


def _default_source() -> Path:
    """``$XDG_DATA_HOME/lazy-skills-mcp/skills``, else ``~/.local/share/lazy-skills-mcp/skills``."""
    xdg_data_home = os.environ.get(XDG_DATA_HOME_VAR)
    data_home = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return data_home.joinpath(*DEFAULT_RELATIVE_PATH)


def _non_empty_paths(values: Sequence[str]) -> tuple[Path, ...]:
    """The non-empty values as paths, in order, with a leading ``~`` expanded."""
    return tuple(_expand_home(value) for value in values if value)


def _expand_home(value: str) -> Path:
    """Expand a leading ``~`` or ``~/`` to the home folder; leave anything else as given."""
    if value == "~":
        return Path.home()
    if value.startswith("~/"):
        return Path.home() / value.removeprefix("~/")
    return Path(value)
