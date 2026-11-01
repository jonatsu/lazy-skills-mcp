"""`--print-skills-dir`: resolve and print the directory without serving it.

The flag must answer with the same resolution `main` uses to start the server, but exit
before any filesystem check or server construction, so it works whether or not the
directory exists yet -- the deploy tooling calls it to learn where to deploy, not to
learn whether the deployment already happened.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lazy_skills_mcp.cli import main


def test_prints_the_resolved_directory_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")

    status = main(["--print-skills-dir"])

    assert status == 0
    assert capsys.readouterr().out == "/env/skills-dir\n"


def test_an_explicit_skills_dir_argument_still_wins(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")

    status = main(["--skills-dir", "/explicit/skills", "--print-skills-dir"])

    assert status == 0
    assert capsys.readouterr().out == "/explicit/skills\n"


def test_does_not_require_the_directory_to_exist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    missing = tmp_path / "never-created"
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)

    status = main(["--skills-dir", str(missing), "--print-skills-dir"])

    assert status == 0
    assert capsys.readouterr().out == f"{missing}\n"
    assert not missing.exists()


def test_does_not_start_the_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`build_server` would fail on a missing directory; reaching a clean 0 exit here
    without that error on stderr proves the server was never built."""
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)

    status = main(["--skills-dir", "/definitely/does/not/exist", "--print-skills-dir"])

    assert status == 0
    assert capsys.readouterr().err == ""


def test_several_sources_print_one_per_line_in_order(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("LAZY_SKILLS_MCP_SKILLS_DIR", raising=False)

    status = main(["--skills-dir", "/b/skills", "--skills-dir", "/a/skills", "--print-skills-dir"])

    assert status == 0
    assert capsys.readouterr().out == "/b/skills\n/a/skills\n"


def test_skip_folders_are_not_printed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LAZY_SKILLS_MCP_SKILLS_DIR", "/env/skills-dir")

    status = main(["--skip-installed-in", "/native/skills", "--print-skills-dir"])

    assert status == 0
    assert capsys.readouterr().out == "/env/skills-dir\n"


def test_a_missing_second_source_fails_startup_naming_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], skills_dir: Path
) -> None:
    missing = skills_dir.parent / "not-there"

    status = main(["--skills-dir", str(skills_dir), "--skills-dir", str(missing)])

    assert status == 1
    assert str(missing) in capsys.readouterr().err
