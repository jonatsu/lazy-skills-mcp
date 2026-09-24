"""The MCP tool layer, exercised end-to-end through the SDK's in-memory client."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.types import TextContent

from skillserverlib.server import build_server

pytestmark = pytest.mark.anyio


async def test_find_skills_with_no_query_returns_the_whole_catalog(skills_dir: Path) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {})

    assert result.is_error is not True
    names = sorted(entry["name"] for entry in result.structured_content["skills"])
    assert names == ["embedded-linux-bringup", "nix-flakes"]


async def test_find_skills_matches_every_term_case_insensitively(skills_dir: Path) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "EMBEDDED board"})

    names = [entry["name"] for entry in result.structured_content["skills"]]
    assert names == ["embedded-linux-bringup"]


async def test_find_skills_with_no_matching_term_returns_nothing(skills_dir: Path) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "nonexistent-term"})

    assert result.structured_content["skills"] == []


async def test_find_skills_description_embeds_the_alphabetical_catalog(
    skills_dir: Path,
) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()

    (find_skills_tool,) = [t for t in tools.tools if t.name == "find_skills"]
    assert find_skills_tool.description is not None
    description = find_skills_tool.description
    assert description.index("embedded-linux-bringup") < description.index("nix-flakes")


async def test_load_skill_returns_content_directory_and_files(tmp_path: Path) -> None:
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody text\n", encoding="utf-8"
    )
    (skill_dir / "references" / "notes.md").write_text("notes", encoding="utf-8")

    server = build_server(root)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "my-skill"})

    content = result.structured_content
    assert content["content"].startswith("---\nname: my-skill")
    assert content["directory"] == str(skill_dir.resolve())
    assert content["files"] == ["references/notes.md"]


async def test_load_skill_with_an_unknown_name_names_the_closest_matches(
    skills_dir: Path,
) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "nix-flake"})

    assert result.is_error is True
    (text_content,) = result.content
    assert isinstance(text_content, TextContent)
    assert "nix-flakes" in text_content.text


async def test_building_the_server_with_a_missing_directory_fails_closed(
    tmp_path: Path,
) -> None:
    from skillserverlib.catalog import SkillsDirectoryError

    missing = tmp_path / "does-not-exist"
    with pytest.raises(SkillsDirectoryError, match=str(missing)):
        build_server(missing)


async def test_nothing_is_written_to_stdout_while_serving_tool_calls(
    skills_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)

    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        await client.list_tools()
        await client.call_tool("find_skills", {})
        await client.call_tool("load_skill", {"name": "nix-flakes"})
        await client.call_tool("load_skill", {"name": "does-not-exist"})

    assert captured.getvalue() == ""
