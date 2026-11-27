"""Command-line interface: argument parsing, interactive query loop and export."""

import argparse
import sys

import visualizer
from data_loader import DATA_FILE_PATH
from data_manager import check_integrity
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig
from query_service import QueryError, parse_query, run_query

EXIT_COMMANDS = {"quit", "exit", "q"}


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="Append query results to this file.")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of transfers allowed.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name, e.g. 'Line 1'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    return parser


def export_result(path, result, output_format):
    """Append a query result to the output file."""
    if output_format == "json":
        payload = visualizer.render_compact(result, "json") + "\n"
    else:
        payload = visualizer.render_compact(result, "text") + "\n\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(payload)


def handle_query(text, network, config, args):
    """Process one query line: parse, compute, print and optionally export."""
    start_input, end_input = parse_query(text)
    result = run_query(network, start_input, end_input, config)

    if not result.start_exact:
        print(f"Note: '{result.start_input}' is not an official station name; "
              f"matched to nearest station '{result.start}'")
    if not result.end_exact:
        print(f"Note: '{result.end_input}' is not an official station name; "
              f"matched to nearest station '{result.end}'")

    print(visualizer.render(result, args.format))

    if args.output_file:
        try:
            export_result(args.output_file, result, args.format)
            print(f"Result appended to {args.output_file}")
        except OSError as exc:
            print(f"Error: could not write output file: {exc}")


def interactive_loop(network, config, args):
    """Run continuous queries until the user quits or input ends."""
    print("Enter a query as 'Starting Station; Ending Station' (or 'quit' to exit).")
    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            handle_query(text, network, config, args)
        except QueryError as exc:
            print(f"Error: {exc}")
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Unexpected error: {exc}")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork.from_file(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: could not load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_integrity(network)
        print(report.format())
        return 0 if report.ok else 1

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=[args.line_preference] if args.line_preference else [],
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(f"Loaded {network.station_count} stations.")
    return interactive_loop(network, config, args)
