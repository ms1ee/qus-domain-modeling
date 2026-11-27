"""Command-line interface for the Beijing Subway fare calculator."""

import argparse
import re
import sys
from datetime import datetime

from data_loader import DataLoadError
from fare_calculator import calculate_fare  # noqa: F401  (available for diagnostics)
from models import Query
from network import SubwayNetwork
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    SUPPORTED_MODES,
    PathfindingConfig,
)
from report import build_report, build_summary
from route_planner import PathNotFoundError, plan_route

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_PATTERN = re.compile(r"[;,\uff1b\uff0c]")
EXIT_WORDS = ("q", "quit", "exit")


class InputFormatError(ValueError):
    """Raised when a query line does not follow the 'Start; End' format."""


def _non_negative_int(text):
    """argparse type: a non-negative integer."""
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return value


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation and route query tool.")
    parser.add_argument("--output_file", default=None,
                        help="write the latest query result to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=SUPPORTED_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query_text(text):
    """Split 'Starting Station; Ending Station' into two stripped names.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty parts.
    """
    parts = [part.strip() for part in SEPARATOR_PATTERN.split(text.strip())]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0], parts[1]


def _resolve_station(network, raw, label):
    """Resolve a station name, printing prompts. Returns canonical name or None."""
    name, exact = network.resolve_station(raw)
    if name is None:
        print(f"{label} station '{raw}' does not exist, please check the station name")
        return None
    if not exact:
        print(f"Note: '{raw}' is not an exact station name; using nearest station '{name}'")
    return name


def _print_integrity(report):
    """Print a data integrity report."""
    print("Data integrity check: " + ("PASSED" if report.is_valid else "FAILED"))
    for error in report.errors:
        print(f"  ERROR: {error}")
    for warning in report.warnings:
        print(f"  WARNING: {warning}")
    if not report.errors and not report.warnings:
        print("  No issues found.")


def _write_output(path, content):
    """Write content to a file (UTF-8). Returns True on success."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.write("\n")
        return True
    except OSError as exc:
        print(f"Could not write output file '{path}': {exc}")
        return False


def handle_query(network, config, text, args):
    """Process one query line: validate, compute, render and output."""
    start_raw, end_raw = parse_query_text(text)

    start = _resolve_station(network, start_raw, "Starting")
    end = _resolve_station(network, end_raw, "Ending")
    if start is None or end is None:
        return
    if start == end:
        print("Starting station cannot be the same as the ending station")
        return

    try:
        route = plan_route(network, start, end, config)
    except PathNotFoundError as exc:
        print(f"Path calculation failed: {exc}")
        return
    except Exception as exc:  # defensive: unexpected path-search failure
        print(f"Path calculation error: {exc}")
        return

    try:
        summary = build_summary(route)
    except Exception as exc:  # defensive: fare/time calculation failure
        print(f"Fare calculation error: {exc}")
        return

    query = Query(
        start_name=start,
        end_name=end,
        mode=config.mode,
        max_transfers=config.max_transfers,
        line_preference=", ".join(config.preferred_lines) or None,
        timestamp=datetime.now(),
    )

    output_path = args.output_file
    try:
        report = build_report(query, route, summary, args.format, output_path)
    except ValueError as exc:
        print(f"Report error: {exc}")
        return

    print(report.content)
    if output_path:
        if _write_output(output_path, report.content):
            print(f"Result saved to {output_path}")


def run_cli(argv=None) -> int:
    """Run the CLI. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork()
    except (DataLoadError, OSError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = network.check_integrity()
        _print_integrity(report)
        return 0 if report.is_valid else 1

    preferred = []
    if args.line_preference:
        resolved = network.resolve_line_name(args.line_preference)
        if resolved is None:
            print(f"Warning: line '{args.line_preference}' is not a known line; using it as given")
            preferred = [args.line_preference.strip()]
        else:
            preferred = [resolved]

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway Fare Calculator (type 'quit' to exit)")
    while True:
        try:
            line = input("Enter query ('Starting Station; Ending Station'): ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        try:
            handle_query(network, config, text, args)
        except InputFormatError as exc:
            print(exc)
        except Exception as exc:  # keep the session alive on unexpected errors
            print(f"Unexpected error: {exc}")
    return 0
