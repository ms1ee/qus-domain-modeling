"""Command-line interface for the Beijing Subway fare calculation system.

Run with:  python src/cli.py [--format text|json] [--mode MODE]
           [--max_transfers N] [--line_preference LINE]
           [--output_file PATH] [--check_data]
"""

import argparse
import re
import sys

from data_loader import DataLoadError
from data_manager import DataManager
from fare_calculator import Sum_money  # noqa: F401  (fare is computed inside report)
from pathfinding import DEFAULT_MODE, VALID_MODES, PathfindingConfig, PathNotFoundError
from report import compute_route, export_results, render_report

QUERY_SEPARATORS = r"[;；,，]"
QUIT_COMMANDS = ("quit", "exit", "q")
HELP_COMMANDS = ("help", "?")

HELP_TEXT = """Enter a query in the form 'Starting Station; Ending Station'
(a comma may also be used as separator).
Commands: help, quit"""


class QueryError(Exception):
    """Raised for invalid user input."""


def _normalize(text):
    """Normalise a name for lenient matching (case and separators ignored)."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def build_name_index(graph):
    """Map normalised station names to official station names."""
    return {_normalize(name): name for name in graph.station_names()}


def resolve_station(raw, name_index, label):
    """Standardise a user-entered station name against the official names."""
    key = _normalize(raw)
    if not key or key not in name_index:
        raise QueryError(f"{label} station '{raw.strip()}' does not exist, please check the station name")
    return name_index[key]


def parse_query(text):
    """Split a query into (starting station, ending station) strings."""
    parts = [part.strip() for part in re.split(QUERY_SEPARATORS, text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise QueryError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    return parts[0], parts[1]


def parse_line_preference(value, known_lines):
    """Parse a comma-separated list of preferred lines (e.g. 'Line 1,Line 2')."""
    if not value:
        return []
    index = {_normalize(line): line for line in known_lines}
    preferred = []
    for part in re.split(r"[,，;；]", value):
        token = part.strip()
        if not token:
            continue
        key = _normalize(token)
        if key in index:
            line = index[key]
        elif "line" + key in index:
            line = index["line" + key]
        else:
            raise ValueError(
                f"unknown line '{token}'. Known lines: {', '.join(known_lines)}"
            )
        if line not in preferred:
            preferred.append(line)
    return preferred


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=DEFAULT_MODE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser.parse_args(argv)


def process_query(text, graph, name_index, config):
    """Parse, validate and compute a single query; return the result record."""
    start_raw, end_raw = parse_query(text)
    start = resolve_station(start_raw, name_index, "Starting")
    end = resolve_station(end_raw, name_index, "Ending")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    return compute_route(graph, start, end, config)


def run_interactive(graph, config, fmt, output_file):
    """Run the continuous query loop until the user quits."""
    name_index = build_name_index(graph)
    results = []
    print("Beijing Subway fare calculator. " + HELP_TEXT)
    while True:
        try:
            line = input("\nQuery> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in QUIT_COMMANDS:
            break
        if lowered in HELP_COMMANDS:
            print(HELP_TEXT)
            continue

        try:
            result = process_query(text, graph, name_index, config)
            rendered = render_report(result, fmt)
        except QueryError as exc:
            print(f"Input error: {exc}")
            continue
        except PathNotFoundError as exc:
            print(f"Path error: {exc}")
            continue
        except (ValueError, KeyError, ArithmeticError) as exc:
            print(f"Calculation error: {exc}")
            continue
        except Exception as exc:  # last-resort guard to keep the session alive
            print(f"Unexpected error while processing query: {exc}")
            continue

        print(rendered)
        if output_file:
            results.append(result)
            try:
                export_results(results, fmt, output_file)
                print(f"Results exported to {output_file}")
            except OSError as exc:
                print(f"Export error: cannot write '{output_file}': {exc}")
    return 0


def main(argv=None):
    """Entry point. Returns the process exit code."""
    args = parse_args(argv)

    manager = DataManager()
    try:
        manager.load()
        graph = manager.build_graph()
    except DataLoadError as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        issues = manager.check_integrity()
        if not issues:
            print("Data integrity check passed: no issues found.")
            print(f"Stations: {graph.node_count}, connections: {graph.edge_count}")
            return 0
        print(f"Data integrity check found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must not be negative", file=sys.stderr)
        return 2

    try:
        preferred = parse_line_preference(args.line_preference, manager.get_lines())
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    try:
        config = PathfindingConfig(args.mode, args.max_transfers, preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_interactive(graph, config, args.format, args.output_file)


if __name__ == "__main__":
    sys.exit(main())
