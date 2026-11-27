"""Command-line interface: argument parsing, input validation, continuous queries."""

import argparse
import difflib
import sys
from datetime import datetime

from data_checker import DataChecker
from data_loader import build_graph, load_subway_data
from pathfinding import (
    DEFAULT_MAX_TRANSFERS,
    DEFAULT_MODE,
    VALID_MODES,
    PathfindingConfig,
    find_route,
)
from report import format_json, format_text, write_report
from subway_errors import (
    DataLoadError,
    InputFormatError,
    InvalidQueryError,
    StationNotFoundError,
    SubwayError,
)

SEPARATOR = ";"
EXIT_WORDS = {"quit", "exit", "q"}


def build_arg_parser():
    """Create the argument parser for the program."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=DEFAULT_MODE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=DEFAULT_MAX_TRANSFERS,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def normalize_station_name(raw):
    """Standardize whitespace in a user-supplied station name."""
    return " ".join(raw.replace("\u3000", " ").split())


def _fold(name):
    """Key used for lenient station-name matching."""
    return name.casefold().replace(" ", "")


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw names.

    Raises:
        InputFormatError: if the format is wrong.
    """
    normalized = text.replace("\uff1b", SEPARATOR)
    parts = normalized.split(SEPARATOR)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0], parts[1]


def resolve_station(graph, raw, role):
    """Standardize a station name and verify that it exists.

    Args:
        graph: the subway Graph.
        raw: user-supplied name.
        role: "Starting" or "Ending" (used in error messages).

    Raises:
        StationNotFoundError: if no station matches.
    """
    name = normalize_station_name(raw)
    if graph.has_station(name):
        return name
    names = graph.station_names()
    index = {}
    for station in names:
        index.setdefault(_fold(station), station)
    key = _fold(name)
    candidates = [key, key[:-1] if key.endswith("\u7ad9") else key + "\u7ad9"]
    for candidate in candidates:
        if candidate in index:
            return index[candidate]
    message = f"{role} station '{name}' does not exist, please check the station name"
    suggestions = difflib.get_close_matches(name, names, n=3, cutoff=0.5)
    if suggestions:
        message += f". Did you mean: {', '.join(suggestions)}?"
    raise StationNotFoundError(message)


def validate_query(graph, text):
    """Parse and validate a full query; return (start, end) station names."""
    raw_start, raw_end = parse_query(text)
    start = resolve_station(graph, raw_start, "Starting")
    end = resolve_station(graph, raw_end, "Ending")
    if start == end:
        raise InvalidQueryError(
            "Starting station cannot be the same as the ending station")
    return start, end


def run_single_query(graph, text, config, fmt, output_file=None):
    """Execute one query, optionally export it, and return the rendered text."""
    start, end = validate_query(graph, text)
    route = find_route(graph, start, end, config)
    timestamp = datetime.now().isoformat(timespec="seconds")
    if fmt == "json":
        rendered = format_json(route, timestamp, indent=2)
    else:
        rendered = format_text(route, timestamp)
    if output_file:
        if fmt == "json":
            # One compact JSON document per line (JSON Lines) when appending.
            write_report(format_json(route, timestamp, indent=None) + "\n",
                         output_file, append=True)
        else:
            write_report(rendered + "\n\n", output_file, append=True)
    return rendered


def build_config(args):
    """Create a PathfindingConfig from parsed command-line arguments.

    Raises:
        ValueError: for invalid mode or max_transfers.
    """
    preferred = []
    if args.line_preference:
        preferred = [item.strip() for item in args.line_preference.split(",")
                     if item.strip()]
    return PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                             preferred_lines=preferred)


def interactive_loop(graph, config, fmt, output_file=None):
    """Read queries until the user quits. Returns the process exit code."""
    print("Beijing Subway Fare Calculator")
    print("Enter a query as 'Starting Station; Ending Station'. "
          "Type 'quit' to exit.")
    while True:
        try:
            line = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        try:
            print(run_single_query(graph, text, config, fmt, output_file))
        except SubwayError as exc:
            print(f"Error: {exc}", file=sys.stderr)
        except OSError as exc:
            print(f"Error: cannot write output file: {exc}", file=sys.stderr)
        except Exception as exc:  # defensive: keep the session alive
            print(f"Error: unexpected failure while processing query: {exc}",
                  file=sys.stderr)
    return 0


def main(argv=None):
    """Program entry point. Returns the exit status code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data()
        graph = build_graph(data)
    except DataLoadError as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        checker = DataChecker(graph, data)
        ok = checker.run_all()
        print(checker.format_report())
        return 0 if ok else 1

    try:
        config = build_config(args)
    except ValueError as exc:
        print(f"Error: invalid configuration: {exc}", file=sys.stderr)
        return 2

    known_lines = set(graph.all_lines())
    for line in config.preferred_lines:
        if line not in known_lines:
            print(f"Warning: line preference '{line}' is not a known line",
                  file=sys.stderr)

    return interactive_loop(graph, config, args.format, args.output_file)


if __name__ == "__main__":
    sys.exit(main())
