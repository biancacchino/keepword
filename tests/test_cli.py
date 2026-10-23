import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from keepword.__main__ import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Measure(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.dir)

    def test_uses_bundled_rules_when_cwd_has_none(self):
        code, out, _ = run("measure", "--transcripts", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("no-em-dash", out)
        self.assertIn("Rules: bundled defaults", out)

    def test_prefers_keepword_toml_in_cwd(self):
        (self.dir / "keepword.toml").write_text('[[rule]]\nid = "mine"\nwords = ["x"]\n')
        _, out, _ = run("measure", "--transcripts", str(self.dir))
        self.assertIn("mine", out)
        self.assertNotIn("no-em-dash", out)
        self.assertIn("Rules: keepword.toml", out)

    def test_missing_rules_file_is_a_clear_error(self):
        code, _, err = run("measure", "--rules", "nope.toml", "--transcripts", str(self.dir))
        self.assertEqual(code, 2)
        self.assertIn("nope.toml", err)

