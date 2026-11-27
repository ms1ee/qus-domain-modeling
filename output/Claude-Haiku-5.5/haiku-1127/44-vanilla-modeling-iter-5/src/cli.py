"""Command-line interface: argument parsing, input validation and query loop."""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Optional

from data_loader import DATA_FILE_PATH, load_subway_data
from data_management import check_data_integrity
from models import SubwayNetwork
from pathfinding import PATH_MODES
from report import build_report, route_to_dict
from route_service import FareCalculationError, PathNotFoundError, plan_route

FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")


class QueryInputError(Exception):
    """Raised when a user query fails validation."""


@dataclass
class CommandLineOptions:
    """Options given on the command line.

    Attributes:
        output_file: optional export file path.
        format: "text" or "json".
        mode: path query mode.
        max_transfers: optional maximum transfer count.
        line_preference: optional canonical preferred line name.
        check_data: run the integrity check and exit.
    """

    output_file: Optional[str] = None
    format: str = "text"
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None
    check_data: bool = False


class ResultExporter:
    """Exports query results to a file.

    Text results are appended to the file. JSON results are kept as a list
    for the session and the file is rewritten so it always holds valid JSON.
    """

    def __init__(self, path, fmt):
        self.path = path
        self.fmt = fmt
        self._json_results = []

    def export(self, route, report):
        """Write one query result to the export file."""
        if self.fmt == "json":
            self._json_results.append(route_to_dict(route))
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(self._json_results, handle, ensure_ascii=False, indent=2)
        else:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(report.content + "\n\n")


def parse_args(argv=None):
    """Parse command-line arguments (exits with status 2 on invalid arguments)."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(PATH_MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must not be negative")
    return args


def parse_query_text(text):
    """Split 'Starting Station; Ending Station' into two raw names.

    Raises:
        QueryInputError: If the format is wrong.
    """
    parts = text.replace("\uff1b", ";").split(";")
    if len(parts) != 2:
        raise QueryInputError(FORMAT_ERROR_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryInputError(FORMAT_ERROR_MESSAGE)
    return start, end


def validate_query(text, network):
    """Validate a query string and return canonical (start, end) station names.

    Raises:
        QueryInputError: With a user-facing message on any validation failure.
    """
    start_raw, end_raw = parse_query_text(text)
    start = network.find_station(start_raw)
    if start is None:
        raise QueryInputError(
            f"Starting station '{start_raw}' does not exist, please check the station name"
        )
    end = network.find_station(end_raw)
    if end is None:
        raise QueryInputError(
            f"Ending station '{end_raw}' does not exist, please check the station name"
        )
    if start == end:
        raise QueryInputError("Starting station cannot be the same as the ending station")
    return start, end


def run_query_loop(network, options, input_func=input, stdout=None, stderr=None):
    """Repeatedly read queries, compute routes and print reports until quit/EOF.

    Returns:
        int: exit status (0).
    """
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    exporter = ResultExporter(options.output_file, options.format) if options.output_file else None

    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' "
          "(or 'quit' to exit).", file=out)
    while True:
        try:
            raw = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            print(file=out)
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            start, end = validate_query(text, network)
        except QueryInputError as exc:
            print(f"Error: {exc}", file=err)
            continue

        try:
            route = plan_route(
                network, start, end,
                mode=options.mode,
                max_transfers=options.max_transfers,
                line_preference=options.line_preference,
            )
        except PathNotFoundError as exc:
            print(f"Error: {exc}", file=err)
            continue
        except FareCalculationError as exc:
            print(f"Fare calculation error: {exc}", file=err)
            continue
        except (ValueError, KeyError) as exc:
            print(f"Path calculation error: {exc}", file=err)
            continue
        except Exception as exc:  # last-resort guard so the session keeps running
            print(f"Unexpected error while calculating the route: {exc}", file=err)
            continue

        try:
            report = build_report(route, options.format)
        except ValueError as exc:
            print(f"Report error: {exc}", file=err)
            continue

        print(report.content, file=out)
        print(file=out)

        if exporter is not None:
            try:
                exporter.export(route, report)
                print(f"Result exported to {options.output_file}", file=out)
            except OSError as exc:
                print(f"Export error: could not write '{options.output_file}': {exc}", file=err)
    return 0


def main(argv=None, input_func=input, stdout=None, stderr=None):
    """CLI entry point. Returns the process exit status."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    args = parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork.from_data(data, DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=err)
        return 1

    if args.check_data:
        report = check_data_integrity(network)
        if report.passed:
            print("Data integrity check: PASSED", file=out)
        else:
            print("Data integrity check: FAILED", file=out)
            for issue in report.issues:
                print(f"  - {issue}", file=out)
        return 0 if report.passed else 1

    line_preference = None
    if args.line_preference is not None:
        line_preference = network.find_line(args.line_preference)
        if line_preference is None:
            print(f"Error: line '{args.line_preference}' does not exist. "
                  f"Available lines: {', '.join(network.line_names())}", file=err)
            return 2

    options = CommandLineOptions(
        output_file=args.output_file,
        format=args.format,
        mode=args.mode,
        max_transfers=args.max_transfers,
        line_preference=line_preference,
        check_data=False,
    )
    return run_query_loop(network, options, input_func=input_func, stdout=out, stderr=err)
