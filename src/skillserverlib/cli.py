"""Command line entry point: resolve the lazy skills directory and serve it."""

from __future__ import annotations

import argparse
import logging
import sys

from skillserverlib.catalog import SkillsDirectoryError
from skillserverlib.location import resolve_skills_dir
from skillserverlib.server import build_server


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="skill-server",
        description="Serve the lazy skill tier as MCP tools (find_skills, load_skill) over stdio.",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        metavar="DIR",
        help=(
            "Lazy skills directory (default: $XDG_DATA_HOME/agent-skills/lazy, "
            "else ~/.local/share/agent-skills/lazy)"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Resolve the lazy skills directory, build the server, and serve it over stdio.

    Args:
        argv: Command line arguments, or None to read from ``sys.argv``.

    Returns:
        0 after a clean shutdown. When the resolved directory cannot serve a
        catalog, the failure is printed to stderr and 1 is returned instead of
        starting, so the harness reports a failed MCP server rather than an empty
        catalog.
    """
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    skills_dir = resolve_skills_dir(args.skills_dir)
    try:
        server = build_server(skills_dir)
    except SkillsDirectoryError as exc:
        print(f"skill-server: {exc}", file=sys.stderr)
        return 1

    server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
