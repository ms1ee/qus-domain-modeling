"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import json
import re
import sys

from data_loader import load_subway_data
from data_manager import check_data_integrity
from errors import InvalidInputError, SubwayError
from network import SubwayNetwork
from path_report import export_report, format_json, format_text, route_to_dict
from pathfinding import (
    MODE_SHORTEST,
    VALID_MODES,
    PathfindingConfig,
    find_route,
)

FORMAT_ERROR_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format"
)
# Accepted separators between the starting and ending station.
SEPARATOR_PATTERN = re.compile(r"[;\uff1b,\uff0c]")
QUIT_COMMANDS = {"quit", "exit", "q"}

HELP_TEXT = """Commands:
  <Starting Station>; <Ending Station>   Query a route (',' also accepted as separator)
  mode <shortest_distance|least_transfer|comprehensive>
                                         Change the query mode for later queries
  mode                                   Show the current query mode
  help                                   Show this help
  quit / exit / q                        Leave the program"""


def _non_negative_int(text):
    """argparse type helper for non-negative integers."""
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got '{text}'") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("value must not be negative")
    return value


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="beijing_subway_fare",
        description="Beijing Subway route and fare calculator.",
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    parser.add_argument("--query", default=None,
                        help="run one query 'Starting Station; Ending Station' and exit")
    return parser.parse_args(argv)


def parse_query(text):
    """Split a query string into (starting station, ending station).

    Raises:
        InvalidInputError: If the format is not 'Start; End'.
    """
    if text is None:
        raise InvalidInputError(FORMAT_ERROR_MESSAGE)
    parts = [part.strip() for part in SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InvalidInputError(FORMAT_ERROR_MESSAGE)
    return parts[0], parts[1]


def resolve_stations(network, start_raw, end_raw):
    """Standardize and validate the starting and ending stations.

    Returns:
        (str, str): Official station names.

    Raises:
        StationNotFoundError: If a station does not exist (via InvalidInputError
            message for unknown stations).
        InvalidInputError: If both stations are the same.
    """
    start = network.standardize_name(start_raw)
    if start is None:
        raise InvalidInputError(
            f"Starting station '{start_raw}' does not exist, please check the station name"
        )
    end = network.standardize_name(end_raw)
    if end is None:
        raise InvalidInputError(
            f"Ending station '{end_raw}' does not exist, please check the station name"
        )
    if start == end:
        raise InvalidInputError("Starting station cannot be the same as the ending station")
    return start, end


def resolve_line_preference(network, value):
    """Map a user-entered line name (e.g. '1' or 'line 1') to an official line name.

    Returns:
        str or None: The official line name, or None when no preference is given.
    """
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    candidates = {cleaned.casefold(), f"line {cleaned}".casefold()}
    for line in network.line_names():
        if line.casefold() in candidates:
            return line
    raise InvalidInputError(
        f"Unknown line preference '{value}'. Known lines: {', '.join(network.line_names())}"
    )


class QuerySession:
    """Holds the network, the query configuration and all results of a session."""

    def __init__(self, network, config, output_file=None, fmt="text"):
        self.network = network
        self.config = config
        self.output_file = output_file
        self.fmt = fmt
        self.routes = []

    def run_query(self, query_text):
        """Execute one query and return the rendered report.

        Raises:
            SubwayError: For any invalid input, unknown station, missing path
                or export failure.
        """
        start_raw, end_raw = parse_query(query_text)
        start, end = resolve_stations(self.network, start_raw, end_raw)
        route = find_route(self.network, start, end, self.config)
        self.routes.append(route)
        rendered = format_text(route) if self.fmt == "text" else format_json(route)
        if self.output_file:
            try:
                self._export()
            except OSError as exc:
                raise SubwayError(
                    f"could not write output file '{self.output_file}': {exc}"
                ) from exc
        return rendered

    def _export(self):
        """Write all results of the session to the output file."""
        if self.fmt == "json":
            content = json.dumps(
                [route_to_dict(route) for route in self.routes],
                ensure_ascii=False,
                indent=2,
            )
        else:
            content = "\n\n".join(format_text(route) for route in self.routes)
        return export_report(content, self.output_file)


def _execute_query(session, text):
    """Run a query and print either the report or an error message."""
    try:
        rendered = session.run_query(text)
    except SubwayError as exc:
        print(f"Error: {exc}")
    except Exception as exc:  # defensive: never crash the interactive loop
        print(f"Error: unexpected failure while calculating the route: {exc}")
    else:
        print(rendered)


def _handle_mode_command(session, text):
    """Handle 'mode' commands in the interactive loop."""
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        print(f"Current mode: {session.config.mode}")
        return
    value = parts[1].strip()
    if value not in VALID_MODES:
        print(f"Error: unknown mode '{value}', expected one of: {', '.join(VALID_MODES)}")
        return
    session.config.mode = value
    print(f"Query mode set to: {value}")


def interactive_loop(session, input_func=input):
    """Run the continuous query loop until the user quits or input ends."""
    print("Beijing Subway Fare Calculation System")
    print("Type 'help' for commands. Enter 'Starting Station; Ending Station' to query.")
    while True:
        try:
            raw = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        lowered = text.casefold()
        if lowered in QUIT_COMMANDS:
            break
        if lowered in ("help", "?"):
            print(HELP_TEXT)
            continue
        first_word = text.split(maxsplit=1)[0].casefold()
        if first_word == "mode" and ";" not in text:
            _handle_mode_command(session, text)
            continue
        _execute_query(session, text)
    print("Goodbye.")


def main(argv=None):
    """CLI entry point. Returns the process exit code."""
    args = parse_args(argv)
    try:
        network = SubwayNetwork(load_subway_data())
    except SubwayError as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_data_integrity(network)
        print(report.to_text())
        return 0 if report.ok else 1

    try:
        line_preference = resolve_line_preference(network, args.line_preference)
    except InvalidInputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=[line_preference] if line_preference else [],
    )
    session = QuerySession(network, config, args.output_file, args.format)

    if args.query is not None:
        try:
            rendered = session.run_query(args.query)
        except SubwayError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:  # defensive
            print(f"Error: unexpected failure while calculating the route: {exc}", file=sys.stderr)
            return 1
        print(rendered)
        return 0

    interactive_loop(session)
    return 0
