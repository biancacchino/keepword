"""Read Claude Code transcripts and yield what Claude wrote, by scope.

The transcript format is undocumented, so every assumption about it lives here.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "projects"


@dataclass
class Item:
    scope: str  # reply, file, or commit
    text: str
    project: str
    timestamp: str


def items(root: Path = DEFAULT_ROOT) -> Iterator[Item]:
    for path in sorted(root.rglob("*.jsonl")):  # rglob: subagent runs live in subfolders
        with path.open(errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant" or entry.get("isApiErrorMessage"):
                    continue
                project = Path(entry.get("cwd") or path.parent.name).name
                for scope, text in _texts(entry.get("message", {}).get("content")):
                    yield Item(scope, text, project, entry.get("timestamp", ""))


def _texts(content) -> Iterator[tuple[str, str]]:
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            yield "reply", block.get("text", "")
        elif block.get("type") == "tool_use":
            name, inp = block.get("name"), block.get("input") or {}
            if name == "Write":
                yield "file", inp.get("content", "")
            elif name == "Edit":
                yield "file", inp.get("new_string", "")
            elif name == "Bash" and "git commit" in inp.get("command", ""):
                # ponytail: checks the whole command, so a chained `gh pr create` body counts too.
                # A heredoc that merely mentions "git commit" also counts; parse the -m/-F args if that gets noisy.
                yield "commit", inp["command"]
