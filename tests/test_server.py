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


async def test_find_skills_with_an_empty_string_query_returns_the_whole_catalog(
    skills_dir: Path,
) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": ""})

    names = sorted(entry["name"] for entry in result.structured_content["skills"])
    assert names == ["embedded-linux-bringup", "nix-flakes"]


async def test_find_skills_requires_every_term_and_does_not_match_on_any_one_term(
    skills_dir: Path,
) -> None:
    """Each term matches a different entry individually, but no entry has both.

    An AND-vs-OR mutation of `_matches_every_term` (`all` -> `any`) survives every
    other existing test, because their queries always put both terms on the same
    matching entry. This query is chosen so OR matching would wrongly return both
    entries, while AND matching correctly returns neither.
    """
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "embedded flakes"})

    assert result.structured_content["skills"] == []


async def test_find_skills_matches_case_insensitively_against_description_content(
    tmp_path: Path,
) -> None:
    """The description itself carries mixed case, not just the query.

    A haystack-casing mutation (dropping `.lower()` on the entry text) survives
    the existing case-insensitivity test, because every fixture description is
    already all-lowercase; only the query varies in case there.
    """
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Handles YOCTO Image Builds\n---\nbody\n",
        encoding="utf-8",
    )

    server = build_server(root)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "yocto image"})

    names = [entry["name"] for entry in result.structured_content["skills"]]
    assert names == ["my-skill"]


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


async def test_load_skill_returns_the_full_manifest_text_exactly(tmp_path: Path) -> None:
    """A prefix check alone cannot tell full text apart from a truncated copy.

    A mutation that truncates `content` to its first 20 characters survives
    `test_load_skill_returns_content_directory_and_files`, because the manifest
    happens to start with exactly that many matching characters. This test
    compares against the manifest's own full text instead of a fixed prefix.
    """
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    skill_dir.mkdir(parents=True)
    manifest_text = (
        "---\nname: my-skill\ndescription: does a thing\n---\n"
        "body text that runs on for a while, well past any short fixed prefix\n"
    )
    (skill_dir / "SKILL.md").write_text(manifest_text, encoding="utf-8")

    server = build_server(root)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "my-skill"})

    assert result.structured_content["content"] == manifest_text


async def test_load_skill_returns_an_absolute_directory_even_from_a_relative_skills_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The returned directory must be absolute regardless of how `skills_dir` was
    given to `build_server`.

    Dropping `.resolve()` on `entry.directory` survives every existing test,
    because `tmp_path` is already absolute with no symlink components to
    normalize on this platform. Passing a relative path, after chdir-ing to its
    parent, is the case where an unresolved relative path would actually surface
    as a relative `directory` in the tool result.
    """
    root = tmp_path / "lazy"
    skill_dir = root / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does a thing\n---\nbody\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    server = build_server(Path("lazy"))
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "my-skill"})

    directory = result.structured_content["directory"]
    assert Path(directory).is_absolute()
    assert directory == str(skill_dir.resolve())


async def test_load_skill_rejects_a_path_traversal_style_name_as_unknown(
    skills_dir: Path,
) -> None:
    """`load_skill` must resolve a name only against the scanned catalog, never
    as a filesystem path, so a traversal-shaped name is just another unknown
    name."""
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "../secret"})

    assert result.is_error is True
    (text_content,) = result.content
    assert isinstance(text_content, TextContent)
    assert "unknown skill" in text_content.text


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


async def test_find_skills_and_load_skill_are_declared_read_only(skills_dir: Path) -> None:
    server = build_server(skills_dir)
    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()

    by_name = {tool.name: tool for tool in tools.tools}
    for name in ("find_skills", "load_skill"):
        annotations = by_name[name].annotations
        assert annotations is not None
        assert annotations.read_only_hint is True
        assert annotations.open_world_hint is False


async def test_find_skills_description_is_fixed_while_the_catalog_rescans_on_each_call(
    tmp_path: Path,
) -> None:
    """`find_skills`'s own description is a snapshot taken at server construction;
    the catalog it searches is rescanned on every call. A skill added to disk
    after `build_server` returns must be findable and loadable, while the tool's
    fixed description must not mention it.
    """
    root = tmp_path / "lazy"
    first_skill = root / "first-skill"
    first_skill.mkdir(parents=True)
    (first_skill / "SKILL.md").write_text(
        "---\nname: first-skill\ndescription: exists at startup\n---\nbody\n", encoding="utf-8"
    )

    server = build_server(root)

    second_skill = root / "second-skill"
    second_skill.mkdir(parents=True)
    (second_skill / "SKILL.md").write_text(
        "---\nname: second-skill\ndescription: added after startup\n---\nbody\n",
        encoding="utf-8",
    )

    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()
        (find_skills_tool,) = [t for t in tools.tools if t.name == "find_skills"]
        assert find_skills_tool.description is not None
        assert "second-skill" not in find_skills_tool.description

        find_result = await client.call_tool("find_skills", {"query": "second"})
        names = [entry["name"] for entry in find_result.structured_content["skills"]]
        assert names == ["second-skill"]

        load_result = await client.call_tool("load_skill", {"name": "second-skill"})
        assert load_result.is_error is not True
        assert load_result.structured_content["content"].startswith("---\nname: second-skill")


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
