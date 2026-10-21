"""Count how often Claude broke each rule, by scope, week, and project."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta

from keepword.rules import SCOPES, Rule, check
from keepword.transcripts import Item


@dataclass
class Report:
    totals: Counter = field(default_factory=Counter)  # scope -> items seen
    hits: Counter = field(default_factory=Counter)  # (rule id, scope) -> items breaking it
    week_totals: Counter = field(default_factory=Counter)  # monday -> items seen
    week_hits: Counter = field(default_factory=Counter)  # monday -> items breaking any rule
    project_totals: Counter = field(default_factory=Counter)
    project_hits: Counter = field(default_factory=Counter)
    rule_ids: list[str] = field(default_factory=list)


def measure(items: Iterable[Item], rules: list[Rule]) -> Report:
    report = Report(rule_ids=[r.id for r in rules])
    for item in items:
        week = _monday(item.timestamp)
        report.totals[item.scope] += 1
        report.week_totals[week] += 1
        report.project_totals[item.project] += 1
        broken = {v.rule_id for v in check(item.text, rules, item.scope)}
        for rule_id in broken:
            report.hits[rule_id, item.scope] += 1
        if broken:
            report.week_hits[week] += 1
            report.project_hits[item.project] += 1
    return report


def _monday(timestamp: str) -> str:
    try:
        d = date.fromisoformat(timestamp[:10])
    except ValueError:
        return "unknown"
    return (d - timedelta(days=d.weekday())).isoformat()


def _rate(hit: int, total: int) -> str:
    return f"{hit}/{total} ({hit / total:.1%})" if total else "-"


def format_report(report: Report) -> str:
    out = ["By rule".ljust(22) + "".join(s.ljust(22) for s in SCOPES)]
    for rule_id in report.rule_ids:
        out.append(rule_id.ljust(22) + "".join(_rate(report.hits[rule_id, s], report.totals[s]).ljust(22) for s in SCOPES))
    out += ["", "By week (anything broken)"]
    out += [f"  {w}  {_rate(report.week_hits[w], report.week_totals[w])}" for w in sorted(report.week_totals)]
    out += ["", "Worst projects"]
    out += [f"  {p.ljust(30)}  {_rate(n, report.project_totals[p])}" for p, n in report.project_hits.most_common(5)]
    return "\n".join(out)
