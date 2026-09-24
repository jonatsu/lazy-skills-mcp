"""The MCP tool layer: `find_skills` and `load_skill` over the lazy skill catalog.

Both tools are read-only and world-closed, and rescan the catalog on every call
(`load_catalog` never caches), so a Kasetto sync during a session is visible at the
next call. Only `find_skills`'s own tool description is fixed for the server's
lifetime, built once here from the catalog at construction time, since Codex does
not act on `list_changed` notifications.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from skillserverlib.catalog import SkillEntry, load_catalog, manifest_path

_READ_ONLY_ANNOTATIONS = ToolAnnotations(read_only_hint=True, open_world_hint=False)
_CLOSEST_MATCH_COUNT = 3


class SkillSummary(TypedDict):
    """One catalog entry as returned by `find_skills`."""

    name: str
    description: str


class FindSkillsResult(TypedDict):
    """`find_skills`'s structured result."""

    skills: list[SkillSummary]


class LoadSkillResult(TypedDict):
    """`load_skill`'s structured result."""

    content: str
    directory: str
    files: list[str]


def _matches_every_term(entry: SkillEntry, terms: list[str]) -> bool:
    """Whether every term appears, case-insensitively, in the entry's name or description."""
    haystack = f"{entry.name} {entry.description}".lower()
    return all(term in haystack for term in terms)


def _find_skills_description(catalog_names: list[str]) -> str:
    """Build `find_skills`'s tool description, embedding the alphabetical catalog."""
    catalog_line = ", ".join(catalog_names) if catalog_names else "(none)"
    return (
        "Search the lazy skill catalog. A skill matches when every "
        "whitespace-separated query term appears, case-insensitively, in its name "
        "or its description; an empty or missing query returns the whole catalog. "
        "Load a matching skill's full instructions with load_skill. "
        f"Known skills: {catalog_line}."
    )


def build_server(skills_dir: Path) -> MCPServer[None]:
    """Build the skill-server `MCPServer` over `skills_dir`.

    Args:
        skills_dir: The resolved lazy skills directory.

    Returns:
        An `MCPServer` exposing `find_skills` and `load_skill`, ready for `run()`.

    Raises:
        SkillsDirectoryError: `skills_dir` is missing, unreadable, or holds no
            valid skill. The catalog is scanned once here, both to build
            `find_skills`'s fixed description and to fail the server closed before
            it ever starts, per the design's failure handling.
    """
    startup_names = sorted(entry.name for entry in load_catalog(skills_dir))

    server: MCPServer[None] = MCPServer("skill-server")

    @server.tool(
        description=_find_skills_description(startup_names),
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def find_skills(query: str | None = None) -> FindSkillsResult:
        catalog = load_catalog(skills_dir)
        terms = query.lower().split() if query else []
        matching = [entry for entry in catalog if _matches_every_term(entry, terms)]
        return FindSkillsResult(
            skills=[
                SkillSummary(name=entry.name, description=entry.description) for entry in matching
            ]
        )

    @server.tool(annotations=_READ_ONLY_ANNOTATIONS)
    def load_skill(name: str) -> LoadSkillResult:
        """Load one lazy skill's full SKILL.md text, directory, and file list.

        Args:
            name: The skill's catalog name, as returned by `find_skills`.

        Returns:
            The skill's `SKILL.md` content, its absolute directory, and the
            relative paths of its other files.

        Raises:
            ToolError: `name` matches no catalog entry; the message names the
                closest catalog names.
        """
        catalog = load_catalog(skills_dir)
        by_name = {entry.name: entry for entry in catalog}
        entry = by_name.get(name)
        if entry is None:
            closest = difflib.get_close_matches(name, by_name.keys(), n=_CLOSEST_MATCH_COUNT)
            suggestion = f" Closest matches: {', '.join(closest)}." if closest else ""
            raise ToolError(f"unknown skill {name!r}.{suggestion}")

        content = manifest_path(entry.directory).read_text(encoding="utf-8")
        return LoadSkillResult(
            content=content,
            directory=str(entry.directory.resolve()),
            files=list(entry.files),
        )

    return server
