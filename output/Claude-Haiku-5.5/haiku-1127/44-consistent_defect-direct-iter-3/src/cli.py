"""
Command-line interface for the Beijing Subway fare calculation system.

Supports one-shot options (--check_data), output configuration (--format,
--output_file), routing configuration (--mode, --max_transfers,
--line_preference) and a continuous interactive query loop.
"""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH
from network import StationNotFoundError, SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig
from route_planner import CalculationError, RouteNotFoundError, plan_route
import report

INPUT_FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")
# ';' is the documented separator; ',' and full-width variants are also accepted.
SEPARATOR_PATTERN = re.compile(r"[;,\uff1b\uff0c]")
PREFERENCE_PATTERN = re.compile(r"[,;\uff1b\uff0c]")


class QueryError(Exception):
    """A user-facing error raised while processing a query."""


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="Append query results to this file")
    parser.add_argument("--format", choices=[report.FORMAT_TEXT, report.FORMAT_JSON], default=report.FORMAT_TEXT,
                        help="Output format: text or json (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="Path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="Run data integrity checks and exit")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def parse_line_preference(text):
    """Split a line preference argument into a list of line names."""
    if not text:
        return []
    return [part.strip() for part in PREFERENCE_PATTERN.split(text) if part.strip()]


def parse_query(text):
    """
    Parse 'Starting Station; Ending Station' input.

    Returns:
        (start, end) station name strings.

    Raises:
        QueryError: If the input does not contain exactly two non-empty parts.
    """
    parts = SEPARATOR_PATTERN.split(text)
    if len(parts) != 2:
        raise QueryError(INPUT_FORMAT_HINT)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(INPUT_FORMAT_HINT)
    return start, end


def resolve_endpoint(network, query, role, notes):
    """Resolve one station name, recording a note when fuzzy matching was used."""
    try:
        name, exact = network.resolve_station(query)
    except StationNotFoundError:
        raise QueryError(f"{role} station '{query}' does not exist, please check the station name")
    if not exact:
        notes.append(f"Note: {role.lower()} station '{query}' matched to nearest station '{name}'")
    return name


def run_query(network, text, config, fmt):
    """
    Execute one query and render its result.

    Returns:
        (rendered_output, notes)

    Raises:
        QueryError: For any user-facing failure.
    """
    origin_query, dest_query = parse_query(text)
    notes = []
    origin = resolve_endpoint(network, origin_query, "Starting", notes)
    destination = resolve_endpoint(network, dest_query, "Ending", notes)
    if origin == destination:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        result = plan_route(network, origin, destination, config)
    except RouteNotFoundError as exc:
        raise QueryError(str(exc))
    except CalculationError as exc:
        raise QueryError(str(exc))
    except ValueError as exc:
        raise QueryError(str(exc))

    try:
        output = report.render(result, fmt)
    except Exception as exc:
        raise QueryError(f"Report generation failed: {exc}")
    return output, notes


def run_check(network):
    """Print integrity check results. Returns 1 if errors were found, else 0."""
    issues = network.check_integrity()
    print("Data integrity check")
    print("-" * 40)
    if not issues:
        print("No issues found.")
        return 0
    errors = 0
    for level, message in issues:
        if level == "ERROR":
            errors += 1
        print(f"[{level}] {message}")
    print("-" * 40)
    print(f"Total issues: {len(issues)} (errors: {errors})")
    return 1 if errors else 0


def interactive_loop(network, config, args):
    """Run the continuous query loop until the user quits."""
    print("Beijing Subway fare query system")
    print("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
    while True:
        try:
            line = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            output, notes = run_query(network, text, config, args.format)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort safety net keeps the loop alive
            print(f"Unexpected error while processing query: {exc}")
            continue

        for note in notes:
            print(note)
        print(output)

        if args.output_file:
            try:
                report.write_output(output, args.output_file)
                print(f"Result saved to {args.output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
        print()


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        network = SubwayNetwork(data_path=DATA_FILE_PATH)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Failed to load subway data from {DATA_FILE_PATH}: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_check(network)

    preferred = parse_line_preference(args.line_preference)
    known_lines = set(network.all_lines())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line preference '{line}' is not a known line", file=sys.stderr)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2

    interactive_loop(network, config, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
