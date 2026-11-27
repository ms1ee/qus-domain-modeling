"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys

from data_loader import load_subway_data
from fare_calculator import Sum_money  # noqa: F401  (fare module is part of the runtime)
from network import SubwayNetwork
from pathfinding import PathfindingConfig, VALID_MODES
from report import render_result
from route_service import (
    EndpointNotFoundError,
    FareCalculationError,
    FORMAT_MESSAGE,
    InvalidQueryError,
    PathNotFoundError,
    RouteQueryError,
    RouteService,
    parse_query_input,
)

EXIT_COMMANDS = ("quit", "exit", "q")


def build_arg_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest path and fare query)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="output_format", choices=["text", "json"], default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_line_preference(value):
    """Convert the --line_preference argument into a list of line names."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def format_integrity_report(report):
    """Render the data integrity check result as text."""
    lines = []
    status = "PASSED" if report["ok"] else "FAILED"
    lines.append(f"Data integrity check: {status}")
    lines.append(f"Stations: {report['station_count']}")
    lines.append(f"Connections: {report['connection_count']}")
    lines.append(f"Lines: {report['line_count']}")
    for message in report["errors"]:
        lines.append(f"ERROR: {message}")
    for message in report["warnings"]:
        lines.append(f"WARNING: {message}")
    if report["ok"] and not report["warnings"]:
        lines.append("No problems found.")
    return "\n".join(lines)


def _format_error(exc):
    """Build the user-facing message for a query error."""
    message = str(exc)
    if isinstance(exc, EndpointNotFoundError) and exc.suggestions:
        message += ". Did you mean: " + ", ".join(exc.suggestions) + "?"
    return message


def append_to_file(path, content):
    """Append rendered output to a file, separated by a blank line."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n\n")


def handle_query(service, text, config, output_format, output_file=None, output_func=print):
    """Process one query line. Returns True on success, False on error."""
    try:
        start, end = parse_query_input(text)
        result = service.query(start, end, config)
    except EndpointNotFoundError as exc:
        output_func(f"Error: {_format_error(exc)}")
        return False
    except InvalidQueryError as exc:
        output_func(f"Error: {exc}")
        return False
    except PathNotFoundError as exc:
        output_func(f"Error: {exc}")
        return False
    except FareCalculationError as exc:
        output_func(f"Error: {exc}")
        return False
    except RouteQueryError as exc:
        output_func(f"Error: {exc}")
        return False
    except Exception as exc:  # last-resort guard so the session keeps running
        output_func(f"Error: unexpected failure while processing query: {exc}")
        return False

    rendered = render_result(result, output_format)
    output_func(rendered)

    if output_file:
        try:
            append_to_file(output_file, rendered)
        except OSError as exc:
            output_func(f"Warning: could not write to output file '{output_file}': {exc}")
    return True


def run_interactive(service, config, output_format, output_file=None,
                    input_func=input, output_func=print):
    """Run the continuous query loop until the user exits.

    Returns:
        The number of successful queries.
    """
    successes = 0
    output_func("Enter a query as 'Starting Station; Ending Station' (type 'quit' to exit).")
    while True:
        try:
            line = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        if handle_query(service, text, config, output_format, output_file, output_func):
            successes += 1
    return successes


def main(argv=None):
    """Entry point for the CLI. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data()
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    try:
        network = SubwayNetwork(data)
    except Exception as exc:
        print(f"Error: failed to build subway network: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = network.check_integrity()
        print(format_integrity_report(report))
        return 0 if report["ok"] else 1

    preferred = parse_line_preference(args.line_preference)
    known_lines = set(network.line_names())
    unknown = [line for line in preferred if line not in known_lines]
    if unknown:
        print("Warning: unknown preferred line(s): " + ", ".join(unknown), file=sys.stderr)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))

    service = RouteService(network)
    print("Beijing Subway fare calculator")
    print(f"Input format: {FORMAT_MESSAGE}" if False else "Input format: 'Starting Station; Ending Station'")
    run_interactive(service, config, args.output_format, args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
