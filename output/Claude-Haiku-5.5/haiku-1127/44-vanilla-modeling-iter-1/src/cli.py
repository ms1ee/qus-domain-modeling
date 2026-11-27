"""Command-line interface: argument parsing, input validation and query loop."""

import argparse
from typing import Callable

from src import path_report
from src.data_manager import DataManager
from src.network import QueryError, SubwayNetwork
from src.pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig

INPUT_PROMPT = "Enter query as 'Starting Station; Ending Station' (type 'quit' to exit): "
EXIT_COMMANDS = ("quit", "exit", "q")
INPUT_FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class InputError(ValueError):
    """Raised for malformed or invalid user input."""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=path_report.SUPPORTED_FORMATS, default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query(text: str) -> tuple[str, str]:
    """Split 'Starting Station; Ending Station' into its two parts."""
    if text.count(";") != 1:
        raise InputError(INPUT_FORMAT_HINT)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputError(INPUT_FORMAT_HINT)
    return start, end


def validate_query(network: SubwayNetwork, raw_start: str, raw_end: str) -> tuple[str, str]:
    """Standardize station names and apply logical validation."""
    start = network.standardize_station_name(raw_start)
    if start is None:
        raise InputError(f"Starting station '{raw_start}' does not exist, please check the station name")
    end = network.standardize_station_name(raw_end)
    if end is None:
        raise InputError(f"Ending station '{raw_end}' does not exist, please check the station name")
    if start == end:
        raise InputError("Starting station cannot be the same as the ending station")
    return start, end


def run_session(
    network: SubwayNetwork,
    config: PathfindingConfig,
    fmt: str,
    output_file: str = None,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> int:
    """Interactive continuous query loop. Returns the number of successful queries."""
    completed = 0
    while True:
        try:
            raw = read(INPUT_PROMPT)
        except (EOFError, KeyboardInterrupt):
            write("")
            break

        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            raw_start, raw_end = parse_query(text)
            start, end = validate_query(network, raw_start, raw_end)
        except InputError as exc:
            write(f"Error: {exc}")
            continue

        try:
            route = network.query(start, end, config)
        except QueryError as exc:
            write(f"Error: {exc}")
            continue
        except Exception as exc:  # unexpected failure must not end the session
            write(f"Error: unexpected failure while calculating the route: {exc}")
            continue

        try:
            report = path_report.build_report(route, fmt)
        except Exception as exc:
            write(f"Error: failed to render the report: {exc}")
            continue

        write(report.content)
        write("")
        completed += 1

        if output_file:
            try:
                path_report.write_report(report, output_file)
                write(f"Result appended to '{output_file}'")
            except OSError as exc:
                write(f"Error: cannot write output file '{output_file}': {exc}")
    return completed


def main(argv=None) -> int:
    """Program entry point. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    manager = DataManager()
    try:
        network = manager.load_network()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data from '{manager.sourceFile}': {exc}")
        return 1

    if args.check_data:
        issues = manager.check_integrity(network)
        if issues:
            print(f"Data integrity check FAILED with {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        print("Data integrity check passed.")
        return 0

    preferred: list[str] = []
    if args.line_preference:
        official = network.resolve_line(args.line_preference)
        if official is None:
            print(f"Error: line '{args.line_preference}' does not exist. "
                  f"Available lines: {', '.join(network.line_names())}")
            return 2
        preferred = [official]

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    run_session(network, config, args.format, args.output_file)
    return 0
