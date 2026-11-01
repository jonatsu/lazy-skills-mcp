"""Build skill folders on disk for tests, in the one frontmatter format the server reads."""

from __future__ import annotations

from pathlib import Path


def write_skill(
    skill_dir: Path,
    *,
    name: str | None = None,
    description: str = "does a thing",
    body: str = "body\n",
) -> Path:
    """Create `skill_dir` holding a valid `SKILL.md`, and return the folder.

    Args:
        skill_dir: The skill folder to create, with any missing parents.
        name: The frontmatter `name`; defaults to the folder's name, which makes it valid.
        description: The frontmatter `description`.
        body: The Markdown after the frontmatter.
    """
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name or skill_dir.name}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )
    return skill_dir
