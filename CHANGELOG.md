# Changelog

## Unreleased

## 0.2.0

### Added

- `--skills-dir` can be repeated to read several sources, in priority order, and `LAZY_SKILLS_MCP_SKILLS_DIR` accepts
  a `PATH`-style list. When two skills share a name, the first found wins and a warning names both folders.
- Skills in grouped folders are found by layout alone, whatever tool installed them: a folder holding `SKILL.md` is a
  skill, any other folder is a group searched up to 8 levels deep. Hidden folders are skipped. A source can be a
  whole skills checkout.
- `--skip-installed-in DIR`, repeatable, leaves out every skill whose folder name or frontmatter `name` appears in a
  folder the agent loads natively. It has no default.
- A leading `~` in any path is expanded, because agents start MCP servers without a shell.
- Package metadata: a description, the README as the long description, the MIT licence, and project URLs.

### Changed

- A symlinked skill folder whose real location lies outside the source is now served, as a copy would be, instead of
  skipped. A skill still lists no file outside its own folder.
- A folder without `SKILL.md` is now a group that is searched, instead of a skipped folder with a warning.
- `--print-skills-dir` prints one source per line; with a single source, its output is unchanged.
- `find_skills`'s description names at most 300 skills, then counts the rest.
- A scan reads only each skill's `SKILL.md`; `load_skill` lists the files of the skill it returns.
- Startup errors name a "skills source" instead of the "lazy skills directory".

### Fixed

- The PyYAML minimum is now 6.0.1. PyYAML 6.0 has no Python 3.12 wheels and fails to build from source, so the
  declared minimum could not install on any supported Python.
- A `SKILL.md` that is not valid UTF-8 is skipped and logged instead of failing the whole scan.
- When a source disappears during a session, the tool error names it instead of a generic failure.

## 0.1.1

### Changed

- Python 3.12 and every later version are supported; 0.1.0 required Python 3.12 exactly. The tests pass on 3.12,
  3.13 and 3.14.

## 0.1.0

The first release as a standalone repository, extracted with its history from the author's agent-setup repository.

### Added

- `find_skills` searches a skills directory by name and description and returns the best matches first.
- `load_skill` returns a skill's `SKILL.md` text, its directory, and the relative paths of its other files.
- The skills directory resolves from `--skills-dir`, then `LAZY_SKILLS_MCP_SKILLS_DIR`, then
  `$XDG_DATA_HOME/lazy-skills-mcp/skills`, then `~/.local/share/lazy-skills-mcp/skills`.
  `--print-skills-dir` prints the result.

### Changed

- The server is renamed from `lazy-skills-server` to `lazy-skills-mcp`: the command, the Python package
  `lazy_skills_mcp`, the environment variable `LAZY_SKILLS_MCP_SKILLS_DIR`, the default directory, and the MCP
  server name.
