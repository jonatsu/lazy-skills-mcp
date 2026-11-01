# Backlog

Work that is wanted but not queued. An item belongs here when nothing depends on it yet, and its reasoning is worth
keeping so that it is neither re-derived nor re-proposed. Move an entry to `ROADMAP.md` when something starts depending
on it.

## Skill Sources

- **A configuration file for skill sources.** A file such as `~/.config/lazy-skills-mcp/config.toml` would list the
  skill sources, each with name or glob filters, as an alternative to repeating command-line options in every agent's
  registration. It is the most flexible way to choose what the server serves. It also adds the largest interface:
  its schema joins the contract that pinned deployments depend on, so every later change to it is a compatibility
  decision. Several sources, grouped folders, and skipping skills that agents already load natively come first, as
  command-line options; build the file only when those options prove awkward to repeat across agents.

- **List groups instead of skill names in `find_skills`'s description.** For a large collection, an opt-in option
  would name the groups, such as `development/python`, instead of every skill. Until then the description lists
  names, capped at 300. The option also needs `find_skills` to match a skill's group path: search reads only names
  and descriptions today, so an agent that searched for a listed group would get nothing back. A skill from a flat
  source has no group and stays listed by name. Build it when a real collection outgrows the cap, so the design
  starts from that case.

- **An environment variable for skip folders.** A `LAZY_SKILLS_MCP_SKIP_INSTALLED_IN` list would mirror
  `--skip-installed-in`, as `LAZY_SKILLS_MCP_SKILLS_DIR` mirrors `--skills-dir`. 0.2.0 leaves it out because skip
  folders differ per agent, and a variable set in a shell profile reaches every agent started from that shell. Add it
  if a client cannot pass arguments, or if one machine-wide setting suits an agent family that all reads
  `~/.agents/skills`.

- **A scan object owned by discovery.** The catalog builder creates the map of visited real paths, discovery fills
  it, and the catalog reads it back to decide whether a source counts as empty. A small object in `discovery.py`
  that walks a source and answers whether a source was already reached would keep that format private. Make it the
  first step of the configuration file or group listing, since per-source filters change exactly this seam.

## Scan Cost and Logging

- **A log line for a slow scan, then a frontmatter cache.** Every tool call rescans every source and skip folder and
  parses each `SKILL.md`, so the cost grows with the collection and shows up only as agent latency. First, log one
  line with folder count, skill count, and elapsed time when a scan passes a threshold. If a real collection is slow,
  cache parsed frontmatter keyed on real path, `mtime_ns`, and size, which keeps changes visible at the next call.
  The 97-skill `jonatsu/agent-skills` checkout scans without a noticeable delay, so neither is needed yet.

- **Warnings logged once per process.** Each scan repeats the warnings for problems that persist, so a find and a
  load log each one twice. A group first reached at the depth limit through a long path also logs "not searching"
  even when a shorter path searches it later in the same walk. A process-lifetime set of emitted messages would
  silence the repeats; the false depth warning needs the walk to defer that warning until the scan ends. Do this if
  log noise becomes a complaint.
