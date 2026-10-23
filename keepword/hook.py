"""Claude Code hook: block replies, file writes, and commits that break a rule.

Must import on any python3, because the plugin runs whatever `python3` the user has.
Keep this file free of 3.10+ syntax; the rule engine is imported only after the version check.
Anything that goes wrong here fails open: exit 1 is a non-blocking error in Claude Code,
so the user sees a notice and their work goes on.
"""

import json
import sys
from pathlib import Path


def main():
    if sys.version_info < (3, 11):  # noqa: UP036 - the plugin runs the user's python3, not ours
        print(f"keepword: needs Python 3.11+ (found {sys.version.split()[0]}), so rules are not being checked.", file=sys.stderr)
        return 1
    try:
        out = decide(json.load(sys.stdin))
    except Exception as e:  # noqa: BLE001 - fail open, never block the user because keepword broke
        print(f"keepword: skipped checks after an error: {e}", file=sys.stderr)
        return 1
    if out:
        json.dump(out, sys.stdout)
    return 0


def decide(event):
    from keepword.rules import check, find_rules, load_rules
    from keepword.transcripts import tool_text

    source, _ = find_rules(Path(event.get("cwd") or "."))
    rules = load_rules(source.read_text())
    name = event.get("hook_event_name")

    if name == "Stop":
        # This is the retry cap: a rewrite we asked for is never blocked again, so one block per reply.
        if event.get("stop_hook_active"):
            return None
        found = check(event.get("last_assistant_message") or "", rules, "reply")
        if found:
            reason = f"Your last reply broke these rules:\n{_describe(found)}\nSend it again with these fixed."
            return {"decision": "block", "reason": reason}

    elif name == "PreToolUse":
        written = tool_text(event.get("tool_name"), event.get("tool_input") or {})
        found = check(written[1], rules, written[0]) if written else []
        if found:
            reason = f"keepword blocked this {written[0]}:\n{_describe(found)}\nFix it and try again."
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
    return None


def _describe(violations):
    # !a writes non-ASCII as an escape, so the reason never shows Claude the banned char itself.
    return "\n".join(
        f"- line {v.line}, {v.rule_id} {v.match!a}" + (f": {v.message}" if v.message else "") for v in violations
    )


if __name__ == "__main__":
    sys.exit(main())
