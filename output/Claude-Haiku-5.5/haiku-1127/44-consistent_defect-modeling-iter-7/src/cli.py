"""
Command-line interface for the Beijing Subway fare calculation system.

Supports interactive continuous queries ("Starting Station; Ending Station"),
command-line options (--output_file, --format, --mode, --max_transfers,
--line_preference, --check_data) and layered error handling.
"""

import argparse
import os
import re
import sys

from data_integrity import DataIntegrityChecker
from models import Query
from network import SubwayNetwork, UnknownStationError
from pathfinding import (
    MODE_COMPREHENSIVE,
    VALID_MODES,
    NoPathError,
    PathfindingConfig,
    ShortestPath,
)
from route_reporter import build_route, build_summary, generate_report


INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")
_SEPARATOR_PATTERN = re.compile(r"\s*[;,；，]\s*")


class QueryError(Exception):
    """Base class for errors raised while answering a query."""


class InputFormatError(QueryError):
    """The input does not follow the 'Starting Station; Ending Station' format."""


class SameStationError(QueryError):
    """Origin and destination are the same station."""


class PathCalculationError(QueryError):
    """No path could be calculated."""


class FareCalculationError(QueryError):
    """The fare or summary could not be calculated."""


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="fmt", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_COMPREHENSIVE,
                        help="path query mode (default: comprehensive)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser.parse_args(argv)


def parse_query_input(text):
    """Split user input into (origin, destination).

    Raises:
        InputFormatError: If the input is not two non-empty names.
    """
    parts = _SEPARATOR_PATTERN.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def answer_query(network, origin_raw, destination_raw, mode, max_transfers,
                 line_preference, fmt):
    """Answer one passenger query.

    Returns:
        tuple: (Report, list of notice strings)

    Raises:
        UnknownStationError, SameStationError, PathCalculationError, FareCalculationError
    """
    notices = []
    try:
        origin, origin_fuzzy = network.resolve_station(origin_raw)
    except UnknownStationError:
        raise UnknownStationError(origin_raw)
    try:
        destination, dest_fuzzy = network.resolve_station(destination_raw)
    except UnknownStationError:
        raise UnknownStationError(destination_raw)

    if origin_fuzzy:
        notices.append(f"Starting station '{origin_raw}' matched to nearest station '{origin}'")
    if dest_fuzzy:
        notices.append(f"Ending station '{destination_raw}' matched to nearest station '{destination}'")
    if origin == destination:
        raise SameStationError("Starting station cannot be the same as the ending station")

    preferred = []
    if line_preference:
        preferred = [line_preference.strip()]
        if line_preference.strip() not in network.line_names():
            notices.append(f"Line '{line_preference}' is not a known line; preference ignored")

    try:
        config = PathfindingConfig(mode=mode, max_transfers=max_transfers, preferred_lines=preferred)
        source_no = network.station_number(origin)
        target_no = network.station_number(destination)
        path = ShortestPath(network.graph, source_no, config)
        node_numbers, edges = path.path_with_edges(target_no)
        path.get_transfer_count(target_no)
    except NoPathError as exc:
        message = f"No route found from '{origin}' to '{destination}'"
        if max_transfers is not None:
            message += f" within {max_transfers} transfer(s)"
        raise PathCalculationError(message + f" ({exc})")
    except Exception as exc:
        raise PathCalculationError(f"Path calculation failed: {exc}")

    try:
        names = [network.name_of(n) for n in node_numbers]
        route = build_route(names, edges, mode)
        summary = build_summary(route)
    except Exception as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}")

    query = Query(origin=origin, destination=destination, mode=mode,
                  max_transfers=max_transfers, line_preference=line_preference)
    report = generate_report(route, summary, query, fmt)
    return report, notices


def write_output_file(path, content):
    """Append report content to an output file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n\n")


def run_check_data(network, out=print):
    """Run data integrity checks and print the results.

    Returns:
        int: 0 if all checks passed, 1 otherwise.
    """
    checker = DataIntegrityChecker(network.graph, network.number_to_name)
    passed = checker.run()
    for line in checker.report_lines():
        out(line)
    return 0 if passed else 1


def run_interactive(network, args, input_func=input, out=print):
    """Run the continuous query loop until the user quits.

    Returns:
        int: Process exit code (0 on normal exit).
    """
    out("Beijing Subway fare query system. Enter 'Starting Station; Ending Station'.")
    out("Type 'quit' to exit.")
    while True:
        try:
            raw = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            out("")
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            origin_raw, destination_raw = parse_query_input(text)
            report, notices = answer_query(
                network, origin_raw, destination_raw, args.mode,
                args.max_transfers, args.line_preference, args.fmt,
            )
            for notice in notices:
                out("Notice: " + notice)
            out(report.content)
            if args.output_file:
                try:
                    write_output_file(args.output_file, report.content)
                    out(f"Result saved to {args.output_file}")
                except OSError as exc:
                    out(f"Warning: could not write output file: {exc}")
        except InputFormatError as exc:
            out(f"Error: {exc}")
        except UnknownStationError as exc:
            out(f"Error: {exc}")
        except QueryError as exc:
            out(f"Error: {exc}")
        except Exception as exc:  # last-resort guard so the loop keeps running
            out(f"Unexpected error: {exc}")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be non-negative", file=sys.stderr)
        return 2
    try:
        network = SubwayNetwork()
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1
    try:
        if args.check_data:
            return run_check_data(network)
        return run_interactive(network, args)
    except KeyboardInterrupt:
        print()
        return 0
