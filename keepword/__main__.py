import argparse
import sys
from pathlib import Path

from keepword.measure import format_report, measure
from keepword.rules import load_rules
from keepword.transcripts import DEFAULT_ROOT, items


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="keepword", description="Make your agent keep its word.")
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure", help="how often Claude broke your rules, from its transcripts")
    m.add_argument("--rules", type=Path, default=Path("keepword.toml"))
    m.add_argument("--transcripts", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules.read_text())
    except (OSError, ValueError) as e:
        print(f"keepword: can't load rules from {args.rules}: {e}", file=sys.stderr)
        return 2
    print(format_report(measure(items(args.transcripts), rules)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
