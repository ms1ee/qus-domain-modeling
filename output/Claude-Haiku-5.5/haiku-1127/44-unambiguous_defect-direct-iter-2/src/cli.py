"""Command-line interface for the Beijing Subway fare calculation system.

Provides argument parsing, input validation, interactive continuous querying,
result export and error handling.
"""

import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import NetworkError, SubwayNetwork, check_data_integrity
from path_report import build_path_report, format_json_report, format_text_report
from pathfinding import (
    DEFAULT_MODE,
    VALID_MODES,
    PathfindingConfig,
    PathNotFoundError,
    find_route,
)

INPUT_FORMAT_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format"
)
QUIT_WORDS = ("quit", "exit", "q")
SEPARATOR_PATTERN = re.compile(r"[;；,，]")
RESULT_DIVIDER = "-" * 60

HELP_TEXT = """Commands:
  <Starting Station>; <Ending Station>   query the route and fare
  mode <shortest_distance|least_transfer|comprehensive>
                                         change the path query mode
  transfers <N|none>                     set the maximum number of transfers
  help                                   show this help
  quit                                   leave the program
Separators accepted between stations: ';' ',' (full-width forms too)."""


class QueryError(Exception):
    """A user-facing error raised while handling a query or command."""


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra-based)."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="append query results to this file",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format: text (console style) or json (structured data)",
    )
    parser.add_argument(
        "--mode",
        choices=list(VALID_MODES),
        default=DEFAULT_MODE,
        help="path query mode",
    )
    parser.add_argument(
        "--max_transfers",
        type=int,
        default=None,
        help="maximum number of allowed transfers",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="preferred line(s), e.g. 'Line 1' (comma-separated for several)",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="run the data integrity check and exit",
    )
    return parser


def parse_query(text):
    """Split a 'Starting Station; Ending Station' input into two raw names."""
    parts = [part.strip() for part in SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise QueryError(INPUT_FORMAT_MESSAGE)
    return parts[0], parts[1]


def resolve_station(network, raw_name, role):
    """Standardize a station name and verify that it exists."""
    canonical = network.standardize_station(raw_name)
    if canonical is None:
        raise QueryError(
            f"{role} station '{raw_name}' does not exist, please check the station name"
        )
    return canonical


def parse_line_preference(text, network):
    """Validate a comma-separated line preference string and return canonical names."""
    if not text:
        return []
    result = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        canonical = network.standardize_line(item)
        if canonical is None:
            raise QueryError(f"Unknown line '{item}', please check the line name")
        if canonical not in result:
            result.append(canonical)
    return result


class QuerySession:
    """Holds the state of an interactive session and processes user input."""

    def __init__(self, network, config, output_format="text", output_file=None):
        self.network = network
        self.config = config
        self.output_format = output_format
        self.output_file = output_file

    # ----- query processing -------------------------------------------------

    def run_query(self, text):
        """Validate a query, compute the route and return the formatted result."""
        start_raw, end_raw = parse_query(text)
        start = resolve_station(self.network, start_raw, "Starting")
        end = resolve_station(self.network, end_raw, "Ending")
        if start == end:
            raise QueryError("Starting station cannot be the same as the ending station")

        try:
            route = find_route(
                self.network.graph,
                self.network.number_of(start),
                self.network.number_of(end),
                self.config,
            )
        except PathNotFoundError as exc:
            raise QueryError(
                f"No route found from '{start}' to '{end}' under the current settings: {exc}"
            ) from exc
        except (ValueError, KeyError, NetworkError) as exc:
            raise QueryError(f"Path calculation failed: {exc}") from exc

        query = {
            "start": start,
            "end": end,
            "mode": self.config.mode,
            "max_transfers": self.config.max_transfers,
            "line_preference": list(self.config.preferred_lines),
        }
        try:
            report = build_path_report(self.network, route, query)
        except (ValueError, TypeError) as exc:
            raise QueryError(f"Fare calculation failed: {exc}") from exc

        if self.output_format == "json":
            return format_json_report(report)
        return format_text_report(report)

    def export(self, result):
        """Append a query result to the output file, if one was configured."""
        if not self.output_file:
            return
        try:
            with open(self.output_file, "a", encoding="utf-8") as handle:
                handle.write(result)
                handle.write("\n")
                if self.output_format == "text":
                    handle.write(RESULT_DIVIDER + "\n")
        except OSError as exc:
            print(
                f"Warning: could not write to '{self.output_file}': {exc}",
                file=sys.stderr,
            )

    # ----- session commands -------------------------------------------------

    def set_mode(self, mode):
        """Change the query mode for subsequent queries."""
        if mode not in VALID_MODES:
            raise QueryError(
                f"Unknown mode '{mode}', valid modes: {', '.join(VALID_MODES)}"
            )
        self.config = PathfindingConfig(
            mode, self.config.max_transfers, self.config.preferred_lines
        )

    def set_max_transfers(self, value):
        """Change the maximum transfer limit for subsequent queries."""
        if value.lower() == "none":
            limit = None
        else:
            try:
                limit = int(value)
            except ValueError as exc:
                raise QueryError("transfers expects a non-negative integer or 'none'") from exc
            if limit < 0:
                raise QueryError("transfers expects a non-negative integer or 'none'")
        self.config = PathfindingConfig(self.config.mode, limit, self.config.preferred_lines)

    def handle(self, raw):
        """Process one line of user input. Returns False when the session should end."""
        text = raw.strip()
        if not text:
            return True
        lowered = text.lower()
        if lowered in QUIT_WORDS:
            return False
        if lowered in ("help", "?"):
            print(HELP_TEXT)
            return True

        words = lowered.split()
        if words[0] == "mode" and SEPARATOR_PATTERN.search(text) is None:
            if len(words) != 2:
                print("Usage: mode <shortest_distance|least_transfer|comprehensive>")
                return True
            try:
                self.set_mode(words[1])
                print(f"Query mode set to '{self.config.mode}'.")
            except QueryError as exc:
                print(f"Error: {exc}")
            return True

        if words[0] == "transfers" and SEPARATOR_PATTERN.search(text) is None:
            if len(words) != 2:
                print("Usage: transfers <N|none>")
                return True
            try:
                self.set_max_transfers(words[1])
                limit = self.config.max_transfers
                print(f"Maximum transfers set to {'unlimited' if limit is None else limit}.")
            except QueryError as exc:
                print(f"Error: {exc}")
            return True

        try:
            result = self.run_query(text)
        except QueryError as exc:
            print(f"Error: {exc}")
            return True
        print(result)
        self.export(result)
        return True


def main(argv=None):
    """Run the CLI. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        integrity = check_data_integrity(data)
        print(integrity.format())
        return 0 if integrity.ok else 1

    try:
        network = SubwayNetwork(data)
    except NetworkError as exc:
        print(f"Error: failed to build the subway network: {exc}", file=sys.stderr)
        return 1

    try:
        preferred = parse_line_preference(args.line_preference, network)
        config = PathfindingConfig(args.mode, args.max_transfers, preferred)
    except (QueryError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    session = QuerySession(network, config, args.format, args.output_file)

    print("Beijing Subway fare calculation system")
    print(f"Mode: {config.mode}; max transfers: "
          f"{'unlimited' if config.max_transfers is None else config.max_transfers}; "
          f"line preference: {', '.join(preferred) if preferred else 'none'}")
    print("Enter 'Starting Station; Ending Station' (type 'help' for commands, 'quit' to exit).")

    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not session.handle(raw):
            break
    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
