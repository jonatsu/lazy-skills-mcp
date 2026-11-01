# Skill sources: brainstorm draft

**Status: draft, 2026-11-01.** This draft is deliberately incomplete. It records the direction the user chose for
where the server reads skills from. A technical design comes next. Items are marked as a user decision, a
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
  out. Its default is `~/.agents/skills`. Each agent's registration passes the folders that agent loads, so the
  server stays agent-agnostic.

## Why `~/.agents/skills` Is the Skip Default, Not the Source Default

The user first suggested `~/.agents/skills` as the default source. On 2026-11-01, six of seven agents checked
loaded that folder natively: Codex, Copilot CLI, Gemini CLI, Cursor, OpenCode and Oh-My-Pi. Claude Code did not.
Serving it would make those six agents load every skill twice and lose the on-demand saving. The folder is a
convention, not part of the Agent Skills specification. Sources:

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
server at the complete skills source, and `find_skills` returns exactly the skills that `base.yaml` does not install.

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
| A missing skip folder | Treated as empty, nothing logged | As recommended | The default `~/.agents/skills` is often absent, and a warning on every start would be noise | resolved |
| Symlinked skill and group folders | Follow them; visit each real folder once so a loop ends | As recommended | Linked installs work like copies, as Codex documents for itself; the rule that a skill lists no file outside its own folder stays | resolved |
| Search depth limit | 8 levels below each source | 8 | Only guards against runaway searches; `jonatsu/agent-skills` needs 3 | resolved |
| Skill names in `find_skills`'s description | Full list, capped at 300 names with a count of the rest | As recommended, plus an opt-in option that lists groups instead of names | Names are the cue that makes agents search; 97 skills cost about 450 tokens. Large collections can switch to groups | resolved |

## Questions for the Technical Design

- The option names. `--skip-installed-in` is provisional, and the group-listing option has no name yet.
- In group-listing mode, how a skill from a flat source, which has no group, appears in the description.
- How the published interface contract in the README grows to cover the new options, the `PATH`-style variable, and
  the multi-line `--print-skills-dir` output.
