"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import re
import sys

from data_check import format_check_report, run_integrity_check
from data_loader import DataLoadError
from fare_calculator import Sum_money  # noqa: F401  (fare is computed in path_report)
from network import NetworkError, SubwayNetwork
from pathfinding import (MODE_SHORTEST_DISTANCE, PathfindingConfig,
                         PathNotFoundError, VALID_MODES, compute_route)
from path_report import build_report, format_json, format_text
from station_matcher import InputFormatError, StationMatcher, StationNotFoundError

QUIT_COMMANDS = {"q", "quit", "exit"}
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
# Accepts ';' or ',' (ASCII and full-width) as the separator.
_SEPARATOR_PATTERN = re.compile(r"[;,\uff1b\uff0c]")


def non_negative_int(value):
    """argparse type: parse a non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (interactive CLI).")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="output_format", choices=["text", "json"],
                        default="text", help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="comma-separated preferred lines, e.g. 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw station names.

    Raises:
        InputFormatError: If the input does not contain exactly two non-empty parts.
    """
    parts = _SEPARATOR_PATTERN.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def parse_line_preference(text):
    """Parse a comma-separated line preference string into a list (or None)."""
    if not text:
        return None
    lines = [item.strip() for item in text.split(",") if item.strip()]
    return lines or None


class SubwayQueryCLI:
    """Interactive, continuous query loop.

    Attributes:
        network: SubwayNetwork providing the graph and names.
        config: PathfindingConfig applied to every query.
        output_format: "text" or "json".
        output_file: Optional path where results are appended.
    """

    def __init__(self, network, config, output_format="text", output_file=None,
                 input_func=input, output_func=print):
        self.network = network
        self.config = config
        self.output_format = output_format
        self.output_file = output_file
        self._input = input_func
        self._print = output_func
        self._matcher = StationMatcher(network.station_names())

    def _error(self, message):
        self._print(f"Error: {message}")

    def run(self):
        """Run the query loop until the user quits or input ends."""
        self._print("Beijing Subway Fare Calculation System")
        self._print("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
        while True:
            try:
                text = self._input("Query> ")
            except (EOFError, KeyboardInterrupt):
                self._print("")
                break
            if not text or not text.strip():
                continue
            if text.strip().lower() in QUIT_COMMANDS:
                break
            self.handle_query(text)
        self._print("Goodbye.")
        return 0

    def handle_query(self, text):
        """Process one query string.

        Returns:
            bool: True if a route was computed and reported successfully.
        """
        # Input format validation.
        try:
            raw_start, raw_end = parse_query(text)
        except InputFormatError as exc:
            self._error(str(exc))
            return False

        # Station name standardisation and existence verification.
        try:
            start_match = self._matcher.standardize(raw_start)
        except StationNotFoundError:
            self._error(f"Starting station '{raw_start}' does not exist, please check the station name")
            return False
        except InputFormatError as exc:
            self._error(str(exc))
            return False
        try:
            end_match = self._matcher.standardize(raw_end)
        except StationNotFoundError:
            self._error(f"Ending station '{raw_end}' does not exist, please check the station name")
            return False
        except InputFormatError as exc:
            self._error(str(exc))
            return False

        if not start_match.exact:
            self._print(f"Note: '{raw_start}' matched to nearest station '{start_match.name}'.")
        if not end_match.exact:
            self._print(f"Note: '{raw_end}' matched to nearest station '{end_match.name}'.")

        # Logical validation.
        if start_match.name == end_match.name:
            self._error("Starting station cannot be the same as the ending station")
            return False

        # Path calculation.
        try:
            route = compute_route(
                self.network.graph,
                self.network.number_of(start_match.name),
                self.network.number_of(end_match.name),
                self.config,
            )
        except PathNotFoundError:
            self._error(f"No route found between '{start_match.name}' and '{end_match.name}' "
                        f"under the current constraints (check --max_transfers / --line_preference)")
            return False
        except (ValueError, NetworkError) as exc:
            self._error(f"Path calculation failed: {exc}")
            return False

        # Fare calculation and report generation.
        query = {
            "start": start_match.name,
            "end": end_match.name,
            "mode": self.config.mode,
            "max_transfers": self.config.max_transfers,
            "line_preference": list(self.config.preferred_lines),
        }
        try:
            report = build_report(self.network, route, query)
        except (ValueError, ArithmeticError, NetworkError) as exc:
            self._error(f"Fare calculation failed: {exc}")
            return False

        if self.output_format == "json":
            output = format_json(report, indent=2)
        else:
            output = format_text(report)
        self._print(output)

        if self.output_file:
            self._write_result(report)
        return True

    def _write_result(self, report):
        """Append a query result to the output file."""
        try:
            with open(self.output_file, "a", encoding="utf-8") as handle:
                if self.output_format == "json":
                    handle.write(format_json(report, indent=None) + "\n")
                else:
                    handle.write(format_text(report) + "\n\n")
        except OSError as exc:
            self._error(f"Cannot write output file '{self.output_file}': {exc}")


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork.from_file()
    except (DataLoadError, NetworkError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = run_integrity_check(network.data)
        print(format_check_report(report))
        return 0 if report.ok else 1

    preferred = parse_line_preference(args.line_preference)
    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    if preferred:
        known = set(network.all_lines())
        unknown = [line for line in preferred if line not in known]
        if unknown:
            print(f"Warning: unknown line preference(s): {', '.join(unknown)}")

    cli = SubwayQueryCLI(network, config, output_format=args.output_format,
                         output_file=args.output_file)
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
