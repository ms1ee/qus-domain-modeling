"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from path_report import render_json, render_text, write_report
from pathfinding import VALID_MODES, PathfindingConfig
from route_service import RouteError, plan_route
from subway_network import SubwayNetwork

EXIT_WORDS = ("quit", "exit", "q")
FORMAT_CHOICES = ("text", "json")


def build_parser():
    """Create the argument parser for the command line."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=FORMAT_CHOICES, default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_line_preference(value):
    """Split a comma-separated line preference string into a list of line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_query(text):
    """Parse 'Starting Station; Ending Station' (a comma is also accepted).

    Returns:
        (start, end) station name strings.

    Raises:
        ValueError: if the input does not contain exactly two non-empty names.
    """
    parts = re.split(r"[;,]", text)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    return parts[0].strip(), parts[1].strip()


def run_check(network):
    """Print the data integrity report and return an exit code (1 on errors)."""
    issues = network.check_integrity()
    if not issues:
        print("Data integrity check passed: no issues found.")
        return 0
    for issue in issues:
        print(issue)
    errors = sum(1 for issue in issues if issue.startswith("[ERROR]"))
    warnings = len(issues) - errors
    print(f"Integrity check finished: {errors} error(s), {warnings} warning(s).")
    return 1 if errors else 0


def describe_match(query, official, exact):
    """Return a notice when the input was matched to a nearest official name."""
    if exact:
        return ""
    return (f"Note: '{query}' is not an official station name; "
            f"matched to nearest station '{official}'.")


def run_cli(argv=None):
    """Run the CLI. Returns the process exit code."""
    args = build_parser().parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be non-negative", file=sys.stderr)
        return 2

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data)
    except (DataLoadError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_check(network)

    preferred = parse_line_preference(args.line_preference)
    known_lines = set(network.lines())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: preferred line '{line}' is not in the network",
                  file=sys.stderr)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway fare calculator.")
    print("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")

    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            start_query, end_query = parse_query(text)
        except ValueError as exc:
            print(f"Error: {exc}")
            continue

        try:
            result = plan_route(network, start_query, end_query, config)
        except RouteError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never terminate the query loop
            print(f"Error: unexpected failure during path calculation: {exc}")
            continue

        for query, official, exact in ((start_query, result.start, result.start_exact),
                                       (end_query, result.end, result.end_exact)):
            notice = describe_match(query, official, exact)
            if notice:
                print(notice, file=sys.stderr)

        output = render_json(result) if args.format == "json" else render_text(result)
        print(output)

        if args.output_file:
            try:
                write_report(output, args.output_file, append=True)
                print(f"Result appended to {args.output_file}")
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}", file=sys.stderr)

    return 0
