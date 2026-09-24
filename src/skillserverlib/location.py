"""Resolve the lazy skills directory, with no arithmetic over this package's own path.

One function decides the answer, by the precedence the design fixes: an explicit
``--skills-dir`` argument, then ``$XDG_DATA_HOME/agent-skills/lazy``, then
``~/.local/share/agent-skills/lazy``. The function is a pure computation over its
argument and the environment; it never touches the filesystem, so callers decide
separately whether the resolved path actually exists.
"""

from __future__ import annotations

import os
from pathlib import Path

XDG_DATA_HOME_VAR = "XDG_DATA_HOME"
LAZY_SKILLS_RELATIVE_PATH = ("agent-skills", "lazy")


def resolve_skills_dir(explicit: str | None) -> Path:
    """Resolve the lazy skills directory by the documented precedence.

    Args:
        explicit: The ``--skills-dir`` command line value, or ``None`` when the
            caller passed nothing. An empty string is treated the same as ``None``,
            since an empty argument carries no directory.

    Returns:
        ``explicit`` as a path when given; otherwise
        ``$XDG_DATA_HOME/agent-skills/lazy`` when that variable is set and
        non-empty; otherwise ``~/.local/share/agent-skills/lazy``.
    """
    if explicit:
        return Path(explicit)

    xdg_data_home = os.environ.get(XDG_DATA_HOME_VAR)
    if xdg_data_home:
        return Path(xdg_data_home, *LAZY_SKILLS_RELATIVE_PATH)

    return Path.home() / ".local" / "share" / Path(*LAZY_SKILLS_RELATIVE_PATH)
