import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from keepword import hook

EM_DASH = "\u2014"
REPO = Path(__file__).resolve().parent.parent


def run(event):
    out, err = io.StringIO(), io.StringIO()
    stdin = io.StringIO(event if isinstance(event, str) else json.dumps(event))
    with mock.patch.object(sys, "stdin", stdin), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = hook.main()
    return code, json.loads(out.getvalue()) if out.getvalue() else None, err.getvalue()


def stop(message, active=False, cwd="/nonexistent"):
    return {"hook_event_name": "Stop", "cwd": cwd, "stop_hook_active": active, "last_assistant_message": message}


def tool(name, cwd="/nonexistent", **tool_input):
    return {"hook_event_name": "PreToolUse", "cwd": cwd, "tool_name": name, "tool_input": tool_input}


def denied(out):
    return out["hookSpecificOutput"]["permissionDecision"] == "deny"


class Stop(unittest.TestCase):
    def test_reply_breaking_a_rule_is_blocked_with_the_reason(self):
        code, out, _ = run(stop(f"fine\nthis {EM_DASH} not"))
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        self.assertIn("no-em-dash", out["reason"])
        self.assertIn("line 2", out["reason"])
        self.assertNotIn(EM_DASH, out["reason"])  # don't prime Claude with the banned char

    def test_clean_reply_passes_silently(self):
        self.assertEqual(run(stop("all good - nothing to see")), (0, None, ""))

    def test_rewrite_after_a_block_is_never_blocked_again(self):
        self.assertEqual(run(stop(f"still {EM_DASH}", active=True)), (0, None, ""))


class PreToolUse(unittest.TestCase):
    def test_write_with_em_dash_is_denied(self):
        _, out, _ = run(tool("Write", file_path="a.md", content=f"a {EM_DASH} b"))
        self.assertTrue(denied(out))
        self.assertIn("no-em-dash", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_edit_checks_only_the_new_text(self):
        self.assertEqual(run(tool("Edit", old_string=f"a {EM_DASH} b", new_string="a - b")), (0, None, ""))
        _, out, _ = run(tool("Edit", old_string="x", new_string=f"y {EM_DASH}"))
        self.assertTrue(denied(out))

    def test_commit_with_ai_trailer_is_denied(self):
        cmd = 'git commit -m "fix: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"'
        _, out, _ = run(tool("Bash", command=cmd))
        self.assertTrue(denied(out))

    def test_bash_that_is_not_a_commit_passes(self):
        self.assertEqual(run(tool("Bash", command=f"echo '{EM_DASH}'")), (0, None, ""))

    def test_other_tools_pass(self):
        self.assertEqual(run(tool("Read", file_path=f"{EM_DASH}.md")), (0, None, ""))


class Rules(unittest.TestCase):
    def test_keepword_toml_in_the_project_wins_over_bundled(self):
        cwd = tempfile.mkdtemp()
        (Path(cwd) / "keepword.toml").write_text('[[rule]]\nid = "no-x"\nwords = ["xyzzy"]\n')
        _, out, _ = run(stop("say xyzzy", cwd=cwd))
        self.assertIn("no-x", out["reason"])
        self.assertEqual(run(stop(f"a {EM_DASH} b", cwd=cwd)), (0, None, ""))


class FailsOpen(unittest.TestCase):
    """Exit 1 is a non-blocking error in Claude Code: the user sees a notice and their work goes on."""

    def test_old_python_skips_checks_with_a_clear_message(self):
        with mock.patch.object(sys, "version_info", (3, 9, 6)):
            code, out, err = run(stop(f"a {EM_DASH} b"))
        self.assertEqual((code, out), (1, None))
        self.assertIn("3.11", err)

    def test_bad_input_skips_checks(self):
        code, out, err = run("not json")
        self.assertEqual((code, out), (1, None))
        self.assertIn("keepword", err)

    def test_broken_rules_file_skips_checks(self):
        cwd = tempfile.mkdtemp()
        (Path(cwd) / "keepword.toml").write_text('[[rule]]\nid = "empty"\n')
        code, out, err = run(stop(f"a {EM_DASH} b", cwd=cwd))
        self.assertEqual((code, out), (1, None))
        self.assertIn("empty", err)


class EntryPoint(unittest.TestCase):
    def test_module_runs_as_a_script(self):
        p = subprocess.run(
            [sys.executable, "-m", "keepword.hook"],
            input=json.dumps(stop(f"a {EM_DASH} b")), capture_output=True, text=True, cwd=REPO, check=False,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["decision"], "block")
