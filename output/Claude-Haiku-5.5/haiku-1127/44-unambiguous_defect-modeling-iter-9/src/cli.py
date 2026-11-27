"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys

from data_loader import DataLoadError
from data_manager import DataManager
from fare_calculator import FareError
from integrity_checker import DataIntegrityChecker
from pathfinding import (
    VALID_MODES,
    MODE_SHORTEST_DISTANCE,
    PathfindingConfig,
    PathfindingError,
    compute_route,
)
from reporter import FORMAT_TEXT, SUPPORTED_FORMATS, ReportError, build_report, write_report
from validator import InputValidator, QueryError

QUIT_COMMANDS = ("quit", "exit", "q")


def build_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (command line)."
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file (overwritten on each query)")
    parser.add_argument("--format", choices=list(SUPPORTED_FORMATS), default=FORMAT_TEXT,
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' (comma-separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


class CLISession:
    """Interactive session that processes queries until the user quits."""

    def __init__(self, network, config, output_format=FORMAT_TEXT, output_file=None):
        self.network = network
        self.config = config
        self.output_format = output_format
        self.output_file = output_file
        self.validator = InputValidator(network)
        self.query_count = 0
        self.is_continuous = True

    def process_query(self, text):
        """Handle one query line. Returns True if a route was printed."""
        try:
            start, end = self.validator.validate(text)
        except QueryError as exc:
            print(f"Error: {exc}")
            return False

        try:
            route = compute_route(self.network, start, end, self.config)
        except PathfindingError as exc:
            print(f"Path error: {exc}")
            return False
        except Exception as exc:  # defensive: keep the session alive
            print(f"Unexpected error during path calculation: {exc}")
            return False

        try:
            report = build_report(self.output_format, start, end, route, self.config)
        except FareError as exc:
            print(f"Fare calculation error: {exc}")
            return False
        except ReportError as exc:
            print(f"Report error: {exc}")
            return False
        except Exception as exc:  # defensive
            print(f"Unexpected error while generating the report: {exc}")
            return False

        print(report.content)
        if self.output_file:
            try:
                path = write_report(report, self.output_file)
                print(f"Results exported to {path}")
            except ReportError as exc:
                print(f"Export error: {exc}")
        self.query_count += 1
        return True

    def run(self):
        """Run the interactive loop. Returns the process exit code."""
        print("Beijing Subway fare calculator")
        print("Enter a query as 'Starting Station; Ending Station' (or 'quit' to exit).")
        while self.is_continuous:
            try:
                line = input("Query> ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break
            text = line.strip()
            if not text:
                continue
            if text.lower() in QUIT_COMMANDS:
                break
            self.process_query(text)
        print(f"Session ended. Queries answered: {self.query_count}")
        return 0


def main(argv=None):
    """Entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        manager = DataManager()
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        checker = DataIntegrityChecker()
        issues = checker.check(manager)
        print(checker.format_report(issues))
        return 0 if not issues else 1

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    preferred = []
    if args.line_preference:
        for raw in args.line_preference.split(","):
            raw = raw.strip()
            if not raw:
                continue
            canonical = manager.network.canonical_line(raw)
            if canonical is None:
                parser.error(f"Unknown line preference '{raw}'")
            preferred.append(canonical)

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        parser.error(str(exc))

    session = CLISession(manager.network, config, args.format, args.output_file)
    return session.run()
