"""Command-line interface for the Beijing Subway fare calculation system.

Supports interactive continuous queries of the form
"Starting Station; Ending Station" (comma or semicolon separators are accepted),
command-line options for output file, format, mode, transfer limit, line
preference, and the data integrity check.
"""

import argparse
import re
import sys

from .models import DataUpdateError, SubwayError
from .network import SubwayNetwork
from .pathfinding import MODES
from .query_service import QueryService
from .reporting import make_report
from .data_loader import DataLoadError

FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = ("quit", "exit", "q")
SEPARATOR_PATTERN = re.compile(r"[;,；，]")


def _non_negative_int(value):
    """argparse type: a non-negative integer."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'")
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def parse_arguments(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Beijing Subway fare calculation system (interactive CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="format", choices=["text", "json"], default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=list(MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser.parse_args(argv)


def parse_query_text(text):
    """Split an input line into (origin, destination) names.

    Raises:
        SubwayError: If the input does not contain exactly two non-empty parts.
    """
    parts = [part.strip() for part in SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise SubwayError(FORMAT_ERROR_MESSAGE)
    return parts[0], parts[1]


def resolve_station_name(network, text, label, stdout):
    """Standardise a station name, reporting fuzzy matches to the user.

    Raises:
        SubwayError: If no station matches the name.
    """
    resolved = network.resolve_station(text)
    if resolved is None:
        raise SubwayError(f"{label} station '{text}' does not exist, please check the station name")
    official, exact = resolved
    if not exact:
        stdout.write(f"Note: matched '{text}' to nearest station '{official}'\n")
    return official


def export_report(report, output_file):
    """Append a rendered report to a file."""
    try:
        with open(output_file, "a", encoding="utf-8") as handle:
            handle.write(report.content + "\n\n")
    except OSError as exc:
        raise SubwayError(f"Cannot write output file '{output_file}': {exc}") from exc


def process_query_line(line, network, service, args, stdout):
    """Handle one query line: validate, compute, print, and optionally export."""
    origin_text, dest_text = parse_query_text(line)
    origin = resolve_station_name(network, origin_text, "Starting", stdout)
    destination = resolve_station_name(network, dest_text, "Ending", stdout)
    if origin == destination:
        raise SubwayError("Starting station cannot be the same as the ending station")

    result = service.run(
        origin,
        destination,
        mode=args.mode,
        max_transfers=args.max_transfers,
        line_preference=args.line_preference,
    )
    report = make_report(result, args.format)
    stdout.write(report.content + "\n")
    if args.output_file:
        export_report(report, args.output_file)
        stdout.write(f"Result exported to {args.output_file}\n")


def run_integrity_check(network, stdout):
    """Print the data integrity report; return the process exit code."""
    report = network.check_integrity()
    stdout.write("Data integrity check\n")
    stdout.write(f"Stations: {len(network.station_names())}, "
                 f"connections: {network.graph.connection_count}, "
                 f"lines: {len(network.line_names())}\n")
    if not report.errors and not report.warnings:
        stdout.write("No problems found.\n")
    for message in report.errors:
        stdout.write(f"ERROR: {message}\n")
    for message in report.warnings:
        stdout.write(f"WARNING: {message}\n")
    stdout.write("Result: " + ("PASSED\n" if report.ok else "FAILED\n"))
    return 0 if report.ok else 1


def interactive_loop(args, network, service, stdin, stdout):
    """Run continuous query cycles until EOF or an exit word is entered."""
    stdout.write("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station'.\n")
    stdout.write("Type 'quit' to exit.\n")
    if args.line_preference and args.line_preference not in network.line_names():
        stdout.write(f"Warning: line preference '{args.line_preference}' is not a known line\n")
    while True:
        stdout.write("\nQuery> ")
        stdout.flush()
        line = stdin.readline()
        if line == "":
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in EXIT_WORDS:
            break
        try:
            process_query_line(line, network, service, args, stdout)
        except SubwayError as exc:
            stdout.write(f"Error: {exc}\n")
        except Exception as exc:  # last-resort guard so the session keeps running
            stdout.write(f"Unexpected error: {exc}\n")
        stdout.flush()


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_arguments(argv)
    stdout = sys.stdout
    try:
        network = SubwayNetwork()
    except (DataLoadError, ValueError, KeyError, DataUpdateError) as exc:
        stdout.write(f"Error: failed to load subway data: {exc}\n")
        return 1

    if args.check_data:
        return run_integrity_check(network, stdout)

    service = QueryService(network)
    try:
        interactive_loop(args, network, service, sys.stdin, stdout)
    except KeyboardInterrupt:
        stdout.write("\nInterrupted. Goodbye.\n")
        return 130
    stdout.write("Goodbye.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
