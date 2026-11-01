# lazy-skills-mcp

An MCP server that lets a coding agent search a directory of Agent Skills and load one
only when a request needs it, instead of loading every skill's description into every session.

An agent that loads skills natively pays for each skill's description in every session, even for specialized
skills such as embedded Linux or Nix that few sessions use. Behind this server, those skills cost two tool
definitions, `find_skills` and `load_skill`, and the agent reads a skill's full text only when it asks for it. It
was built for Codex and GitHub Copilot CLI. An agent that already defers skill loading itself, such as Claude
Code, gains nothing from it.

The server only reads. It serves one directory over stdio, takes no filesystem path from the agent, and never
writes, installs, or syncs skills; put them in the directory with whatever tool you already use.

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

The server needs Python 3.12. uv downloads it when it is missing; pipx needs it installed.

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
pipx install --python python3.12 git+https://github.com/jonatsu/lazy-skills-mcp
```

**Run it without installing**, with uvx, by registering this as the agent's server command:

```bash
uvx --from git+https://github.com/jonatsu/lazy-skills-mcp lazy-skills-mcp
```

**Install from a checkout** with `uv tool install .` in the repository root. The tool gets its own copy, so a
later edit or branch switch in the checkout does not change a running server.

Check the install by printing the directory the server will scan:

```bash
lazy-skills-mcp --print-skills-dir
```

## Register It With an Agent

Put your skills in that directory, one directory per skill, then register the command with each agent.

For Codex, in `~/.codex/config.toml`:

```toml
[mcp_servers.lazy-skills-mcp]
command = "lazy-skills-mcp"
```

For Copilot CLI, in `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "lazy-skills-mcp": {
      "type": "local",
      "command": "lazy-skills-mcp",
      "tools": ["*"]
    }
  }
}
```

Register the server directly rather than behind an MCP proxy. Behind a proxy, the agent must first think of
searching the proxy for skills, and agents do not reliably take that step. Direct registration costs a few
hundred tokens per session and keeps the catalog in plain view.

An agent also needs a reason to search. Add a line to its instructions that names the kinds of skill behind the
server and tells it to call `find_skills` when a request touches one of them.

## Usage

```text
usage: lazy-skills-mcp [-h] [--skills-dir DIR] [--print-skills-dir]

Serve the lazy skill tier as MCP tools (find_skills, load_skill) over stdio.

options:
  -h, --help          show this help message and exit
  --skills-dir DIR    Lazy skills directory. Precedence: this flag, then the
                      LAZY_SKILLS_MCP_SKILLS_DIR environment variable, then
                      $XDG_DATA_HOME/lazy-skills-mcp/skills, else
                      ~/.local/share/lazy-skills-mcp/skills
  --print-skills-dir  Print the resolved skills directory and exit, without
                      checking that it exists and without starting the server.
```

## Tools

Both tools are read-only, take no filesystem path, and resolve names only against the scanned catalog.

- `find_skills(query)` returns the name and description of the skills whose name or description contains any
  of the whitespace-separated query terms, ignoring case and hyphens, best first and at most ten. Each term is
  weighted by how rare it is across the catalog (BM25's inverse document frequency), so a word in nearly every
  description barely counts, and a term in the skill's name counts double. An empty or missing query returns
  every skill.
- `load_skill(name)` returns the skill's full `SKILL.md` text, its absolute directory, and the relative paths of
  its other files. The agent then reads `references/` and runs `scripts/` from that directory with its own
  tools. An unknown name is a tool error that lists up to three close names. A large skill can exceed a
  client's inline tool-result limit: Copilot CLI 1.0.91 saved a 29.8 KB result to a temporary file and read it
  in ranges, which works but costs the agent extra calls.

A skill is left out of the catalog, with the reason logged, when its frontmatter is missing or unparsable or
its `name` differs from its directory name. A file whose resolved path leaves its skill's directory, such as an
outward symlink, is left out of the file list. So is a skill directory that resolves outside the skills
directory.

## The Skills Directory

The server resolves its directory in this order: the `--skills-dir` argument, then the
`LAZY_SKILLS_MCP_SKILLS_DIR` environment variable, then `$XDG_DATA_HOME/lazy-skills-mcp/skills`, then
`~/.local/share/lazy-skills-mcp/skills`. Empty variables are skipped. Because the default needs no argument, an
agent's configuration need not carry a machine-specific path.

The server scans the directory one level deep, as `<skills-dir>/<skill>/SKILL.md`. It rescans on every tool
call, so a skill added or changed during a session shows up at the next call with no restart. Only the skill
names listed in `find_skills`'s tool description are fixed at startup, because Codex ignores `list_changed`
notifications. A new skill is therefore findable at once, but named in that description only from the next
session.

When the resolved directory is missing, unreadable, or holds no valid skill, the server exits non-zero with a
message naming the path it tried:

```text
lazy-skills-mcp: lazy skills directory not found: /srv/skills
```

The agent then reports a failed MCP server rather than an empty catalog. All diagnostics go to stderr, since
stdout carries the MCP protocol.

## Interface Contract

Deployments pin a commit of this repository and script against the interface below. A change to any part of it
breaks them at their next pin bump, so treat it as a breaking change and say so in the commit message.

- The console command `lazy-skills-mcp`.
- Its `--skills-dir DIR` and `--print-skills-dir` flags, and the bare directory path that the second prints on
  stdout.
- The `LAZY_SKILLS_MCP_SKILLS_DIR` environment variable and the resolution order above.
- The default directory, `$XDG_DATA_HOME/lazy-skills-mcp/skills`, else `~/.local/share/lazy-skills-mcp/skills`.
- The `<skills-dir>/<skill>/SKILL.md` layout.
- The tool names `find_skills` and `load_skill`.

## When an Agent Never Calls `find_skills`

Work down this list, since each step depends on the one before it:

1. Confirm that the server starts. `lazy-skills-mcp --print-skills-dir` must name a directory that holds
   skills, and the agent must not list the server as failed.
2. Confirm that the agent's live configuration registers the server.
3. Confirm that the agent's instructions name the kinds of skill behind the server.
4. Check the wording. The instruction line, the server's `instructions`, and both tool descriptions in
   `src/lazy_skills_mcp/server.py` are all the agent sees. If the request's domain is missing from the
   instruction line, the agent has no reason to search.

## Development

The repository pins Python and uv with [mise](https://mise.jdx.dev); uv alone works too.

```bash
uv sync           # create the environment from uv.lock
just test         # run the tests
just check        # run every pre-commit hook: hygiene, secret scans, ruff, mypy
pre-commit install
```

A running agent session keeps its server process, so start a new session to use changed code.

## License

[MIT](LICENSE).
