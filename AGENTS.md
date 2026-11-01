# Agent Instructions

An MCP server that serves Agent Skills on demand through two tools, `find_skills` and `load_skill`.
[CONTRIBUTING.md](CONTRIBUTING.md) holds the setup, the module map, and the conventions; this file lists what must
not be missed.

## Before You Commit

- Run `just check` and `just test`; both must pass, and CI runs the same. Run `just test-all-pythons` after changing
  filesystem handling, since `Path` error behavior differs between Python 3.12, 3.13 and 3.14.
- Stage a new file before running `just check`: pre-commit sees tracked files only, so it skips an untracked file.
- `just check` may rewrite files (ruff fixes and formatting). Review the result before committing.

## Rules

- Never write to stdout from the server; it carries the MCP protocol. Log through `logging`, which goes to stderr.
- Treat everything in the README's "Interface Contract" as public. Changing it is a breaking change: say so in the
  commit message and in `CHANGELOG.md`.
- When a tool's behavior changes, update its description in `server.py` in the same commit. Agents see only those
  descriptions and the server instructions.
- A single bad skill, folder, or symlink must be logged and skipped, never abort the scan. Only an unusable source,
  or nothing left to serve, fails the server.
- Build test skill trees under `tmp_path` with `write_skill` from `tests/skill_tree.py`. Never read a real skills
  folder from a test.

## Documents

- Record user-visible changes under `## Unreleased` in `CHANGELOG.md`.
- Queue decided work in `ROADMAP.md`; keep undecided ideas, with their reasoning, in `BACKLOG.md`.
- `docs/plans/` and `docs/reviews/` are dated records of past decisions. Read them for rationale; do not rewrite
  them to describe the current code.
- Cut releases by [docs/releasing.md](docs/releasing.md).
