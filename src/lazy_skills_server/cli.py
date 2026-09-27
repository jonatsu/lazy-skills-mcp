"""Command line entry point: resolve the lazy skills directory and serve it."""

from __future__ import annotations

import argparse
import logging
import sys

from lazy_skills_server.catalog import SkillsDirectoryError
from lazy_skills_server.location import resolve_skills_dir
from lazy_skills_server.server import build_server


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="lazy-skills-server",
        description="Serve the lazy skill tier as MCP tools (find_skills, load_skill) over stdio.",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        metavar="DIR",
        help=(
            "Lazy skills directory. Precedence: this flag, then the "
            "LAZY_SKILLS_SERVER_SKILLS_DIR environment variable, then "
            "$XDG_DATA_HOME/lazy-skills-server/skills, else "
            "~/.local/share/lazy-skills-server/skills"
        ),
    )
    parser.add_argument(
        "--print-skills-dir",
        action="store_true",
        help=(
            "Print the resolved skills directory and exit, without checking that it "
            "exists and without starting the server."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Resolve the lazy skills directory, build the server, and serve it over stdio.

    Args:
        argv: Command line arguments, or None to read from ``sys.argv``.

    Returns:
        0 after a clean shutdown. With ``--print-skills-dir``, 0 immediately after
        printing the resolved directory, whether or not it exists. When the resolved
        directory cannot serve a catalog, the failure is printed to stderr and 1 is
        returned instead of starting, so the harness reports a failed MCP server
        rather than an empty catalog.
    """
    args = _parse_args(argv)

    skills_dir = resolve_skills_dir(args.skills_dir)
    if args.print_skills_dir:
        print(skills_dir)
        return 0

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        server = build_server(skills_dir)
    except SkillsDirectoryError as exc:
        print(f"lazy-skills-server: {exc}", file=sys.stderr)
        return 1

    server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
