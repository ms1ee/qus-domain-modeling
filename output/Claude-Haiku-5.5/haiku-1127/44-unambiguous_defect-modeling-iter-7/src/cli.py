"""
Command-line interface for the Beijing Subway fare calculation system.

Usage examples:
  python src/main.py
  python src/main.py --mode least_transfer --format json
  python src/main.py --output_file result.txt --line_preference "Line 1"
  python src/main.py --check_data
"""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH
from data_manager import DataManager
from pathfinding import VALID_MODES
from report import format_json, format_text, write_report
from route_service import RoutingError, find_route

FORMAT_ERROR_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format")
EXIT_COMMANDS = ("quit", "exit", "q")
HELP_COMMANDS = ("help", "?")
HELP_TEXT = (
    "Enter a query in the form 'Starting Station; Ending Station'.\n"
    "Accepted separators: ';' (or a comma).\n"
    "Type 'quit' to exit."
)

_SEPARATOR_PATTERN = re.compile(r"[;\uff1b,\uff0c]")


class QueryFormatError(Exception):
    """Raised when a query string does not follow the expected format."""


def build_arg_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="comprehensive",
                        help="path query mode (default: comprehensive)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_query(text):
    """
    Split a query string into (starting station, ending station).

    Raises:
        QueryFormatError: If the text is not of the form 'A; B'.
    """
    parts = _SEPARATOR_PATTERN.split(text)
    if len(parts) != 2:
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    return start, end


class SubwayCLI:
    """
    Interactive command-line application.

    Attributes:
        data_manager: DataManager providing the network data.
        input_func: Function used to read user input (default: input).
        args: Parsed command-line arguments.
    """

    def __init__(self, data_manager=None, input_func=input):
        self.data_manager = data_manager or DataManager(DATA_FILE_PATH)
        self.input_func = input_func
        self.args = None
        self._output_started = False

    def run(self, argv=None):
        """
        Run the application.

        Returns:
            int: Process exit code.
        """
        parser = build_arg_parser()
        self.args = parser.parse_args(argv)

        if self.args.max_transfers is not None and self.args.max_transfers < 0:
            print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
            return 2

        try:
            self.data_manager.load()
        except FileNotFoundError:
            print(f"Error: subway data file not found: {self.data_manager.data_path}",
                  file=sys.stderr)
            return 1
        except (OSError, ValueError) as exc:
            print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
            return 1

        if self.args.check_data:
            return self._run_check()

        self._run_interactive()
        return 0

    def _run_check(self):
        """Execute the data integrity check and return an exit code."""
        passed = self.data_manager.run_integrity_check()
        for line in self.data_manager.checker.report_lines():
            print(line)
        return 0 if passed else 1

    def _print_banner(self):
        """Print the welcome banner."""
        print("Beijing Subway Fare Calculation System")
        print(f"Stations loaded: {len(self.data_manager.station_names())}, "
              f"lines: {len(self.data_manager.line_names())}")
        print(HELP_TEXT)

    def _run_interactive(self):
        """Read queries until the user quits or input ends."""
        self._print_banner()
        while True:
            try:
                raw = self.input_func("\nQuery> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            text = (raw or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in EXIT_COMMANDS:
                break
            if lowered in HELP_COMMANDS:
                print(HELP_TEXT)
                continue
            self.process_query(text)
        print("Goodbye!")

    def process_query(self, text):
        """
        Handle one query string: validate, compute, print and optionally export.

        Returns:
            bool: True if the query was answered successfully.
        """
        try:
            start, end = parse_query(text)
            result = find_route(
                self.data_manager, start, end,
                mode=self.args.mode,
                max_transfers=self.args.max_transfers,
                line_preference=self.args.line_preference,
            )
        except QueryFormatError as exc:
            print(f"Error: {exc}")
            return False
        except RoutingError as exc:
            print(f"Error: {exc}")
            return False
        except Exception as exc:  # defensive: unexpected path/fare failures
            print(f"Error: unexpected failure while calculating the route: {exc}")
            return False

        try:
            content = format_json(result) if self.args.format == "json" else format_text(result)
        except Exception as exc:
            print(f"Error: failed to build the report: {exc}")
            return False

        print(content)

        if self.args.output_file:
            try:
                write_report(content, self.args.output_file, append=self._output_started)
                self._output_started = True
                print(f"Result written to {self.args.output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
                return False
        return True


def main(argv=None):
    """Entry point used by src/main.py. Returns the process exit code."""
    return SubwayCLI().run(argv)
