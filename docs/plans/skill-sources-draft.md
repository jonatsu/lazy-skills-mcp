# Skill sources: brainstorm draft

**Status: superseded by [skill-sources-design.md](skill-sources-design.md), which was implemented in 0.2.0.** This
draft, written on 2026-11-01, records the direction the user chose for where the server reads skills from, and is
kept for its decisions table and the alternatives rejected there. Items are marked as a user decision, a
recommendation, or a provisional idea.

## Original Idea and Purpose

Today the server reads one flat directory, by default `~/.local/share/lazy-skills-mcp/skills`. A deployment must
therefore copy the on-demand skills into that directory, and it must keep a second list of which skills those are.
In agent-setup, that means two Kasetto scopes, `lazy` and `claude-lazy`, beside the `base.yaml` list of natively
loaded skills. The user named both costs as the problem (user decision): keeping two skill lists in step, and the
extra copy into a separate folder.

The desired outcome is that a user points the server at the skills they already have, in whatever layout their
skill tool produced, and the server serves exactly the skills their agent does not load natively.

## Direction

- **Several sources** (user decision). `--skills-dir` may be given more than once, so the server reads several
  folders. An environment-variable form follows the same idea.
- **Grouped folders, detected automatically** (user decision). A folder that contains `SKILL.md` is a skill, and the
  server does not search inside it for more skills. Any other folder is a group, and the server searches inside it.
  Hidden folders such as `.git` are skipped, and a depth limit stops runaway searches. This lets the server read a
  checkout of a skills repository directly: `jonatsu/agent-skills` nests skills one and two groups deep, as
  `agents/<skill>/` and `development/python/<skill>/`.
- **Tool-agnostic** (user decision). The rules depend only on the folder layout, never on which tool installed the
  skills, whether Kasetto, `npx skills`, or a plain copy.
- **Skip what the agent already loads** (user decision). A repeatable option, provisionally
  `--skip-installed-in DIR`, names folders whose skills the agent loads natively; the server leaves those skills
  out. It has no default: skipping happens only when a registration asks for it, so upgrading changes nothing for
  an existing registration. Each agent's registration passes the folders that agent loads, so the server stays
  agent-agnostic. The README recommends `~/.agents/skills` as the usual value.

## Why `~/.agents/skills` Is Not the Source Default

The user first suggested `~/.agents/skills` as the default source. On 2026-11-01, the documentation of six of
seven agents checked said they load that folder natively: Codex, Copilot CLI, Gemini CLI, Cursor, OpenCode and
Oh-My-Pi. Claude Code's did not. Serving it would make those six agents load every skill twice and lose the
on-demand saving. The folder is a convention, not part of the Agent Skills specification. Sources:

- [Copilot CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
- [Codex skills](https://developers.openai.com/codex/skills)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Gemini CLI skills](https://geminicli.com/docs/cli/skills/)
- [Cursor skills](https://cursor.com/docs/context/skills)
- [OpenCode skills](https://opencode.ai/docs/skills/)
- [Oh-My-Pi discovery source](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/discovery/agents.ts)
- [Agent Skills client guide](https://agentskills.io/client-implementation/adding-skills-support)

## Alternatives Considered

- **Built-in agent profiles**, such as `--agent codex`, were rejected. The server would have to track every agent's
  native folders, and those conventions keep changing.
- **Detecting the agent from its MCP client name** was rejected. Client names are not standardized, and a wrong
  guess silently hides skills.
- **A configuration file** listing sources with filters was deferred to [BACKLOG.md](../../BACKLOG.md).

## Scope

In scope: how the server finds, groups, and filters skills; the command-line and environment interface for it; and
how `find_skills`'s tool description names the skills it serves. Out of scope: the tool names `find_skills` and
`load_skill` and the shape of their results, and how any skill tool installs skills.

## Success Signal

Agent-setup deletes its `lazy` and `claude-lazy` Kasetto scopes and keeps one list, `base.yaml`. Its agents point the
server at the complete skills source, each passing the folder its agent loads natively as a skip folder, and
`find_skills` returns exactly the skills that `base.yaml` does not install for that agent.

Inside this repository, a test proves the same thing: given a fixture source tree and a fixture skip folder,
`find_skills` with an empty query returns exactly the source's skills minus those in the skip folder.

## Decisions

Settled with the user in an interview on 2026-11-01.

| Decision | Recommended | Chosen | Why | Status |
| --- | --- | --- | --- | --- |
| Source when no `--skills-dir` is given | Keep today's default directory | Keep today's default | Existing bare-command registrations keep working, and a new user can start with no configuration | resolved |
| `--print-skills-dir` with several sources | One path per line, in source order | As recommended | With one source or none the output is unchanged, so agent-setup's destination check keeps working | resolved |
| `LAZY_SKILLS_MCP_SKILLS_DIR` with several folders | `PATH`-style list, split on `os.pathsep` | As recommended | The variable offers what the repeatable flag offers; a single path means what it did before | resolved |
| Release number | 0.2.0 | 0.2.0 | Nothing in today's contract breaks, so the new options are a minor release before 1.0 | resolved |
| Same skill name in two sources | First source wins, warning logs both paths | As recommended | Source order becomes a priority order, like `PATH`; one duplicate does not take the server down | resolved |
| When a skill counts as installed in a skip folder | Folder name or frontmatter `name` matches | As recommended | When in doubt the skill stays out, because the agent already loads it natively | resolved |
| How a skip folder is read | Flat, one skill per child folder | As recommended | Agents document only the flat layout; reading flat makes the worst mistake a duplicate, never a lost skill | resolved |
| A missing skip folder | Treated as empty, with a warning naming the path | As recommended | Every skip folder is now explicit, so a missing one is likely a typo that would otherwise load every skill twice unnoticed | resolved |
| Skip folders when none is given | Default `~/.agents/skills`, an explicit value replaces it | No default; skipping happens only when asked | Upgrading changes nothing for existing registrations; agent-setup passes its own per-agent folders anyway | resolved |
| Symlinked skill and group folders | Follow them; visit each real folder once so a loop ends | As recommended | Linked installs work like copies, as Codex documents for itself; the rule that a skill lists no file outside its own folder stays | resolved |
| Search depth limit | 8 levels below each source | 8 | Only guards against runaway searches; `jonatsu/agent-skills` needs 3 | resolved |
| Skill names in `find_skills`'s description | Full list, capped at 300 names with a count of the rest | As recommended | Names are the cue that makes agents search; 97 skills cost about 450 tokens and the cap bounds the cost near 1,400 | resolved |
| An option that lists groups instead of names | Defer to BACKLOG.md | Deferred | Search matches only names and descriptions, so the option also needs searchable group paths; it waits for a real large collection. Cost of deferring: a collection beyond 300 skills shows only a capped name list | deferred |

## Design Constraints From the Review

A plan critic reviewed this draft on 2026-11-01. These constraints follow from the decisions above:

- Following symlinked skill and group folders means removing today's check that drops a skill folder whose real
  location lies outside the source (`_is_confined` in `catalog.py`). The rule that a skill lists no file outside its
  own folder stays. The design decides which path `load_skill` reports as the skill's directory.
- The walk order is fixed: sources in order, then sorted paths, depth first. The first skill found under a name wins,
  within a source as across sources, and a warning names both paths.
- A folder whose `SKILL.md` is invalid is a skipped skill, not a group: the server logs why and does not search
  inside it. Group folders produce no warning.
- Reaching the depth limit logs a warning; the design states whether a skill exactly at depth 8 is found.
- When every skill is skipped, the server exits non-zero with a message that says so. A missing source keeps
  today's fail-closed behaviour.
- The README's interface contract grows explicitly: nested groups extend the `<skill>/SKILL.md` layout.

## Questions for the Technical Design

- The option names. `--skip-installed-in` is provisional.
- How the catalog stays fast when it rescans a deep source tree on every tool call.
- Whether folders such as `node_modules` or test fixtures inside a skills checkout need excluding beyond hidden
  folders.
- Whether `--skills-dir` replaces `LAZY_SKILLS_MCP_SKILLS_DIR` entirely or adds to it, and how empty list entries are
  treated.
- How the published interface contract in the README grows to cover the new options, the `PATH`-style variable, and
  the multi-line `--print-skills-dir` output.
