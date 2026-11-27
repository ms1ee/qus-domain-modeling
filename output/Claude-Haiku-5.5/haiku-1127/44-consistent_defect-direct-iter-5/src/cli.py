"""Command-line interface for the Beijing Subway fare calculator."""

import argparse
import json
import re
import sys

from data_check import has_errors, run_integrity_check
from data_loader import load_subway_data
from network import StationNotFoundError, SubwayNetwork
from pathfinding import (MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig,
                         PathNotFoundError)
from route_report import build_summary, format_text, query_route, to_json_dict

# Accepted separators between starting and ending station (comma, semicolon).
_SEPARATOR_RE = re.compile(r"[;,\uFF0C\uFF1B]")
_QUIT_WORDS = ("quit", "exit", "q")
_RESULT_SEPARATOR = "\n" + "-" * 50 + "\n"


class InputFormatError(Exception):
    """Raised when the query string does not follow the expected format."""


class QueryError(Exception):
    """Raised for user-facing query problems (unknown stations, etc.)."""


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="file to which query results are exported")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1' (comma separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")
    return args


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two station names."""
    parts = [p.strip() for p in _SEPARATOR_RE.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0], parts[1]


def parse_preferences(text):
    """Turn the --line_preference argument into a list of line names."""
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _resolve(network, name, role, notices):
    """Resolve a station name, recording a notice when a fuzzy match was used."""
    try:
        official, exact = network.resolve_station(name)
    except StationNotFoundError:
        raise QueryError(
            f"{role} station '{name}' does not exist, please check the station name")
    if not exact:
        notices.append(f"Note: {role.lower()} station '{name}' matched to nearest station "
                       f"'{official}'")
    return official


class QuerySession:
    """Holds the state of an interactive session and processes queries."""

    def __init__(self, network, config, output_format="text", output_file=None):
        self.network = network
        self.config = config
        self.output_format = output_format
        self.output_file = output_file
        self._text_records = []
        self._json_records = []

    def run_query(self, text):
        """Process one query string and print/export the result."""
        start_name, end_name = parse_query(text)
        notices = []
        start = _resolve(self.network, start_name, "Starting", notices)
        end = _resolve(self.network, end_name, "Ending", notices)
        if start == end:
            raise QueryError("Starting station cannot be the same as the ending station")

        result = query_route(self.network, start, end, self.config)
        for notice in notices:
            print(notice)

        if self.output_format == "json":
            payload = to_json_dict(result)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            self._json_records.append(payload)
            record_for_file = payload
        else:
            rendered = format_text(result)
            print(rendered)
            self._text_records.append(rendered)
            record_for_file = None

        summary = build_summary(result)
        print(f"Summary: {summary['distance_m']} m, {summary['transfer_count']} transfer(s), "
              f"about {summary['estimated_time_min']} min")
        print(f"Fare: {result.fare} yuan")

        if self.output_file:
            self._export(record_for_file)

    def _export(self, _unused=None):
        """Write all results of this session to the output file."""
        try:
            with open(self.output_file, "w", encoding="utf-8") as handle:
                if self.output_format == "json":
                    json.dump(self._json_records, handle, ensure_ascii=False, indent=2)
                else:
                    handle.write(_RESULT_SEPARATOR.join(self._text_records))
                    handle.write("\n")
            print(f"Result exported to {self.output_file}")
        except OSError as exc:
            print(f"Error: could not write output file: {exc}")


def interactive_loop(session, input_func=input):
    """Run continuous query cycles until the user quits."""
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station'.")
    print("Type 'help' for usage, 'quit' to exit.")
    while True:
        try:
            line = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in _QUIT_WORDS:
            break
        if lowered == "help":
            print("Usage: enter 'Starting Station; Ending Station' (comma also accepted).")
            print("Example: Station A; Station B")
            continue
        try:
            session.run_query(text)
        except InputFormatError as exc:
            print(f"Error: {exc}")
        except QueryError as exc:
            print(f"Error: {exc}")
        except PathNotFoundError as exc:
            print(f"Path error: {exc}")
        except ValueError as exc:
            print(f"Error: {exc}")
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Unexpected error while processing query: {exc}")


def main(argv=None) -> int:
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data()
        network = SubwayNetwork(data)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        issues = run_integrity_check(network)
        for level, message in issues:
            print(f"[{level}] {message}")
        return 1 if has_errors(issues) else 0

    preferred = parse_preferences(args.line_preference)
    known_lines = set(network.line_names())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not a known subway line")

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2

    session = QuerySession(network, config, args.format, args.output_file)
    interactive_loop(session)
    return 0
