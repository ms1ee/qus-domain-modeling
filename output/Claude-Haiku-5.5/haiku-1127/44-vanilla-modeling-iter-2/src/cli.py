"""Command-line interface: argument parsing, input validation and the query loop."""

import argparse
import sys

import report
from data_loader import DataLoadError
from pathfinding import PathfindingConfig, VALID_MODES
from route_planner import RouteError, plan_route
from subway_network import SubwayNetwork

PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "
INPUT_FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Raised for invalid user input (format, unknown station, same station)."""


def _non_negative_int(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation system (Dijkstra-based route planning).",
    )
    parser.add_argument("--output_file", default=None,
                        help="export each query result to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. \"Line 1\"")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw names."""
    normalized = text.replace("\uff1b", ";").strip()
    parts = normalized.split(";")
    if len(parts) != 2:
        raise QueryError(INPUT_FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(INPUT_FORMAT_ERROR)
    return start, end


def validate_stations(network, start, end):
    """Standardize and verify station names; return official names."""
    std_start = network.standardize_name(start)
    if std_start is None:
        raise QueryError(f"Starting station '{start}' does not exist, please check the station name")
    std_end = network.standardize_name(end)
    if std_end is None:
        raise QueryError(f"Ending station '{end}' does not exist, please check the station name")
    if std_start == std_end:
        raise QueryError("Starting station cannot be the same as the ending station")
    return std_start, std_end


def run_data_check(network):
    """Print the data integrity report. Returns 0 when passed, 1 otherwise."""
    result = network.check_integrity()
    print("Data integrity check: " + ("PASSED" if result.passed else "FAILED"))
    for issue in result.issues:
        print(f"  - {issue}")
    if not result.issues:
        print("  No issues found.")
    return 0 if result.passed else 1


def run_interactive(network, config, output_file=None, fmt="text",
                    input_func=input, output=print):
    """Run the continuous query loop until the user quits or input ends.

    Returns:
        Exit code (0 on normal termination).
    """
    output("Beijing Subway fare calculator. Type 'quit' to exit.")
    while True:
        try:
            raw = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            output("")
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in ("quit", "exit"):
            break
        try:
            start_raw, end_raw = parse_query(text)
            start, end = validate_stations(network, start_raw, end_raw)
            result = plan_route(network, start, end, config)
            rendered = report.build_report(result, fmt)
            output(rendered.content)
            if output_file:
                report.write_report(rendered, output_file)
                output(f"Result exported to {output_file}")
        except QueryError as exc:
            output(f"Error: {exc}")
        except RouteError as exc:
            output(f"Error: {exc}")
        except OSError as exc:
            output(f"Error: could not write output file: {exc}")
        except Exception as exc:  # defensive: keep the session alive
            output(f"Error: unexpected failure while processing query: {exc}")
    output("Goodbye.")
    return 0


def main(argv=None):
    """CLI entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork()
    except (DataLoadError, KeyError, TypeError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(network)

    preferred = []
    if args.line_preference:
        preferred = [p.strip() for p in args.line_preference.split(",") if p.strip()]
        for line in preferred:
            if line not in network.line_names:
                print(f"Warning: line preference '{line}' is not a known line", file=sys.stderr)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_interactive(network, config, output_file=args.output_file, fmt=args.format)
