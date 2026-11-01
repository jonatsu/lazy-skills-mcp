"""Command line entry point: resolve the skill sources and serve them over stdio."""

from __future__ import annotations

import argparse
import logging
import sys

from lazy_skills_mcp.catalog import SkillsDirectoryError
from lazy_skills_mcp.location import resolve_skill_sources
from lazy_skills_mcp.server import build_server


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="lazy-skills-mcp",
        description="Serve Agent Skills on demand as MCP tools (find_skills, load_skill) over stdio.",
    )
    parser.add_argument(
        "--skills-dir",
        action="append",
        default=[],
        metavar="DIR",
        help=(
            "A folder to read skills from, flat or grouped. Repeat it to read several, "
            "in priority order. Default: the LAZY_SKILLS_MCP_SKILLS_DIR list, then "
            "$XDG_DATA_HOME/lazy-skills-mcp/skills, else ~/.local/share/lazy-skills-mcp/skills"
        ),
    )
    parser.add_argument(
        "--skip-installed-in",
        action="append",
        default=[],
        metavar="DIR",
        help=(
            "A folder the agent loads skills from natively; skills installed there are "
            "not served. Repeatable. Default: none."
        ),
    )
    parser.add_argument(
        "--print-skills-dir",
        action="store_true",
        help=(
            "Print the resolved skill sources, one per line, and exit, without checking "
            "that they exist and without starting the server."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Resolve the skill sources, build the server, and serve it over stdio.

    Args:
        argv: Command line arguments, or None to read from ``sys.argv``.

    Returns:
        0 after a clean shutdown. With ``--print-skills-dir``, 0 immediately after
        printing the resolved sources, whether or not they exist. When the sources
        cannot serve a catalog, the failure is printed to stderr and 1 is returned
        instead of starting, so the agent reports a failed MCP server rather than an
        empty catalog.
    """
    args = _parse_args(argv)
    skills_dirs: list[str] = args.skills_dir
    skip_dirs: list[str] = args.skip_installed_in

    config = resolve_skill_sources(skills_dirs, skip_dirs)
    if args.print_skills_dir:
        for source in config.sources:
            print(source)
        return 0

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        server = build_server(config.sources, config.skip_dirs)
    except SkillsDirectoryError as exc:
        print(f"lazy-skills-mcp: {exc}", file=sys.stderr)
        return 1

    server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
