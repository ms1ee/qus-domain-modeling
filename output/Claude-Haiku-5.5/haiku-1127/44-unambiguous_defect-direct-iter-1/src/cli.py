"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from pathfinding import DEFAULT_MODE, VALID_MODES, NoPathError, PathfindingConfig
from route_report import format_result, plan_route
from subway_network import SubwayNetwork, normalize_name

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = ("q", "quit", "exit")
HELP_WORDS = ("help", "?")
HELP_TEXT = (
    "Enter a route as 'Starting Station; Ending Station' (separators ';' ',' also accepted).\n"
    "Commands: help, quit"
)


class InputFormatError(ValueError):
    """Raised when the query string does not match the expected format."""


class StationLookupError(ValueError):
    """Raised when a station name is empty, unknown or logically invalid."""


def parse_route_input(text):
    """Split 'Start; End' into (start, end) raw names.

    Raises:
        InputFormatError: if the text does not contain exactly two non-empty parts.
    """
    if text is None:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    parts = re.split(r"[;；,，]", text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def resolve_station(network, raw_name, role):
    """Standardize a user-typed station name against the official station list.

    Args:
        role: 'Starting' or 'Ending', used in error messages.

    Raises:
        StationLookupError: if the name is empty or does not exist.
    """
    name = raw_name.strip()
    if not name:
        raise StationLookupError(f"{role} station name is empty, please enter a station name")
    canonical = network.find_station(name)
    if canonical is None:
        message = f"{role} station '{name}' does not exist, please check the station name"
        suggestions = network.suggest_stations(name)
        if suggestions:
            message += ". Did you mean: " + ", ".join(suggestions) + "?"
        raise StationLookupError(message)
    return canonical


def answer_query(network, config, text):
    """Parse, validate and answer one route query. Returns a RouteResult."""
    raw_start, raw_end = parse_route_input(text)
    start = resolve_station(network, raw_start, "Starting")
    end = resolve_station(network, raw_end, "Ending")
    if start == end:
        raise StationLookupError("Starting station cannot be the same as the ending station")
    return plan_route(network, start, end, config)


def parse_line_preference(raw, network):
    """Parse a comma-separated line preference string into canonical line names."""
    if not raw:
        return []
    known = {normalize_name(line): line for line in network.all_lines()}
    result = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        canonical = known.get(normalize_name(part))
        if canonical is None:
            print(f"Warning: line '{part}' is not in the subway data; the preference will have no effect.")
            canonical = part
        if canonical not in result:
            result.append(canonical)
    return result


def build_config(args, network):
    """Build a PathfindingConfig from parsed command-line arguments."""
    preferred = parse_line_preference(args.line_preference, network)
    return PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=preferred)


def export_result(path, result, fmt):
    """Append a query result to the output file (JSON lines for json format)."""
    if fmt == "json":
        content = format_result(result, "json", indent=None) + "\n"
    else:
        content = format_result(result, "text") + "\n\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content)


def run_data_check(network):
    """Print the integrity report. Returns 0 if no errors were found, otherwise 1."""
    issues = network.check_integrity()
    print("Data integrity check")
    print("-" * 40)
    for level, message in issues:
        print(f"[{level}] {message}")
    errors = sum(1 for level, _ in issues if level == "ERROR")
    warnings = sum(1 for level, _ in issues if level == "WARNING")
    print("-" * 40)
    print(f"Done: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def run_interactive(network, config, args):
    """Continuous query loop. Returns the process exit code."""
    print("Beijing Subway Fare Calculator")
    print(HELP_TEXT)
    while True:
        try:
            raw = input("\nRoute> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in EXIT_WORDS:
            break
        if lowered in HELP_WORDS:
            print(HELP_TEXT)
            continue

        try:
            result = answer_query(network, config, text)
        except (InputFormatError, StationLookupError, ValueError) as exc:
            print(f"Error: {exc}")
            continue
        except NoPathError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # Path/fare calculation safety net
            print(f"Error: failed to calculate the route: {exc}")
            continue

        print(format_result(result, args.format))

        if args.output_file:
            try:
                export_result(args.output_file, result, args.format)
                print(f"Result appended to {args.output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
    return 0


def _non_negative_int(value):
    """argparse type for non-negative integers."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {value!r}")
    if number < 0:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {value!r}")
    return number


def build_arg_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation and route planning (CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=DEFAULT_MODE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name(s), comma-separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def main(argv=None):
    """CLI entry point. Returns an exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: could not load subway data from '{DATA_FILE_PATH}': {exc}")
        return 1

    network = SubwayNetwork(data)

    if args.check_data:
        return run_data_check(network)

    try:
        config = build_config(args, network)
    except ValueError as exc:
        print(f"Error: invalid configuration: {exc}")
        return 2

    return run_interactive(network, config, args)


if __name__ == "__main__":
    sys.exit(main())
