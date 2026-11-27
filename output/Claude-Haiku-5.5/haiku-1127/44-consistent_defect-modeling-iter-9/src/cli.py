"""Command-line interface: argument parsing, query input validation and continuous querying."""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from integrity import DataIntegrityChecker
from models import (
    DataError,
    InputFormatError,
    LogicalValidationError,
    StationNotFoundError,
    SubwayError,
)
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig
from report import format_json, format_text, write_report
from route_planner import plan_route

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
# Accepts ';' or ',' (ASCII and full-width variants) as the separator.
QUERY_SEPARATOR_PATTERN = re.compile(r"[;,\uff1b\uff0c]")
EXIT_COMMANDS = ("quit", "exit", "q")


def build_arg_parser():
    """Create the argparse parser for the program."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation and route query system.",
    )
    parser.add_argument("--output_file", default=None,
                        help="write each query result to this file (overwrites previous result)")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default="comprehensive",
                        help="path query mode (default: comprehensive)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help='preferred line name, e.g. "Line 1"')
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser


def parse_args(argv=None):
    """Parse and validate command-line arguments."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def parse_query(text):
    """Split a query 'Starting Station; Ending Station' into two raw station names.

    Raises:
        InputFormatError: if the text does not contain exactly one separator
            or either side is empty.
    """
    raw = (text or "").strip()
    if not raw:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    parts = QUERY_SEPARATOR_PATTERN.split(raw)
    if len(parts) != 2:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return start, end


def _resolve_input(network, raw_name, label, notices):
    """Resolve a user station name, recording a notice when it is fuzzily matched."""
    try:
        official = network.resolve_station(raw_name)
    except StationNotFoundError:
        raise StationNotFoundError(
            f"{label} station '{raw_name}' does not exist, please check the station name"
        ) from None
    if official != raw_name:
        notices.append(f"Note: '{raw_name}' was matched to the nearest station '{official}'")
    return official


def run_query(network, query_text, args):
    """Execute one query and return (route, rendered_text, notices).

    Raises:
        SubwayError subclasses for input, station, logic, path, and fare errors.
    """
    notices = []
    start_raw, end_raw = parse_query(query_text)
    start = _resolve_input(network, start_raw, "Starting", notices)
    end = _resolve_input(network, end_raw, "Ending", notices)
    if start == end:
        raise LogicalValidationError("Starting station cannot be the same as the ending station")

    preferred = []
    if args.line_preference:
        if args.line_preference in network.lines:
            preferred = [args.line_preference]
        else:
            notices.append(f"Note: line preference '{args.line_preference}' is unknown and was ignored")

    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    route = plan_route(network, start, end, config)
    rendered = format_json(route) if args.format == "json" else format_text(route)
    return route, rendered, notices


def run_interactive(network, args, input_func=input, output=print):
    """Continuously read and answer queries until the user quits or input ends."""
    output("Beijing Subway fare query system.")
    output("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
    while True:
        try:
            line = input_func("Query> ")
        except EOFError:
            output("")
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            _, rendered, notices = run_query(network, text, args)
        except SubwayError as exc:
            output(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never crash the query loop
            output(f"Unexpected error while processing the query: {exc}")
            continue

        for notice in notices:
            output(notice)
        output(rendered)
        if args.output_file:
            try:
                saved = write_report(rendered, args.output_file)
                output(f"Result written to {saved}")
            except OSError as exc:
                output(f"Error: could not write output file: {exc}")


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data)
    except (OSError, ValueError, DataError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        checker = DataIntegrityChecker()
        passed = checker.check(network)
        for message in checker.messages:
            print(message)
        print("Data integrity check PASSED" if passed else "Data integrity check FAILED")
        return 0 if passed else 1

    try:
        run_interactive(network, args)
    except KeyboardInterrupt:
        print("\nExiting.")
    return 0
