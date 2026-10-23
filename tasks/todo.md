# keepword - plan

## Pitch

Your AGENTS.md is a wish list.
keepword turns it into a contract: it measures how often your coding agent breaks your rules, then enforces them at the tool boundary.

## What makes it different

- keepword targets *agent rule files* (AGENTS.md / CLAUDE.md) and Claude Code specifically.
- It audits your real history: compliance per rule, per project, over time.
- It enforces at three boundaries: Claude's replies, the files it writes, and its commit messages.
- The demo uses my real data: 139 of 1,879 replies (7.4%) broke the no-em-dash rule.

## Scope (v1)

- Deterministic rules only: banned characters, banned words, regex, required/forbidden commit trailers.
- Rules live in `keepword.toml` (stdlib `tomllib`, zero dependencies).
- Out of scope: using an LLM to judge prose rules like "keep it simple". The thesis is that rules decide what rules can decide.

## Tasks

- [x] Verify Claude Code hook behavior against current docs: Stop hook can block and make Claude revise; PreToolUse can deny Write/Edit/Bash with a reason.
- [x] Rule engine: load `keepword.toml`, check text, return violations with rule id and position. Skip code fences and quoted text.
- [x] Failing tests first for the engine: em dash, U+2011 and other dash look-alikes, banned words (whole word, case-insensitive), commit trailer.
- [x] `keepword measure`: parse `~/.claude/projects/*/*.jsonl`, report violations per rule, per project, per week. Transcript parser isolated in one module, since the format is undocumented.
- [x] Packaging: `pyproject.toml` with a `keepword` console script. Bundled rules are the fallback when there is no `./keepword.toml`.
- [x] `python3 -m keepword.hook`: one entry point that Claude Code calls for Stop and PreToolUse events.
- [x] Retry cap so a Stop-hook block cannot loop forever.
- [x] Python version guard: the hook needs 3.11+ for `tomllib`, but macOS system `python3` is often 3.9. On an old Python, print a clear stderr message and fail open (never block the user's work).
- [x] Claude Code plugin: `.claude-plugin/plugin.json`, `hooks/hooks.json` calling `python3 ${CLAUDE_PLUGIN_ROOT}/...` (stdlib only, no pip), and a `/keepword:measure` skill (plugin commands are namespaced). Installing the plugin turns the hooks on, so there is no `keepword install` step.
- [x] Marketplace: `.claude-plugin/marketplace.json` in this repo, so users run `/plugin marketplace add biancacchino/keepword` then `/plugin install keepword@keepword`.
- [x] README: one-line problem, before/after numbers, screenshot of `measure`, install via the plugin marketplace.
- [x] CI on GitHub Actions (tests + lint), then `protect-main owner/keepword validate test`.
- [ ] Optional: publish to PyPI so `uvx keepword measure` works without installing the plugin (needs my approval).

## Why a plugin, not a skill

- A skill is instructions Claude chooses to follow, which is the wish-list problem keepword exists to fix.
- Enforcement lives in hooks, and a plugin is how Claude Code ships hooks.
- PyPI is a second channel for `measure`, not a requirement.

## Verification

- Unit tests pass for every rule type, including look-alike characters.
- `keepword measure` on my machine reproduces the 139/1,879 baseline.
- End to end (done 2026-10-23 with `claude -p --plugin-dir`, Write denied and reply resent clean; redo via the marketplace after merge): ask Claude to write a sentence with an em dash, confirm it gets blocked and revised.
- After one week of real use, rerun `measure` and compare to the baseline. That number goes in the README.

## Hook findings (checked against code.claude.com/docs/en/hooks, 2026-10-21)

- PreToolUse can deny Write/Edit/Bash before they run (`permissionDecision: "deny"` + reason). Files and commits get real enforcement.
- Stop hook gets `last_assistant_message` and `stop_hook_active`, and can block with a reason.
- But the reply is already on screen when Stop runs. Blocking means Claude sends a second, corrected reply.
- Decided: block, not nudge via `additionalContext`. Enforcement is the point; the retry cap bounds the cost.
- Exit 1 is a non-blocking error: the action goes ahead and the user sees a hook-error notice. The hook fails open this way.
- Claude Code caps Stop-hook continuations at 8 in a row. keepword's own cap is tighter: it skips when `stop_hook_active` is true, so each reply is blocked at most once.

## Baseline (2026-10-21, all transcripts incl. subagents)

- Replies: 143/1,988 (7.2%) had an em dash. Files: 20/395 (5.1%). Commits: 1/83 (1.2%).
- Week of 2026-09-14: 46.6% of items broke a rule. Every week since: 0-6%.
- Checked 2026-10-23: 108 real em dashes in dental-app replies, 2026-09-18 to 09-20. Not parser noise. Likely before the rule was in AGENTS.md; confirm the date it was added.
- Claude Code deletes transcripts after 30 days (`cleanupPeriodDays`), so old weeks drop out of `measure` over time. Rerun 2026-10-23: replies 141/2,329 (6.1%).
- Known noise: code files that mention a dash in a string count as file hits.

## Risks

- Transcript format can change between Claude Code versions. Mitigation: one parser module, a test against a sample file.
- False positives (em dash inside code, data files, or quoted user text). Mitigation: code-fence skipping and per-rule scopes (reply / file / commit).
- A Stop-hook block costs an extra turn of tokens. Mitigation: retry cap, and fast-path when there are no violations.
- Plugin hooks run on every Write/Edit/Bash for every user. A crash or slow start hurts everyone. Mitigation: fail open on any internal error, keep the no-violation path fast.
- Wrong Python on the user's machine. Mitigation: the version guard above.
