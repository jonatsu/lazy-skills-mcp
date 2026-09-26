"""Resolve the lazy skills directory, with no arithmetic over this package's own path.

One function decides the answer, by the precedence the design fixes: an explicit
``--skills-dir`` argument, then the ``LAZY_SKILLS_SERVER_SKILLS_DIR`` environment
variable, then ``$XDG_DATA_HOME/lazy-skills-server/skills``, then
``~/.local/share/lazy-skills-server/skills``. The function is a pure computation
over its argument and the environment; it never touches the filesystem, so callers
decide separately whether the resolved path actually exists.
"""

from __future__ import annotations

import os
from pathlib import Path

SKILLS_DIR_ENV_VAR = "LAZY_SKILLS_SERVER_SKILLS_DIR"
XDG_DATA_HOME_VAR = "XDG_DATA_HOME"
LAZY_SKILLS_RELATIVE_PATH = ("lazy-skills-server", "skills")


def resolve_skills_dir(explicit: str | None) -> Path:
    """Resolve the lazy skills directory by the documented precedence.

    Args:
        explicit: The ``--skills-dir`` command line value, or ``None`` when the
            caller passed nothing. An empty string is treated the same as ``None``,
            since an empty argument carries no directory.

    Returns:
        ``explicit`` as a path when given; otherwise the ``LAZY_SKILLS_SERVER_SKILLS_DIR``
        environment variable when set and non-empty; otherwise
        ``$XDG_DATA_HOME/lazy-skills-server/skills`` when ``XDG_DATA_HOME`` is set
        and non-empty; otherwise ``~/.local/share/lazy-skills-server/skills``.
    """
    if explicit:
        return Path(explicit)

    env_skills_dir = os.environ.get(SKILLS_DIR_ENV_VAR)
    if env_skills_dir:
        return Path(env_skills_dir)

    xdg_data_home = os.environ.get(XDG_DATA_HOME_VAR)
    if xdg_data_home:
        return Path(xdg_data_home, *LAZY_SKILLS_RELATIVE_PATH)

    return Path.home() / ".local" / "share" / Path(*LAZY_SKILLS_RELATIVE_PATH)
