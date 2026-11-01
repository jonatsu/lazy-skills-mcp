# Backlog

Work that is wanted but not queued. An item belongs here when nothing depends on it yet, and its reasoning is worth
keeping so that it is neither re-derived nor re-proposed. Move an entry to `TODO.md` when something starts depending
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
