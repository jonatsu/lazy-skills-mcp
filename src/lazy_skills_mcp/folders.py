"""Folder checks for the discovery walk and the skip folders, each with its own error policy.

`Path.is_dir` raises on Python 3.12 and 3.13 when a parent folder cannot be searched,
and a symlink can point anywhere. `is_reachable_folder` treats any error as "no", for a
skip folder that only needs a warning. `is_listed_child_folder` lets a parent's error
reach the caller's listing handler and handles a bad symlink itself, for walking a
folder's children.
"""

from __future__ import annotations

import errno
import logging
import stat
from pathlib import Path

logger = logging.getLogger(__name__)


def is_reachable_folder(path: Path) -> bool:
    """Whether `path` is a folder, treating any filesystem error as "no"."""
    try:
        return path.is_dir()
    except OSError:
        return False


def is_listed_child_folder(path: Path) -> bool:
    """Whether a child from a folder listing is a folder, raising when its parent cannot be searched.

    The child's own entry is checked first, and an error there, such as a permission
    error from a parent that can be listed but not searched, propagates so the caller's
    listing handler logs the parent. A symlinked child is then followed on its own: a
    broken or looping link is simply not a folder, and a target that cannot be reached
    is logged and skipped, so one bad link never hides its siblings.
    """
    try:
        entry_mode = path.lstat().st_mode
    except FileNotFoundError:
        return False
    if not stat.S_ISLNK(entry_mode):
        return stat.S_ISDIR(entry_mode)
    try:
        return stat.S_ISDIR(path.stat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        if exc.errno != errno.ELOOP:
            logger.warning("skipping %s: cannot reach its target (%s)", path, exc)
        return False
