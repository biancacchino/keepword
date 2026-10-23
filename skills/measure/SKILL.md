---
description: Show how often Claude broke your keepword rules, from your Claude Code transcripts.
argument-hint: "[--rules path/to/keepword.toml]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/keepword *)
---

!`${CLAUDE_PLUGIN_ROOT}/bin/keepword measure $ARGUMENTS`

Above is the keepword report. Summarize it in a few lines: the overall rate, the rule broken most often, and any week that stands out.
Do not repeat the whole table.
