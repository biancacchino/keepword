import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

EM_DASH = "\u2014"
REPO = Path(__file__).resolve().parent.parent


def manifest(path):
    return json.loads((REPO / path).read_text())


def hook_commands():
    hooks = manifest("hooks/hooks.json")["hooks"]
    return {event: entry["hooks"][0]["command"] for event, (entry,) in hooks.items()}


def sh(command, cwd, stdin=""):
    """Run a command the way Claude Code does: in the user's project, with CLAUDE_PLUGIN_ROOT set."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO)}
    env.pop("PYTHONPATH", None)
    return subprocess.run(["sh", "-c", command], input=stdin, capture_output=True, text=True, cwd=cwd, env=env, check=False)


class Hooks(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp()  # not the repo, so keepword is only importable via the plugin root

    def test_every_hook_command_runs_from_another_project(self):
        # The hook dispatches on hook_event_name, so a Stop event proves each command reaches it.
        event = {"hook_event_name": "Stop", "cwd": self.project, "last_assistant_message": f"a {EM_DASH} b"}
        for name, command in hook_commands().items():
            p = sh(command, self.project, json.dumps(event))
            self.assertEqual(p.returncode, 0, f"{name}: {p.stderr}")
            self.assertEqual(json.loads(p.stdout)["decision"], "block", name)

    def test_a_keepword_package_in_the_project_is_not_imported(self):
        planted = Path(self.project) / "keepword"
        planted.mkdir()
        (planted / "__init__.py").write_text("raise SystemExit('planted code ran')")
        event = {"hook_event_name": "Stop", "cwd": self.project, "last_assistant_message": "fine"}
        p = sh(hook_commands()["Stop"], self.project, json.dumps(event))
        self.assertEqual((p.returncode, p.stderr), (0, ""))


class Command(unittest.TestCase):
    def test_bin_keepword_measures_from_another_project(self):
        project = tempfile.mkdtemp()
        p = sh(f'"{REPO}/bin/keepword" measure --transcripts .', project)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("no-em-dash", p.stdout)


class Manifests(unittest.TestCase):
    def test_names_and_versions_agree(self):
        plugin = manifest(".claude-plugin/plugin.json")
        (listed,) = manifest(".claude-plugin/marketplace.json")["plugins"]
        project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
        self.assertEqual(plugin["name"], listed["name"])
        self.assertEqual(plugin["name"], project["name"])
        self.assertEqual(plugin["version"], project["version"])
