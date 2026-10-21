import unittest
from pathlib import Path

from keepword.rules import Rule, check, load_rules

EM_DASH = Rule(id="no-em-dash", chars=["\u2014", "\u2013", "\u2015"], message="Use a plain dash.")
BANNED = Rule(id="banned-words", words=["leverages", "robust", "seamless"])
NO_TRAILER = Rule(id="no-ai-trailer", pattern=r"(?im)^co-authored-by:.*claude", scopes=["commit"])


class CharRules(unittest.TestCase):
    def test_em_dash_is_caught_with_line_number(self):
        [v] = check("fine\nthis \u2014 not", [EM_DASH], "reply")
        self.assertEqual((v.rule_id, v.match, v.line), ("no-em-dash", "\u2014", 2))

    def test_look_alikes_are_caught(self):
        self.assertEqual(len(check("a \u2013 b \u2015 c", [EM_DASH], "reply")), 2)

    def test_plain_dash_passes(self):
        self.assertEqual(check("a - b", [EM_DASH], "reply"), [])


class WordRules(unittest.TestCase):
    def test_whole_word_case_insensitive(self):
        [v] = check("A Robust design", [BANNED], "reply")
        self.assertEqual(v.match, "Robust")

    def test_substring_is_not_a_match(self):
        self.assertEqual(check("robustness", [BANNED], "reply"), [])


class Scopes(unittest.TestCase):
    def test_rule_only_runs_in_its_scopes(self):
        text = "fix: thing\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        self.assertEqual(len(check(text, [NO_TRAILER], "commit")), 1)
        self.assertEqual(check(text, [NO_TRAILER], "reply"), [])

    def test_code_is_skipped_in_replies_but_not_files(self):
        text = "ok\n```\nx = '\u2014'\n```\nand `\u2014` inline"
        self.assertEqual(check(text, [EM_DASH], "reply"), [])
        self.assertEqual(len(check(text, [EM_DASH], "file")), 2)

    def test_quoted_words_are_mentions_in_replies_only(self):
        reply = 'Your banned list ("leverages", "robust") and \u201cseamless\u201d. But robust here.'
        [v] = check(reply, [BANNED], "reply")
        self.assertEqual(v.match, "robust")
        commit = 'git commit -m "feat: robust login"'
        self.assertEqual(len(check(commit, [BANNED], "commit")), 1)


class Loading(unittest.TestCase):
    def test_load_from_toml(self):
        rules = load_rules(
            '[[rule]]\nid = "no-em-dash"\nchars = ["\\u2014"]\nscopes = ["reply"]\n'
            '[[rule]]\nid = "banned"\nwords = ["robust"]\n'
        )
        self.assertEqual([r.id for r in rules], ["no-em-dash", "banned"])
        self.assertEqual(rules[1].scopes, ["reply", "file", "commit"])

    def test_rule_with_no_check_is_rejected(self):
        with self.assertRaises(ValueError):
            load_rules('[[rule]]\nid = "empty"\n')

    def test_typo_in_key_is_rejected(self):
        with self.assertRaises(ValueError):
            load_rules('[[rule]]\nid = "x"\nword = ["robust"]\n')

    def test_shipped_config_catches_my_rules(self):
        rules = load_rules(Path(__file__).parent.parent.joinpath("keepword.toml").read_text())
        commit = "feat: robust login \u2014 done\n\nGenerated with Claude Code"
        ids = [v.rule_id for v in check(commit, rules, "commit")]
        self.assertEqual(ids, ["banned-words", "no-em-dash", "no-ai-attribution"])


if __name__ == "__main__":
    unittest.main()
