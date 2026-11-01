"""The MCP tool layer: `find_skills` and `load_skill` over the lazy skill catalog.

Both tools are read-only and world-closed, and rescan the catalog on every call
(`load_catalog` never caches), so a Kasetto sync during a session is visible at the
next call. Only `find_skills`'s own tool description is fixed for the server's
lifetime, built once here from the catalog at construction time, since Codex does
not act on `list_changed` notifications.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from lazy_skills_mcp.catalog import load_catalog
from lazy_skills_mcp.ranking import MAX_RESULTS, rank_entries
from lazy_skills_mcp.skill import list_skill_files, manifest_path

_FIND_SKILLS_TITLE = "Find skills"
_LOAD_SKILL_TITLE = "Load skill"
_SERVER_INSTRUCTIONS = (
    "Skills missing from your preloaded skill list live here. When a request falls in a "
    "domain the find_skills catalog covers, call find_skills before answering or searching "
    "the web, then load_skill on the best match and follow its instructions."
)
_LOAD_SKILL_DESCRIPTION = (
    "Load a skill's full SKILL.md instructions, its directory's absolute path, and its "
    "other files' relative paths. Call it on a name from find_skills, then follow the "
    "instructions for the work; read references and run scripts from that directory."
)
_CLOSEST_MATCH_COUNT = 3


def _read_only_annotations(title: str) -> ToolAnnotations:
    """Every hint set explicitly: both tools only read local files, repeatably."""
    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )


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


def _find_skills_description(catalog_names: list[str]) -> str:
    """Build `find_skills`'s tool description, embedding the alphabetical catalog."""
    catalog_line = ", ".join(catalog_names) if catalog_names else "(none)"
    return (
        f"Find skills missing from your preloaded skill list: {catalog_line}. "
        "Call this first when a request falls in one of these skills' domains, before "
        "answering or searching the web, then load_skill on the best match. Results are "
        "ranked: a skill matches when any query word appears in its name or description, "
        f"rare words and name matches rank higher, and at most {MAX_RESULTS} return. An "
        "empty query returns the whole catalog."
    )


def build_server(sources: Sequence[Path]) -> MCPServer[None]:
    """Build the lazy-skills-mcp `MCPServer` over `sources`.

    Args:
        sources: The skill sources, in priority order.

    Returns:
        An `MCPServer` exposing `find_skills` and `load_skill`, ready for `run()`.

    Raises:
        SkillsDirectoryError: A source is missing or unreadable, or no source holds
            a valid skill. The catalog is scanned once here, both to build
            `find_skills`'s fixed description and to fail the server closed before
            it ever starts.
    """
    startup_names = sorted(entry.name for entry in load_catalog(sources))

    server: MCPServer[None] = MCPServer("lazy-skills-mcp", instructions=_SERVER_INSTRUCTIONS)

    @server.tool(
        title=_FIND_SKILLS_TITLE,
        description=_find_skills_description(startup_names),
        annotations=_read_only_annotations(_FIND_SKILLS_TITLE),
    )
    def find_skills(query: str | None = None) -> FindSkillsResult:
        matching = rank_entries(load_catalog(sources), query)
        return FindSkillsResult(
            skills=[
                SkillSummary(name=entry.name, description=entry.description) for entry in matching
            ]
        )

    @server.tool(
        title=_LOAD_SKILL_TITLE,
        description=_LOAD_SKILL_DESCRIPTION,
        annotations=_read_only_annotations(_LOAD_SKILL_TITLE),
    )
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
        catalog = load_catalog(sources)
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
            files=list(list_skill_files(entry.directory)),
        )

    return server
