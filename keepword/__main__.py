import argparse
import sys
from pathlib import Path

from keepword.measure import format_report, measure
from keepword.rules import find_rules, load_rules
from keepword.transcripts import DEFAULT_ROOT, items


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="keepword", description="Make your agent keep its word.")
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure", help="how often Claude broke your rules, from its transcripts")
    m.add_argument("--rules", type=Path, help="default: ./keepword.toml, else the bundled rules")
    m.add_argument("--transcripts", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)

    source, label = (args.rules, str(args.rules)) if args.rules else find_rules(Path.cwd())
    try:
        rules = load_rules(source.read_text())
    except (OSError, ValueError) as e:
        print(f"keepword: can't load rules from {source}: {e}", file=sys.stderr)
        return 2
    print(f"Rules: {label}\n")
    print(format_report(measure(items(args.transcripts), rules)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
