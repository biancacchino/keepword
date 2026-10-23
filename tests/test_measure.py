import json
import tempfile
import unittest
from pathlib import Path

from keepword.measure import format_report, measure
from keepword.rules import Rule
from keepword.transcripts import items

EM = "\u2014"
RULES = [
    Rule(id="no-em-dash", chars=[EM]),
    Rule(id="no-ai-attribution", pattern="Generated with Claude Code", scopes=["commit"]),
]


def assistant(*content, ts="2026-10-01T12:00:00Z", cwd="/home/me/proj1", **extra):
    return {"type": "assistant", "timestamp": ts, "cwd": cwd, "message": {"content": list(content)}, **extra}


def tool(name, **inp):
    return {"type": "tool_use", "name": name, "input": inp}


LINES = [
    assistant({"type": "text", "text": f"a {EM} b"}),
    assistant({"type": "text", "text": "clean"}, ts="2026-10-08T12:00:00Z", cwd="/home/me/proj2"),
    assistant({"type": "thinking", "thinking": f"thinking {EM} is private"}),
    assistant(tool("Write", file_path="/x.md", content=f"doc {EM}")),
    assistant(tool("Edit", file_path="/x.md", old_string=EM, new_string="fixed")),
    assistant(tool("Bash", command="git commit -m 'feat: x\n\nGenerated with Claude Code'")),
    assistant(tool("Bash", command=f"echo '{EM}'")),
    assistant({"type": "text", "text": f"API error {EM}"}, isApiErrorMessage=True),
    {"type": "user", "message": {"content": f"user said {EM}"}},
]


class Transcripts(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        sub = self.root / "proj" / "session" / "subagents"
        sub.mkdir(parents=True)
        (self.root / "proj" / "a.jsonl").write_text("\n".join(map(json.dumps, LINES)) + "\nnot json\n")
        (sub / "agent.jsonl").write_text(json.dumps(assistant({"type": "text", "text": "sub"})))

    def test_keeps_only_what_claude_wrote_including_subagents(self):
        got = [(i.scope, i.text) for i in items(self.root)]
        self.assertCountEqual(got, [
            ("reply", f"a {EM} b"),
            ("reply", "clean"),
            ("reply", "sub"),
            ("file", f"doc {EM}"),
            ("file", "fixed"),
            ("commit", "git commit -m 'feat: x\n\nGenerated with Claude Code'"),
        ])

    def test_report_counts_per_rule_scope_week_and_project(self):
        report = measure(items(self.root), RULES)
        self.assertEqual(report.totals, {"reply": 3, "file": 2, "commit": 1})
        self.assertEqual(report.hits, {("no-em-dash", "reply"): 1, ("no-em-dash", "file"): 1,
                                       ("no-ai-attribution", "commit"): 1})
        self.assertEqual(report.week_hits, {"2026-09-28": 3})
        self.assertEqual(report.week_totals, {"2026-09-28": 5, "2026-10-05": 1})
        self.assertEqual(report.project_hits, {"proj1": 3})

    def test_format_shows_rate(self):
        out = format_report(measure(items(self.root), RULES))
        self.assertIn("1/3", out)
        self.assertIn("33.3%", out)
        self.assertIn("Most violations, by project", out)
        self.assertFalse([line for line in out.splitlines() if line != line.rstrip()])

