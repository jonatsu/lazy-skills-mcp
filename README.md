# lazy-skills-mcp

An MCP server that lets a coding agent search your Agent Skills and load one only when a request needs it, instead
of loading every skill's description into every session.

An agent that loads skills natively pays for each skill's description in every session, even for specialized
skills such as embedded Linux or Nix that few sessions use. Behind this server, those skills cost two tool
definitions, `find_skills` and `load_skill`, and the agent reads a skill's full text only when it asks for it. It
was built for Codex and GitHub Copilot CLI. An agent that already defers skill loading itself, such as Claude
Code, gains nothing from it.

The server only reads. It serves the skills it finds in the folders you name, over stdio, and never writes,
installs, or syncs skills; put them there with whatever tool you already use. Point it at a whole skills checkout,
grouped into subfolders or flat, and tell it which folders your agent already loads natively: it serves only the
rest.

## What the Agent Sees

Given `/srv/skills` holding the skills `nix-flakes` and `python-testing`, a `find_skills` call with the query
`flake lockfile` returns:

```json
{
  "skills": [
    {
      "name": "nix-flakes",
      "description": "Write and debug Nix flakes, inputs, and lockfiles."
    }
  ]
}
```

The agent then calls `load_skill` with `nix-flakes` and gets the skill's text, its directory, and its other
files, which it reads with its own tools:

```json
{
  "content": "---\nname: nix-flakes\ndescription: Write and debug Nix flakes, inputs, and lockfiles.\n---\n\n# Nix flakes\n",
  "directory": "/srv/skills/nix-flakes",
  "files": [
    "references/inputs.md"
  ]
}
```

## Install

The server needs Python 3.12 or newer. uv downloads a suitable Python when none is installed; pipx needs one installed.

**Install from the repository with uv**, which puts `lazy-skills-mcp` on `PATH`:

```bash
uv tool install git+https://github.com/jonatsu/lazy-skills-mcp
```

**Pin a commit** when you want an install that only changes when you change it:

```bash
uv tool install --reinstall git+https://github.com/jonatsu/lazy-skills-mcp@<commit>
```

**Install with pipx** instead:

```bash
pipx install git+https://github.com/jonatsu/lazy-skills-mcp
```

**Run it without installing**, with uvx, by registering this as the agent's server command:

```bash
uvx --from git+https://github.com/jonatsu/lazy-skills-mcp lazy-skills-mcp
```

**Install from a checkout** with `uv tool install .` in the repository root. The tool gets its own copy, so a
later edit or branch switch in the checkout does not change a running server.

Check the install by printing the folders the server will read:

```bash
lazy-skills-mcp --print-skills-dir
```

## Register It With an Agent

Put your skills in the default folder, `~/.local/share/lazy-skills-mcp/skills`, and register the bare command, or
point the server at the folders that already hold your skills with `--skills-dir`. Add `--skip-installed-in` for each
folder the agent loads skills from natively, so those skills are not served twice.

For Codex, which loads `~/.agents/skills` natively, in `~/.codex/config.toml`:

```toml
[mcp_servers.lazy-skills-mcp]
command = "lazy-skills-mcp"
args = ["--skills-dir", "~/src/agent-skills", "--skip-installed-in", "~/.agents/skills"]
```

For Copilot CLI, which loads `~/.copilot/skills` and `~/.agents/skills` natively, in `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "lazy-skills-mcp": {
      "type": "local",
      "command": "lazy-skills-mcp",
      "args": [
        "--skills-dir", "~/src/agent-skills",
        "--skip-installed-in", "~/.copilot/skills",
        "--skip-installed-in", "~/.agents/skills"
      ],
      "tools": ["*"]
    }
  }
}
```

The server expands the leading `~` itself, because agents start MCP servers without a shell. Each agent gets its own
skip folders, which is why they are arguments rather than an environment variable. Claude Code does not need the
server at all, since it already defers skill loading. If your setup installs Codex skills into `~/.codex/skills`, add
that folder as a skip folder too.

Register the server directly rather than behind an MCP proxy. Behind a proxy, the agent must first think of
searching the proxy for skills, and agents do not reliably take that step. Direct registration costs a few
hundred tokens per session and keeps the catalog in plain view.

An agent also needs a reason to search. Add a line to its instructions that names the kinds of skill behind the
server and tells it to call `find_skills` when a request touches one of them.

## Usage

```text
usage: lazy-skills-mcp [-h] [--skills-dir DIR] [--skip-installed-in DIR]
                       [--print-skills-dir]

Serve Agent Skills on demand as MCP tools (find_skills, load_skill) over
stdio.

options:
  -h, --help            show this help message and exit
  --skills-dir DIR      A folder to read skills from, flat or grouped. Repeat
                        it to read several, in priority order. Default: the
                        LAZY_SKILLS_MCP_SKILLS_DIR list, then
                        $XDG_DATA_HOME/lazy-skills-mcp/skills, else
                        ~/.local/share/lazy-skills-mcp/skills
  --skip-installed-in DIR
                        A folder the agent loads skills from natively; skills
                        installed there are not served. Repeatable. Default:
                        none.
  --print-skills-dir    Print the resolved skill sources, one per line, and
                        exit, without checking that they exist and without
                        starting the server.
```

## Tools

Both tools are read-only, take no filesystem path, and resolve names only against the scanned catalog.

- `find_skills(query)` returns the name and description of the skills whose name or description contains any
  of the whitespace-separated query terms, ignoring case and hyphens, best first and at most ten. Each term is
  weighted by how rare it is across the catalog (BM25's inverse document frequency), so a word in nearly every
  description barely counts, and a term in the skill's name counts double. An empty or missing query returns
  every skill. The tool's description names up to 300 skills, then counts the rest.
- `load_skill(name)` returns the skill's full `SKILL.md` text, its absolute directory, and the relative paths of
  its other files. The agent then reads `references/` and runs `scripts/` from that directory with its own
  tools. An unknown name is a tool error that lists up to three close names. A large skill can exceed a
  client's inline tool-result limit: Copilot CLI 1.0.91 saved a 29.8 KB result to a temporary file and read it
  in ranges, which works but costs the agent extra calls.

A skill is left out of the catalog, with the reason logged, when its frontmatter is missing or unparsable or
its `name` differs from its folder name. A file whose real path leaves its skill's folder, such as an outward
symlink, is left out of the file list.

## Skill Sources

The server reads skills from one or more source folders. It takes them from the first of these that names any:

1. Every `--skills-dir` argument, in order.
2. The `LAZY_SKILLS_MCP_SKILLS_DIR` environment variable, a list separated like `PATH` (`:` on Linux and macOS).
3. `$XDG_DATA_HOME/lazy-skills-mcp/skills`, when `XDG_DATA_HOME` is set to an absolute path.
4. `~/.local/share/lazy-skills-mcp/skills`.

A level never merges with a lower one: any `--skills-dir` replaces the variable. Empty values are ignored, and a
leading `~` is expanded. Because the default needs no argument, an agent's configuration need not name a folder at
all.

Inside a source, the layout decides what is a skill, whatever tool installed it. A folder holding `SKILL.md` is a
skill, and the server does not search inside it. Any other folder is a group, and the server searches its
subfolders, up to 8 levels below the source. So a flat folder of skills and a checkout grouped as
`development/python/<skill>/SKILL.md` both work. Hidden folders such as `.git` are skipped. Symlinked skills and
groups are followed, as copies would be. A source that is itself a skill serves that one skill. Point a source at the
folder that holds your skills rather than at a whole project: every valid `SKILL.md` under it is served, test
fixtures and examples included.

When two skills share a name, the first one found wins: sources in the order given, then sorted paths within a
source. The server logs a warning naming both folders. This makes the order of `--skills-dir` a priority order, so a
personal folder listed first can override one skill from a shared checkout.

Each `--skip-installed-in` folder is read flat, one skill per subfolder. A skill whose folder name or frontmatter
`name` appears there is not served, since the agent already loads it. Matching is by name only, so a different skill
that happens to share an installed name is left out too. There is no default skip folder; a missing one
logs a warning, because it is most likely a typo.

The server rescans its sources on every tool call, so a skill added or changed during a session shows up at the next
call with no restart. Only the skill names listed in `find_skills`'s tool description are fixed at startup, because
Codex ignores `list_changed` notifications. A new skill is therefore findable at once, but named in that
description only from the next session.

The server refuses to start, with a message naming the paths, when a source is missing or unreadable, when no
source holds a valid skill, or when every skill found is installed in a skip folder:

```text
lazy-skills-mcp: skills source not found: /srv/skills
```

The agent then reports a failed MCP server rather than an empty catalog. Problems with single skills or folders,
such as an invalid `SKILL.md`, an unreadable group, or a group past the depth limit, are logged and the scan goes on.
All diagnostics go to stderr, since stdout carries the MCP protocol.

## Interface Contract

Deployments pin a commit of this repository and script against the interface below. A change to any part of it
breaks them at their next pin bump, so treat it as a breaking change and say so in the commit message.

- The console command `lazy-skills-mcp`, and its exit status 1 with a message on stderr when it cannot serve any
  skill at startup.
- Its repeatable `--skills-dir DIR` and `--skip-installed-in DIR` flags, and `--print-skills-dir`, which prints the
  resolved sources on stdout, one path per line.
- The `LAZY_SKILLS_MCP_SKILLS_DIR` environment variable, its `PATH`-style list form, and the resolution order above.
- The expansion of a leading `~` in every path the flags and the variable give.
- The default source, `$XDG_DATA_HOME/lazy-skills-mcp/skills`, else `~/.local/share/lazy-skills-mcp/skills`.
- The layout rule: a folder holding `SKILL.md` is a skill, any other folder is a group, searched at least 8 levels
  deep.
- The duplicate rule: the first skill found under a name is served, by source order and then walk order.
- The skip rule: a skill whose folder name or frontmatter `name` appears in a skip folder is not served.
- The tool names `find_skills` and `load_skill`, their arguments `query` and `name`, and their result fields:
  `skills` with each skill's `name` and `description`, and `content`, `directory` and `files`.

## When an Agent Never Calls `find_skills`

Work down this list, since each step depends on the one before it:

1. Confirm that the server starts. `lazy-skills-mcp --print-skills-dir`, run with the registration's arguments,
   must name folders that hold skills, and the agent must not list the server as failed.
2. Confirm that the agent's live configuration registers the server.
3. Confirm that the agent's instructions name the kinds of skill behind the server.
4. Check the wording. The instruction line, the server's `instructions`, and both tool descriptions in
   `src/lazy_skills_mcp/server.py` are all the agent sees. If the request's domain is missing from the
   instruction line, the agent has no reason to search.

## Development

The repository pins Python and uv with [mise](https://mise.jdx.dev); uv alone works too.

```bash
uv sync                  # create the environment from uv.lock
just test                # run the tests
just test-all-pythons    # run them on Python 3.12, 3.13 and 3.14
just check               # run every pre-commit hook: hygiene, secret scans, ruff, mypy
pre-commit install
```

`just check` covers tracked files only, so stage a new file before relying on it. A running agent session keeps its
server process, so start a new session to use changed code.

## License

[MIT](LICENSE).
