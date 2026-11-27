"""Command-line entry point for the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --mode least_transfer --format json
    python src/main.py --output_file out/result.txt --max_transfers 2
    python src/main.py --line_preference "Line 1"
    python src/main.py --check_data
"""

import os
import sys

# Make sibling modules importable regardless of how this file is launched.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import argparse  # noqa: E402
import re  # noqa: E402

from data_integrity import DataIntegrityChecker  # noqa: E402
from data_loader import DataLoadError  # noqa: E402
from data_manager import DataManager  # noqa: E402
from pathfinding import (  # noqa: E402
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathNotFoundError,
)
from report import format_json, format_text, write_report  # noqa: E402
from route_service import QueryError, plan_route  # noqa: E402

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_PATTERN = re.compile(r"[;；,，]")

HELP_TEXT = """Enter a query in the form:  Starting Station; Ending Station
  Examples:  西直门; 国贸      苹果园;四惠东
Commands:  help  - show this help
           quit  - exit the program (also: exit, q)"""


class InputFormatError(QueryError):
    """Raised when a query line does not contain exactly two station names."""


def parse_query(text):
    """Split a query line into (starting station, ending station).

    Accepts ';' (or full-width '；', ',' and '，') as separator.

    Raises:
        InputFormatError: If the input does not contain exactly two non-empty parts.
    """
    parts = [p.strip() for p in SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0], parts[1]


def _non_negative_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation and route query system."
    )
    parser.add_argument("--output_file", default=None,
                        help="Export query results to this file (appended per query).")
    parser.add_argument("--format", dest="format", choices=("text", "json"), default="text",
                        help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="Maximum number of allowed transfers.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name, e.g. \"Line 1\".")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    return parser


def run_interactive(dm, args, preference):
    """Run the continuous query loop until the user quits or input ends."""
    print("Beijing Subway fare calculator. Type 'help' for instructions.")
    while True:
        try:
            raw = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in ("quit", "exit", "q"):
            break
        if lowered in ("help", "?"):
            print(HELP_TEXT)
            continue

        try:
            start, end = parse_query(text)
            result = plan_route(
                dm, start, end,
                mode=args.mode,
                max_transfers=args.max_transfers,
                line_preference=preference,
            )
            content = format_json(result) if args.format == "json" else format_text(result)
            print(content)
            if args.output_file:
                write_report(content + "\n", args.output_file, append=True)
                print(f"Result appended to {os.path.abspath(args.output_file)}")
        except QueryError as exc:
            print(f"Error: {exc}")
        except PathNotFoundError as exc:
            print(f"Error: no route found between the stations ({exc}). "
                  "Try relaxing --max_transfers or the line preference.")
        except OSError as exc:
            print(f"Error: cannot write output file: {exc}")
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Error: unexpected failure while processing the query: {exc}")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        dm = DataManager()
    except (DataLoadError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(dm)
        passed = checker.run()
        print(checker.report())
        return 0 if passed else 1

    preference = None
    if args.line_preference:
        preference = dm.find_line(args.line_preference)
        if preference is None:
            print(f"Error: line '{args.line_preference}' does not exist. "
                  f"Available lines: {', '.join(dm.line_names())}", file=sys.stderr)
            return 2

    if args.output_file:
        try:
            write_report("", args.output_file, append=False)  # start a fresh export file
        except OSError as exc:
            print(f"Error: cannot create output file: {exc}", file=sys.stderr)
            return 2

    return run_interactive(dm, args, preference)


if __name__ == "__main__":
    sys.exit(main())
