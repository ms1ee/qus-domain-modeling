"""Command-line interface of the Beijing Subway fare calculation system.

Usage:
    python main.py [--format text|json] [--mode MODE] [--max_transfers N]
                   [--line_preference "Line 1"] [--output_file PATH] [--check_data]

Queries are read from standard input, one per line, in the form
"Starting Station; Ending Station" (``;``, ``,`` or ``->`` separators are
accepted). Enter ``quit`` or ``exit`` (or EOF) to stop.
"""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH
from data_manager import SubwayNetwork, format_integrity_report
from fare_calculator import FareCalculationError
from pathfinding import VALID_MODES, PathfindingConfig, RouteNotFoundError
from route_report import build_route_result, format_json, format_text, to_dict

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_RE = re.compile(r"\s*(?:->|→|[;；,，])\s*")
EXIT_COMMANDS = {"quit", "exit", "q", "退出"}


class InputValidationError(Exception):
    """Raised for invalid user input."""


def parse_query(line):
    """Split an input line into (start, end) raw names."""
    parts = SEPARATOR_RE.split(line.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputValidationError(FORMAT_ERROR)
    return parts[0].strip(), parts[1].strip()


def validate_query(network, line):
    """Validate an input line and return canonical (start, end) names."""
    raw_start, raw_end = parse_query(line)
    start = network.find_station(raw_start)
    if start is None:
        raise InputValidationError(_missing_msg(network, "Starting", raw_start))
    end = network.find_station(raw_end)
    if end is None:
        raise InputValidationError(_missing_msg(network, "Ending", raw_end))
    if start == end:
        raise InputValidationError("Starting station cannot be the same as the ending station")
    return start, end


def _missing_msg(network, kind, name):
    msg = "%s station '%s' does not exist, please check the station name" % (kind, name)
    suggestions = network.suggest_stations(name)
    if suggestions:
        msg += " (did you mean: %s?)" % ", ".join(suggestions)
    return msg


def build_parser():
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", help="Export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated (e.g. 'Line 1')")
    parser.add_argument("--check_data", action="store_true", help="Check data integrity and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return parser


def _write_output(path, fmt, results):
    with open(path, "w", encoding="utf-8") as handle:
        if fmt == "json":
            payload = to_dict(results[0]) if len(results) == 1 else [to_dict(r) for r in results]
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        else:
            handle.write("\n\n".join(format_text(r) for r in results) + "\n")


def run_query(network, line, config):
    """Process one query line. Returns (RouteResult or None, error message or None)."""
    try:
        start, end = validate_query(network, line)
    except InputValidationError as exc:
        return None, str(exc)
    try:
        return build_route_result(network, start, end, config), None
    except FareCalculationError as exc:
        return None, "Fare calculation error: %s" % exc
    except RouteNotFoundError as exc:
        return None, "Path calculation error: %s" % exc
    except Exception as exc:  # noqa: BLE001 - last-resort guard
        return None, "Path calculation error: %s" % exc


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers cannot be negative")
        return 2

    try:
        network = SubwayNetwork(path=args.data_file)
    except (OSError, ValueError) as exc:
        print("Error: failed to load subway data: %s" % exc)
        return 1

    if args.check_data:
        report = network.check_integrity()
        print(format_integrity_report(report))
        return 0 if report["passed"] else 1

    preferred = []
    if args.line_preference:
        preferred = [p.strip() for p in re.split(r"[,，;；]", args.line_preference) if p.strip()]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    interactive = sys.stdin.isatty()
    if interactive:
        print("Beijing Subway Fare Calculation System")
        print("Enter queries as 'Starting Station; Ending Station'. Type 'quit' to exit.")

    results = []
    while True:
        if interactive:
            print("> ", end="", flush=True)
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line.casefold() in EXIT_COMMANDS:
            break
        result, error = run_query(network, line, config)
        if error:
            print(error)
            continue
        print(format_json(result) if args.format == "json" else format_text(result))
        results.append(result)
        if args.output_file:
            try:
                _write_output(args.output_file, args.format, results)
            except OSError as exc:
                print("Error: failed to write output file: %s" % exc)
    if interactive:
        print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
