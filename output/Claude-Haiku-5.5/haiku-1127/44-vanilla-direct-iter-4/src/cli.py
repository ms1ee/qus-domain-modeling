"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import json
import sys

from data_loader import load_subway_data
from data_manager import SubwayNetwork
from pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES
from query_service import QueryError, parse_query_input, query_route
from report import format_json, format_text

EXIT_WORDS = ("q", "quit", "exit")
PROMPT = "Enter query ('Starting Station; Ending Station', or 'q' to quit): "


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra-based route planning)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1' (comma-separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_preferences(text):
    """Split a comma-separated line preference string into a list."""
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def run_data_check(network):
    """Print the data integrity report and return an exit status code."""
    report = network.check_integrity()
    print("Data integrity check")
    print(f"  Stations: {len(network.station_to_number)}")
    print(f"  Connections (raw): {len(network.connections)}")
    print(f"  Graph edges: {network.graph.edge_count}")
    if report["errors"]:
        print("Errors:")
        for message in report["errors"]:
            print(f"  - {message}")
    if report["warnings"]:
        print("Warnings:")
        for message in report["warnings"]:
            print(f"  - {message}")
    print("Result: PASSED" if report["ok"] else "Result: FAILED")
    return 0 if report["ok"] else 1


def render(result, output_format):
    """Render a query result in the requested format."""
    if output_format == "json":
        return format_json(result)
    return format_text(result)


def write_output(path, result, output_format):
    """Append a query result to the output file.

    Text results are appended as blocks; JSON results are appended as one
    compact JSON document per line (JSON Lines).
    """
    with open(path, "a", encoding="utf-8") as handle:
        if output_format == "json":
            handle.write(format_json(result, indent=None) + "\n")
        else:
            handle.write(format_text(result) + "\n\n")


def run_interactive(network, args, input_func=input, out=None):
    """Run the continuous query loop until the user quits.

    Returns:
        int: Exit status code.
    """
    out = out if out is not None else sys.stdout
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station'.", file=out)
    while True:
        try:
            text = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print(file=out)
            break
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.lower() in EXIT_WORDS:
            break
        try:
            start, end = parse_query_input(stripped)
            result = query_route(
                network, start, end,
                mode=args.mode,
                max_transfers=args.max_transfers,
                preferred_lines=args.preferred_lines,
            )
        except QueryError as exc:
            print(f"Error: {exc}", file=out)
            continue
        except Exception as exc:  # unexpected failures must not end the session
            print(f"Unexpected error while processing the query: {exc}", file=out)
            continue

        print(render(result, args.format), file=out)

        if args.output_file:
            try:
                write_output(args.output_file, result, args.format)
            except OSError as exc:
                print(f"Error: could not write output file: {exc}", file=out)
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork(load_subway_data())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(network)

    args.preferred_lines = parse_preferences(args.line_preference)
    known = set(network.line_names())
    for line in args.preferred_lines:
        if line not in known:
            print(f"Warning: preferred line '{line}' is not a known line", file=sys.stderr)

    return run_interactive(network, args)
