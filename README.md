# lazy-skills-server

An MCP server that serves the "lazy" tier of skills as tools instead of native, always-loaded skills. It
implements the design in
[`docs/plans/agent-management/lazy-skill-loading.md`](../../../docs/plans/agent-management/lazy-skill-loading.md#interfaces).

```bash
lazy-skills-server                          # serve the default lazy skills directory over stdio
lazy-skills-server --skills-dir /some/dir   # serve a different directory instead
```

## What it serves

The server scans one directory, one level deep: `<skills-dir>/<skill>/SKILL.md`, exactly how Kasetto deploys a
lazy skill (flat, no domain nesting). It parses each `SKILL.md`'s YAML frontmatter for `name` and
`description`, and skips — logging the reason to stderr — any skill whose frontmatter is missing or unparsable,
or whose `name` does not match its directory name. It also excludes any file whose resolved path leaves the
skill's own directory, so a symlink cannot serve something outside it.

The catalog is rescanned on every tool call, not cached, so a Kasetto sync during a session is visible at the
next call with no restart. Only the skill names embedded in `find_skills`'s tool description are fixed for the
process's lifetime, built once at startup, because Codex does not act on `list_changed` notifications.

Two tools, both read-only and world-closed (`ToolAnnotations(read_only_hint=True, open_world_hint=False)`):

- `find_skills(query)` — an optional whitespace-separated term list; a skill matches when every term appears,
  case-insensitively, in its name or its description. An empty or missing query returns every skill.
- `load_skill(name)` — the skill's full `SKILL.md` text, its absolute directory, and the relative paths of its
  other files. An unknown name raises a tool error naming the closest catalog names.

## Directory resolution

One function decides the skills directory, in this order: an explicit `--skills-dir` argument, then the
`LAZY_SKILLS_SERVER_SKILLS_DIR` environment variable (when non-empty), then
`$XDG_DATA_HOME/lazy-skills-server/skills` (when `XDG_DATA_HOME` is non-empty), then
`~/.local/share/lazy-skills-server/skills`. It never derives the path from this package's own location. When
the resolved directory is missing, unreadable, or holds no valid skill, the server exits non-zero with a
message naming the path it tried, so the harness reports a failed MCP server rather than an empty catalog.

## Logging

Every diagnostic goes to stderr. Nothing but the MCP protocol reaches stdout, since stdio is the transport.
