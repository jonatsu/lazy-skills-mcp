# Roadmap

Work that is decided and queued for a coming release. Ideas that nothing depends on yet stay in
[BACKLOG.md](BACKLOG.md) until they are decided.

## Next Breaking Release

- **Check skill names against the Agent Skills naming rule.** The
  [Agent Skills specification](https://agentskills.io/specification#name-field) requires a `name` of 1 to 64
  characters, using only lowercase `a-z`, `0-9` and hyphens, with no leading, trailing, or doubled hyphen, and equal
  to the skill's folder name. 0.2.0 checks only the folder-name match, so any folder name reaches `find_skills`'s
  always-loaded description. The server should reject a skill whose name breaks the rule, logging the reason as it
  does for other invalid skills, and the skip folders should keep matching names as they are. This drops skills
  that 0.2.0 serves, so it ships in a release marked as breaking, with a changelog entry naming the rule. Design
  section 11 records the risk this closes.
