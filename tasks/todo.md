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
- [ ] `keepword measure`: parse `~/.claude/projects/*/*.jsonl`, report violations per rule, per project, per week. Transcript parser isolated in one module, since the format is undocumented.
- [ ] `keepword hook`: one entry point that Claude Code calls for Stop and PreToolUse events.
- [ ] Retry cap so a Stop-hook block cannot loop forever.
- [ ] `keepword install`: prints (does not silently write) the settings.json hook snippet.
- [ ] README: one-line problem, before/after numbers, screenshot of `measure`, install.
- [ ] CI on GitHub Actions (tests + lint), then `protect-main owner/keepword validate test`.
- [ ] Publish to PyPI (needs my approval).

## Verification

- Unit tests pass for every rule type, including look-alike characters.
- `keepword measure` on my machine reproduces the 139/1,879 baseline.
- End to end: install the hook, ask Claude to write a sentence with an em dash, confirm it gets blocked and revised.
- After one week of real use, rerun `measure` and compare to the baseline. That number goes in the README.

## Hook findings (checked against code.claude.com/docs/en/hooks, 2026-10-21)

- PreToolUse can deny Write/Edit/Bash before they run (`permissionDecision: "deny"` + reason). Files and commits get real enforcement.
- Stop hook gets `last_assistant_message` and `stop_hook_active`, and can block with a reason.
- But the reply is already on screen when Stop runs. Blocking means Claude sends a second, corrected reply.
- Open decision: for replies, block (forces a rewrite) or nudge via `additionalContext` (cheaper, fixes the next reply).
- Claude Code caps Stop-hook continuations at 8 in a row; we also skip when `stop_hook_active` is true.

## Risks

- Transcript format can change between Claude Code versions. Mitigation: one parser module, a test against a sample file.
- False positives (em dash inside code, data files, or quoted user text). Mitigation: code-fence skipping and per-rule scopes (reply / file / commit).
- A Stop-hook block costs an extra turn of tokens. Mitigation: retry cap, and fast-path when there are no violations.
