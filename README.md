# keepword

Your AGENTS.md is a wish list.
keepword makes it a contract for Claude Code: it measures how often Claude breaks your rules, then blocks the replies, file writes, and commits that break them.

## Why

I told Claude "Never use the em dash" in my AGENTS.md.
Over a month of real sessions it still used one in 141 of 2,329 replies (6.1%), 24 of 418 files, and 2 of 102 commit messages.
A rule file is a request.
A hook is a check that runs every time.

## Install

In Claude Code:

```
/plugin marketplace add biancacchino/keepword
/plugin install keepword@keepword
```

That turns the hooks on.
There is nothing to pip install: the plugin runs on your `python3`, which needs to be 3.11 or newer.
On an older Python, keepword prints a notice and lets everything through.

## What it does

keepword checks three places:

- **Replies.** When Claude finishes a reply that breaks a rule, keepword sends it back with the rule and line number, and Claude sends a fixed reply. Each reply is sent back at most once, so it can't loop.
- **Files.** A Write or Edit that would put a banned thing in a file is denied before it runs.
- **Commits.** A `git commit` whose message breaks a rule is denied before it runs.

Text in code blocks, inline code, and quotes in replies is skipped, because quoting a banned word is not using it.
If keepword itself fails, it lets the action through and shows a notice, so a bug in keepword never blocks your work.

## Measure

Run `/keepword:measure` in Claude Code to see how often Claude broke your rules, from your saved transcripts:

```
By rule               reply                 file                  commit
no-em-dash            141/2329 (6.1%)       24/418 (5.7%)         2/102 (2.0%)
banned-words          0/2329 (0.0%)         0/418 (0.0%)          1/102 (1.0%)
no-ai-attribution     0/2329 (0.0%)         0/418 (0.0%)          0/102 (0.0%)

By week (anything broken)
  2026-09-14  115/247 (46.6%)
  2026-09-21  1/119 (0.8%)
  2026-09-28  7/398 (1.8%)
  2026-10-05  0/150 (0.0%)
  2026-10-12  33/1397 (2.4%)
  2026-10-19  12/538 (2.2%)
```

Claude Code deletes transcripts older than 30 days by default (`cleanupPeriodDays` in settings), so `measure` only sees what is left.

To run it outside Claude Code: `pip install git+https://github.com/biancacchino/keepword`, then `keepword measure`.

## Your own rules

Put a `keepword.toml` in your project root.
It replaces the bundled rules, which are in [`keepword/keepword.toml`](keepword/keepword.toml).

```toml
[[rule]]
id = "no-em-dash"
message = "Never use the em dash. Use a plain dash."
chars = ["\u2014", "\u2013"]

[[rule]]
id = "banned-words"
words = ["leverage", "robust", "seamless"]  # whole word, any case
scopes = ["reply", "commit"]                # default: reply, file, commit

[[rule]]
id = "no-ai-attribution"
pattern = '(?im)^co-authored-by:.*\bclaude\b'  # Python regex
scopes = ["commit"]
```

Each rule needs an `id` and at least one of `chars`, `words`, or `pattern`.
keepword only checks rules a program can decide.
A rule like "keep it simple" stays in your AGENTS.md.

## Develop

```
python3 -m unittest
claude --plugin-dir .   # try the plugin from this checkout
```
