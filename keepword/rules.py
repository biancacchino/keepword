"""Load keepword rules from TOML and check text against them."""

import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

SCOPES = ["reply", "file", "commit"]
# Fenced blocks and inline code. Quoting a banned thing in code is not using it.
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
# Quoted phrases in replies are mentions too. Not in commits: `-m "..."` quotes the whole message.
_QUOTE = re.compile(r'"[^"\n]*"|\u201c[^\u201d\n]*\u201d')


@dataclass
class Rule:
    id: str
    chars: list[str] = field(default_factory=list)
    words: list[str] = field(default_factory=list)
    pattern: str | None = None
    scopes: list[str] = field(default_factory=lambda: list(SCOPES))
    message: str = ""

    def __post_init__(self):
        if not (self.chars or self.words or self.pattern):
            raise ValueError(f"rule {self.id!r} needs chars, words, or pattern")
        unknown = set(self.scopes) - set(SCOPES)
        if unknown:
            raise ValueError(f"rule {self.id!r} has unknown scopes {sorted(unknown)}, use {SCOPES}")
        # Separate regexes so a pattern's own flags like (?im) stay valid.
        self._regexes = []
        if self.chars:
            self._regexes.append(re.compile("[" + "".join(map(re.escape, self.chars)) + "]"))
        if self.words:
            self._regexes.append(re.compile(r"(?i)\b(?:" + "|".join(map(re.escape, self.words)) + r")\b"))
        if self.pattern:
            self._regexes.append(re.compile(self.pattern))


@dataclass
class Violation:
    rule_id: str
    match: str
    line: int
    message: str


def find_rules(cwd: Path) -> tuple[Traversable, str]:
    """The project's keepword.toml if it has one, else the bundled defaults. Returns (source, label)."""
    local = cwd / "keepword.toml"
    if local.exists():
        return local, "keepword.toml"
    return resources.files("keepword") / "keepword.toml", "bundled defaults"


def load_rules(toml_text: str) -> list[Rule]:
    rules = []
    for raw in tomllib.loads(toml_text).get("rule", []):
        try:
            rules.append(Rule(**raw))
        except TypeError as e:  # unknown or missing keys
            raise ValueError(f"rule {raw.get('id')!r}: {e}") from None
    return rules


def check(text: str, rules: list[Rule], scope: str) -> list[Violation]:
    for regex, scopes in ((_CODE, ("reply", "commit")), (_QUOTE, ("reply",))):
        if scope in scopes:
            # Blank out the span but keep its newlines so line numbers stay right.
            text = regex.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)
    found = []
    for rule in rules:
        if scope not in rule.scopes:
            continue
        for regex in rule._regexes:
            for m in regex.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                found.append((m.start(), Violation(rule.id, m.group(), line, rule.message)))
    return [v for _, v in sorted(found, key=lambda pair: pair[0])]
