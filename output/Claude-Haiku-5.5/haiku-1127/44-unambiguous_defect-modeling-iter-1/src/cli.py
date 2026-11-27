"""Command-line interface: argument parsing, input validation and the
interactive continuous-query loop."""

from __future__ import annotations

import argparse
import re
import sys

import report
from data_manager import DataManager
from errors import InputFormatError, SubwayError, ValidationError
from pathfinding import DEFAULT_MAX_TRANSFERS, MODE_COMPREHENSIVE, VALID_MODES, PathfindingConfig
from route_planner import RouteResult, plan_route

QUERY_SEPARATOR_PATTERN = re.compile(r"[;；,，]")
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")
HELP_COMMANDS = ("help", "?")
HELP_TEXT = """Commands:
  <Starting Station>; <Ending Station>   query the optimal route and fare
  help                                   show this help
  quit / exit / q                        leave the program
Separators accepted: ';' or ',' (full-width forms also accepted)."""


def parse_query(text: str) -> tuple[str, str]:
    """Split a 'Start; End' query into its two raw station names.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty parts.
    """
    parts = QUERY_SEPARATOR_PATTERN.split(text)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def parse_line_preference(text: str | None) -> list[str]:
    """Split a comma-separated line preference argument into line names."""
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="write query results to this file (rewritten after each query)")
    parser.add_argument("--format", choices=report.VALID_FORMATS, default=report.FORMAT_TEXT,
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_COMPREHENSIVE,
                        help="path query mode (default: comprehensive)")
    parser.add_argument("--max_transfers", type=int, default=DEFAULT_MAX_TRANSFERS,
                        help=f"maximum number of transfers allowed (default: {DEFAULT_MAX_TRANSFERS})")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


class QuerySession:
    """Interactive session that answers queries until the user quits.

    Attributes:
        manager: Data manager holding the network.
        config: Path query configuration applied to every query.
        output_format: "text" or "json".
        output_file: Optional file that receives all results of the session.
        results: Route results computed so far in this session.
    """

    def __init__(
        self,
        manager: DataManager,
        config: PathfindingConfig,
        output_format: str = report.FORMAT_TEXT,
        output_file: str | None = None,
    ) -> None:
        self.manager = manager
        self.config = config
        self.output_format = output_format
        self.output_file = output_file
        self.results: list[RouteResult] = []

    def handle_query(self, text: str) -> RouteResult:
        """Validate a query string and compute its route.

        Raises:
            InputFormatError, StationNotFoundError, ValidationError,
            PathNotFoundError, FareError: For any invalid input or failed computation.
        """
        origin_raw, destination_raw = parse_query(text)
        origin = self.manager.resolve_station(origin_raw, "Starting")
        destination = self.manager.resolve_station(destination_raw, "Ending")
        if origin == destination:
            raise ValidationError("Starting station cannot be the same as the ending station")
        return plan_route(self.manager.graph, origin, destination, self.config)

    def _save(self) -> None:
        """Rewrite the output file with all results of this session."""
        if not self.output_file:
            return
        try:
            content = report.render_many(self.results, self.output_format)
            report.write_report(content, self.output_file)
        except (OSError, ValueError) as exc:
            print(f"Error: could not write output file '{self.output_file}': {exc}")

    def run(self, input_func=input) -> int:
        """Run the read-evaluate-print loop until the user quits.

        Returns:
            Process exit code (0 on normal exit).
        """
        print("Beijing Subway Fare Calculator. Type 'help' for usage, 'quit' to exit.")
        while True:
            try:
                raw = input_func("Query> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            text = raw.strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in EXIT_COMMANDS:
                break
            if lowered in HELP_COMMANDS:
                print(HELP_TEXT)
                continue
            try:
                result = self.handle_query(text)
            except SubwayError as exc:
                print(f"Error: {exc}")
                continue
            except (ValueError, KeyError, IndexError) as exc:
                print(f"Error: unexpected failure during path calculation: {exc}")
                continue

            try:
                print(report.render(result, self.output_format))
            except ValueError as exc:
                print(f"Error: could not render result: {exc}")
                continue
            print()
            self.results.append(result)
            self._save()
        return 0


def run_data_check(manager: DataManager) -> int:
    """Print the data integrity report.

    Returns:
        0 if no errors were found, 1 otherwise.
    """
    errors, warnings = manager.check_integrity()
    print("Data integrity check")
    print(f"Stations: {manager.graph.station_count()}, connections: {manager.graph.edge_count()}")
    if not errors and not warnings:
        print("No issues found.")
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")
    print("Result: PASSED" if not errors else f"Result: FAILED ({len(errors)} error(s))")
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point for the command-line program.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")

    manager = DataManager()
    try:
        manager.load()
    except SubwayError as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(manager)

    preferred = parse_line_preference(args.line_preference)
    known_lines = set(manager.graph.lines())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not in the dataset; the preference has little effect")

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    session = QuerySession(manager, config, args.format, args.output_file)
    return session.run()
