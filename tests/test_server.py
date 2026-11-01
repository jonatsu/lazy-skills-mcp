"""The MCP tool layer, exercised end-to-end through the SDK's in-memory client."""

from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.types import TextContent

from lazy_skills_mcp.server import build_server

pytestmark = pytest.mark.anyio


async def test_find_skills_with_no_query_returns_the_whole_catalog(skills_dir: Path) -> None:
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {})

    assert result.is_error is not True
    names = sorted(entry["name"] for entry in result.structured_content["skills"])
    assert names == ["embedded-linux-bringup", "nix-flakes"]


async def test_find_skills_matches_every_term_case_insensitively(skills_dir: Path) -> None:
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "EMBEDDED board"})

    names = [entry["name"] for entry in result.structured_content["skills"]]
    assert names == ["embedded-linux-bringup"]


async def test_find_skills_with_no_matching_term_returns_nothing(skills_dir: Path) -> None:
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "nonexistent-term"})

    assert result.structured_content["skills"] == []


async def test_find_skills_with_an_empty_string_query_returns_the_whole_catalog(
    skills_dir: Path,
) -> None:
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": ""})

    names = sorted(entry["name"] for entry in result.structured_content["skills"])
    assert names == ["embedded-linux-bringup", "nix-flakes"]


async def test_find_skills_returns_each_skill_a_multi_concept_query_touches(
    skills_dir: Path,
) -> None:
    """Each term matches a different skill, and both come back.

    This is the 2026-10-04 Copilot failure: "nix flake python packaging" spans two
    skills, and the earlier all-terms rule returned neither.
    """
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "embedded flakes"})

    names = sorted(entry["name"] for entry in result.structured_content["skills"])
    assert names == ["embedded-linux-bringup", "nix-flakes"]


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

    server = build_server([root])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {"query": "yocto image"})

    names = [entry["name"] for entry in result.structured_content["skills"]]
    assert names == ["my-skill"]


async def test_find_skills_description_embeds_the_alphabetical_catalog(
    skills_dir: Path,
) -> None:
    server = build_server([skills_dir])
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

    server = build_server([root])
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

    server = build_server([root])
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

    server = build_server([Path("lazy")])
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
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "../secret"})

    assert result.is_error is True
    (text_content,) = result.content
    assert isinstance(text_content, TextContent)
    assert "unknown skill" in text_content.text


async def test_load_skill_with_an_unknown_name_names_the_closest_matches(
    skills_dir: Path,
) -> None:
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("load_skill", {"name": "nix-flake"})

    assert result.is_error is True
    (text_content,) = result.content
    assert isinstance(text_content, TextContent)
    assert "nix-flakes" in text_content.text


async def test_find_skills_and_load_skill_are_declared_read_only(skills_dir: Path) -> None:
    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()

    by_name = {tool.name: tool for tool in tools.tools}
    for name in ("find_skills", "load_skill"):
        annotations = by_name[name].annotations
        assert annotations is not None
        assert annotations.read_only_hint is True
        assert annotations.destructive_hint is False
        assert annotations.idempotent_hint is True
        assert annotations.open_world_hint is False
        assert annotations.title
        assert by_name[name].title == annotations.title
        assert "Args:" not in (by_name[name].description or "")


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

    server = build_server([root])

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
    from lazy_skills_mcp.catalog import SkillsDirectoryError

    missing = tmp_path / "does-not-exist"
    with pytest.raises(SkillsDirectoryError, match=str(missing)):
        build_server([missing])


async def test_nothing_is_written_to_stdout_while_serving_tool_calls(
    skills_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)

    server = build_server([skills_dir])
    async with Client(server, raise_exceptions=True) as client:
        await client.list_tools()
        await client.call_tool("find_skills", {})
        await client.call_tool("load_skill", {"name": "nix-flakes"})
        await client.call_tool("load_skill", {"name": "does-not-exist"})

    assert captured.getvalue() == ""


def test_server_instructions_point_agents_at_find_skills(skills_dir: Path) -> None:
    server = build_server([skills_dir])

    assert server.instructions is not None
    assert "find_skills" in server.instructions
    assert "load_skill" in server.instructions


def _write(skill_dir: Path) -> None:
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_dir.name}\ndescription: about {skill_dir.name}\n---\nbody\n",
        encoding="utf-8",
    )


async def test_find_skills_serves_the_sources_minus_the_skills_installed_natively(
    tmp_path: Path,
) -> None:
    """The draft's success signal: an empty query returns exactly the source's skills
    minus those the agent loads natively from its skip folder."""
    source = tmp_path / "agent-skills"
    for relative in ["agents/ast-grep", "development/python/python-style", "embedded/u-boot"]:
        _write(source / relative)
    native = tmp_path / "native"
    _write(native / "ast-grep")

    server = build_server([source], [native])
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("find_skills", {})

    names = sorted(entry["name"] for entry in result.structured_content["skills"])
    assert names == ["python-style", "u-boot"]


async def _find_skills_description_for(source: Path) -> str:
    server = build_server([source])
    async with Client(server, raise_exceptions=True) as client:
        tools = await client.list_tools()
    (find_skills_tool,) = [t for t in tools.tools if t.name == "find_skills"]
    assert find_skills_tool.description is not None
    return find_skills_tool.description


@pytest.mark.parametrize(("count", "listed", "more"), [(300, 300, None), (301, 300, 1)])
async def test_find_skills_description_lists_at_most_300_names(
    tmp_path: Path, count: int, listed: int, more: int | None
) -> None:
    source = tmp_path / "many"
    for index in range(count):
        _write(source / f"skill-{index:04d}")

    description = await _find_skills_description_for(source)

    assert description.count("skill-") == listed
    assert "skill-0000" in description
    if more is None:
        assert "more" not in description
    else:
        assert f"and {more} more" in description
        assert "skill-0300" not in description


@pytest.mark.parametrize("tool_name", ["find_skills", "load_skill"])
async def test_a_source_that_disappears_mid_session_is_named_in_the_tool_error(
    tmp_path: Path, tool_name: str
) -> None:
    source = tmp_path / "source"
    _write(source / "my-skill")
    server = build_server([source])
    shutil.rmtree(source)

    async with Client(server) as client:
        arguments = {"name": "my-skill"} if tool_name == "load_skill" else {}
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    (content,) = result.content
    assert isinstance(content, TextContent)
    assert str(source) in content.text
