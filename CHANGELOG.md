# Changelog

## Unreleased

### Fixed

- The PyYAML minimum is now 6.0.1. PyYAML 6.0 has no Python 3.12 wheels and fails to build from source, so the
  declared minimum could not install on any supported Python.

### Added

- Package metadata: a description, the README as the long description, the MIT licence, and project URLs.

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
