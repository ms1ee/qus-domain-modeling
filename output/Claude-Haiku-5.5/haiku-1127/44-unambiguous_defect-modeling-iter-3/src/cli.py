"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import json
import re
import sys

from data_manager import DataManager
from models import (
    InputError,
    Query,
    Report,
    StationNotFoundError,
    SubwayError,
)
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    PathfindingConfig,
    VALID_MODES,
    find_route,
)
from fare_calculator import Sum_money
from reporter import build_summary, make_report

# Accepted separators between starting and ending station.
SEPARATOR_PATTERN = re.compile(r"\s*[;,，；]\s*")
EXIT_COMMANDS = {"quit", "exit", "q"}
REPORT_DIVIDER = "\n" + "=" * 60 + "\n"

HELP_TEXT = (
    "Enter a query in the format 'Starting Station; Ending Station'.\n"
    "Commands: help, quit"
)


def _non_negative_int(text):
    """argparse type for non-negative integers."""
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return value


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser.parse_args(argv)


class SubwayCLI:
    """Interactive query session on top of a DataManager."""

    def __init__(self, options, data_manager, input_func=input, output=None):
        self.options = options
        self.data_manager = data_manager
        self._input = input_func
        self._out = output or sys.stdout
        self.reports = []

    def _print(self, text=""):
        print(text, file=self._out)

    # -- input handling -----------------------------------------------------

    @staticmethod
    def parse_query_text(text):
        """Split 'Starting Station; Ending Station' into (start_text, end_text)."""
        stripped = (text or "").strip()
        if not stripped:
            raise InputError("Input is empty, please use 'Starting Station; Ending Station' format")
        parts = SEPARATOR_PATTERN.split(stripped)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise InputError("Input format incorrect, please use 'Starting Station; Ending Station' format")
        return parts[0].strip(), parts[1].strip()

    def resolve_stations(self, start_text, end_text):
        """Validate and standardize both station names."""
        start = self.data_manager.resolve_station(start_text)
        if start is None:
            raise StationNotFoundError(
                f"Starting station '{start_text}' does not exist, please check the station name")
        end = self.data_manager.resolve_station(end_text)
        if end is None:
            raise StationNotFoundError(
                f"Ending station '{end_text}' does not exist, please check the station name")
        if start == end:
            raise InputError("Starting station cannot be the same as the ending station")
        return start, end

    # -- query processing ---------------------------------------------------

    def run_query(self, text):
        """Process one query string and return the rendered Report."""
        start_text, end_text = self.parse_query_text(text)
        start, end = self.resolve_stations(start_text, end_text)

        opts = self.options
        query = Query(
            start_station=start,
            end_station=end,
            mode=opts.mode,
            max_transfers=opts.max_transfers,
            line_preference=opts.line_preference,
        )
        preferred = [opts.line_preference] if opts.line_preference else []
        config = PathfindingConfig(mode=opts.mode, max_transfers=opts.max_transfers,
                                   preferred_lines=preferred)

        try:
            path = find_route(self.data_manager.graph, start, end, config)
        except SubwayError:
            raise
        except Exception as exc:
            raise SubwayError(f"Path calculation failed: {exc}") from exc

        try:
            fare = Sum_money(path.total_distance_m)
            summary = build_summary(path, fare)
        except SubwayError:
            raise
        except Exception as exc:
            raise SubwayError(f"Fare calculation failed: {exc}") from exc

        report = make_report(query, path, summary, opts.format)
        self.reports.append(report)
        return report

    def export_reports(self):
        """Write all reports of this session to the output file, if configured."""
        path = self.options.output_file
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                if self.options.format == "json":
                    payload = [json.loads(r.content) for r in self.reports]
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                else:
                    handle.write(REPORT_DIVIDER.join(r.content for r in self.reports))
                    handle.write("\n")
        except OSError as exc:
            raise SubwayError(f"Could not write output file '{path}': {exc}") from exc

    # -- modes of operation -------------------------------------------------

    def run_interactive(self):
        """Run the continuous query loop until the user quits."""
        self._print("Beijing Subway fare calculator")
        self._print(HELP_TEXT)
        while True:
            try:
                line = self._input("> ")
            except EOFError:
                self._print()
                break
            except KeyboardInterrupt:
                self._print()
                break

            command = line.strip()
            if not command:
                continue
            lowered = command.lower()
            if lowered in EXIT_COMMANDS:
                break
            if lowered == "help":
                self._print(HELP_TEXT)
                continue

            try:
                report = self.run_query(command)
                self._print(report.content)
                self.export_reports()
            except SubwayError as exc:
                self._print(f"Error: {exc}")
            except Exception as exc:  # defensive: never crash the session
                self._print(f"Unexpected error: {exc}")
        return 0

    def check_data(self):
        """Run the data integrity check and print the results. Returns an exit code."""
        passed, issues = self.data_manager.check_integrity()
        if issues:
            for issue in issues:
                self._print(issue)
        else:
            self._print("No issues found.")
        self._print("Data integrity check PASSED" if passed else "Data integrity check FAILED")
        return 0 if passed else 1


def main(argv=None):
    """CLI entry point. Returns the process exit code."""
    options = parse_args(argv)
    try:
        data_manager = DataManager()
    except SubwayError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    cli = SubwayCLI(options, data_manager)
    if options.check_data:
        return cli.check_data()

    if options.line_preference:
        canonical = data_manager.canonical_line(options.line_preference)
        if canonical is None:
            print(f"Error: line preference '{options.line_preference}' does not exist", file=sys.stderr)
            return 2
        options.line_preference = canonical

    return cli.run_interactive()
