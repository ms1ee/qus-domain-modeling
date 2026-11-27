"""Command-line interface: argument parsing, input validation and query loop."""

import argparse
import re

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import check_data_integrity, format_integrity_report
from network import SubwayNetwork, normalize_station_name
from pathfinding import (
    VALID_MODES,
    NoRouteError,
    PathfindingConfig,
    ShortestPath,
    build_route,
)
from visualizer import (
    build_summary,
    export_report,
    format_json_report,
    format_text_report,
)

FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_PATTERN = re.compile(r"\s*[;,\uff1b\uff0c]\s*")
QUIT_COMMANDS = ("quit", "exit", "q")
OUTPUT_FORMATS = ("text", "json")


class CLIError(Exception):
    """Base class for user-facing errors."""


class InputFormatError(CLIError):
    """Raised when the query string is malformed."""


class StationNotFoundError(CLIError):
    """Raised when a station name cannot be resolved."""


class LogicError(CLIError):
    """Raised for logically invalid queries."""


class PathCalculationError(CLIError):
    """Raised when path computation fails."""


class FareCalculationError(CLIError):
    """Raised when fare calculation fails."""


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="beijing_subway_fare",
        description="Beijing Subway fare calculation system (interactive CLI).",
    )
    parser.add_argument(
        "--output_file", default=None,
        help="Append each query result to this file (text or JSON lines).",
    )
    parser.add_argument(
        "--format", choices=OUTPUT_FORMATS, default="text",
        help="Output format: 'text' or 'json' (default: text).",
    )
    parser.add_argument(
        "--mode", choices=VALID_MODES, default="shortest_distance",
        help="Path query mode (default: shortest_distance).",
    )
    parser.add_argument(
        "--max_transfers", type=int, default=None,
        help="Maximum number of allowed transfers.",
    )
    parser.add_argument(
        "--line_preference", default=None,
        help="Preferred line name, e.g. 'Line 1' (comma-separate for several).",
    )
    parser.add_argument(
        "--check_data", action="store_true",
        help="Run data integrity checks and exit.",
    )
    return parser


def parse_query(raw):
    """Split a 'Starting Station; Ending Station' query string.

    Returns:
        (start_text, end_text)

    Raises:
        InputFormatError: If the format is invalid.
    """
    text = (raw or "").strip()
    if not text:
        raise InputFormatError(FORMAT_HINT)
    parts = SEPARATOR_PATTERN.split(text)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(FORMAT_HINT)
    return parts[0].strip(), parts[1].strip()


def resolve_station(network, raw_name, role):
    """Resolve a station name and return (official_name, notice_or_None).

    Raises:
        StationNotFoundError: If no station matches.
    """
    name = normalize_station_name(raw_name)
    if not name:
        raise InputFormatError(FORMAT_HINT)
    result = network.resolve_station(name)
    if result is None:
        raise StationNotFoundError(
            f"{role} station '{name}' does not exist, please check the station name"
        )
    official, exact = result
    if exact:
        return official, None
    return official, f"Note: {role.lower()} station '{name}' matched to nearest station '{official}'"


def answer_query(network, start_raw, end_raw, config):
    """Run a complete query and return (route, summary, notes).

    Raises:
        CLIError subclasses for every user-facing failure.
    """
    start, start_note = resolve_station(network, start_raw, "Starting")
    end, end_note = resolve_station(network, end_raw, "Ending")
    if start == end:
        raise LogicError("Starting station cannot be the same as the ending station")

    notes = [note for note in (start_note, end_note) if note]
    source_no = network.station_to_number[start]
    target_no = network.station_to_number[end]

    try:
        shortest = ShortestPath(network.graph, source_no, config)
        route = build_route(shortest, target_no, network.number_to_name)
    except NoRouteError as exc:
        raise PathCalculationError(str(exc)) from exc
    except Exception as exc:  # defensive: any unexpected search failure
        raise PathCalculationError(f"Path calculation failed: {exc}") from exc

    try:
        summary = build_summary(route)
    except Exception as exc:  # defensive: fare/time computation failure
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    return route, summary, notes


def render_result(route, summary, fmt, query_info, compact=False):
    """Render a query result in the requested format."""
    if fmt == "json":
        return format_json_report(route, summary, query_info, indent=None if compact else 2)
    return format_text_report(route, summary)


def run_query_loop(network, config, fmt, output_file, input_func=input, output_func=print):
    """Interactive continuous-query loop. Returns when the user quits."""
    query_info = {
        "max_transfers": config.max_transfers,
        "line_preference": config.preferred_lines or None,
    }
    output_func("Beijing Subway Fare Calculator")
    output_func("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")

    while True:
        try:
            raw = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break

        if not raw or not raw.strip():
            continue
        if raw.strip().lower() in QUIT_COMMANDS:
            break

        try:
            start_raw, end_raw = parse_query(raw)
            route, summary, notes = answer_query(network, start_raw, end_raw, config)
            for note in notes:
                output_func(note)
            output_func(render_result(route, summary, fmt, query_info))
            if output_file:
                export_report(render_result(route, summary, fmt, query_info, compact=True),
                              output_file)
                output_func(f"Result appended to {output_file}")
        except CLIError as exc:
            output_func(f"Error: {exc}")
        except OSError as exc:
            output_func(f"Error: could not write output file: {exc}")

    output_func("Goodbye!")


def run_data_check(data, output_func=print):
    """Run integrity checks, print the report and return an exit code."""
    issues = check_data_integrity(data)
    output_func(format_integrity_report(issues))
    return 1 if any(severity == "ERROR" for severity, _ in issues) else 0


def parse_preferred_lines(value):
    """Convert the --line_preference value into a list of line names."""
    if not value:
        return []
    return [part.strip() for part in re.split(r"[,\uff0c]", value) if part.strip()]


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except DataLoadError as exc:
        print(f"Error: {exc}")
        return 1

    if args.check_data:
        return run_data_check(data)

    try:
        network = SubwayNetwork(data)
    except DataLoadError as exc:
        print(f"Error: {exc}")
        return 1

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=parse_preferred_lines(args.line_preference),
        )
    except ValueError as exc:
        parser.error(str(exc))

    run_query_loop(network, config, args.format, args.output_file)
    return 0
