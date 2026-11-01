# Contributing

This guide covers setting up a checkout, the checks every change must pass, and the conventions the code and
documents follow. [docs/releasing.md](docs/releasing.md) covers cutting a release.

## Set Up a Checkout

You need [uv](https://docs.astral.sh/uv/) and [just](https://just.systems). [mise](https://mise.jdx.dev) is optional:
`mise install` in the checkout installs the pinned uv and the three Python versions the tests run on.

```bash
git clone https://github.com/jonatsu/lazy-skills-mcp
cd lazy-skills-mcp
uv sync                          # create .venv from uv.lock, with the test, lint and dev tools
uv run pre-commit install        # run the hooks on every commit
```

`pre-commit` is installed into the project environment, not on `PATH`, so call it through `uv run`.

## Run the Checks

| Task | With just | Without just |
| --- | --- | --- |
| Run the tests | `just test` | `uv run --locked pytest` |
| Run them on Python 3.12, 3.13 and 3.14 | `just test-all-pythons` | `uv run --locked --isolated --python 3.13 pytest`, once per version |
| Run every hook: hygiene, secret scans, ruff, mypy | `just check` | `uv run --locked pre-commit run --all-files` |

CI runs the same hooks and tests, plus a run against the lowest supported dependency versions, a package build, and
a dependency audit. Both `just check` and the commit hook can change files: ruff fixes what it can and reformats.
Review and stage those changes, then run the check again. The hooks see tracked files only, so stage a new file
before trusting a clean run.

To try a change in a real agent, install the checkout with `uv tool install --reinstall .` and start a new agent
session. A running session keeps its old server process.

## Code Conventions

- Keep stdout for the MCP protocol. Diagnostics go through `logging`, which the CLI sends to stderr.
- Keep the interface contract in the README stable. A change to anything it lists is a breaking change: say so in
  the commit message and the changelog.
- When a tool's behavior changes, change its description in `server.py` in the same commit. Agents read only the
  tool descriptions and the server instructions, so write them for an agent deciding whether to call the tool.
- Build test skill trees under `tmp_path` with `write_skill` from `tests/skill_tree.py`. Never read a real skills
  folder. Write a `SKILL.md` by hand only when its exact content is what the test is about.
- Tests that change permission bits skip when run as root, since root ignores them.
- Docstrings follow the Google style. Comments say why the code does something, not what it did before.

The modules form one chain. `cli` resolves configuration with `location` and builds the server. `server` exposes
the two tools over `catalog` and `ranking`. `catalog` combines `discovery` (walking sources) and `installed`
(reading skip folders). Both use `skill` (one skill folder) and `folders` (error-tolerant folder checks).
[docs/plans/skill-sources-design.md](docs/plans/skill-sources-design.md) holds the design and its decisions.

## Commits and Documents

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org), such as
`fix: name the actual problem in skill and source rejection messages`. Keep each commit to one logical change that
passes the checks on its own.

Record a user-visible change under `## Unreleased` in `CHANGELOG.md`. Queue decided future work in `ROADMAP.md`,
and keep ideas nothing depends on yet in `BACKLOG.md`, with the reasoning that would otherwise be re-derived.
