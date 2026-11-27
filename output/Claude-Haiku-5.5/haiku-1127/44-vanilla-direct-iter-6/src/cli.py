"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys
import unicodedata

from data_loader import load_subway_data
from data_manager import check_data_integrity
from models import build_network
from path_report import build_report_data, export_report, render_json, render_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    PathNotFoundError,
    plan_route,
)

EXIT_COMMANDS = ("quit", "exit", "q")
QUERY_PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "


class QueryError(Exception):
    """Base class for user-facing query errors."""


class InputFormatError(QueryError):
    """The query text is not in 'Starting Station; Ending Station' form."""


class StationNotFoundError(QueryError):
    """A station name does not match any station in the network."""


class QueryLogicError(QueryError):
    """The query is logically invalid (for example identical endpoints)."""


def _normalize_key(name):
    """Normalize a station name for loose matching."""
    text = unicodedata.normalize("NFKC", name)
    text = " ".join(text.split()).casefold()
    if len(text) > 1 and text.endswith("站"):
        text = text[:-1].rstrip()
    return text


def _clean(text):
    """Trim and collapse whitespace, applying NFKC normalization."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


class StationIndex:
    """Resolves user-typed station names to official network station names."""

    def __init__(self, network):
        self._exact = set(network.station_to_number)
        self._by_key = {}
        for name in network.station_names():
            self._by_key.setdefault(_normalize_key(name), name)

    def resolve(self, raw):
        """Return the official station name for ``raw``, or None if unknown."""
        cleaned = _clean(raw)
        if cleaned in self._exact:
            return cleaned
        return self._by_key.get(_normalize_key(cleaned))


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw names.

    Raises:
        InputFormatError: If the separator is missing, repeated, or a name is empty.
    """
    message = "Input format incorrect, please use 'Starting Station; Ending Station' format"
    normalized = text.replace("；", ";")
    if normalized.count(";") != 1:
        raise InputFormatError(message)
    start, end = (part.strip() for part in normalized.split(";"))
    if not start or not end:
        raise InputFormatError(message)
    return start, end


def validate_query(raw_start, raw_end, index):
    """Validate station names and the logical constraints of a query.

    Returns:
        tuple: ``(start, end)`` official station names.

    Raises:
        StationNotFoundError: If a station does not exist.
        QueryLogicError: If the start and end stations are the same.
    """
    start = index.resolve(raw_start)
    if start is None:
        raise StationNotFoundError(
            f"Starting station '{raw_start}' does not exist, please check the station name")
    end = index.resolve(raw_end)
    if end is None:
        raise StationNotFoundError(
            f"Ending station '{raw_end}' does not exist, please check the station name")
    if start == end:
        raise QueryLogicError("Starting station cannot be the same as the ending station")
    return start, end


def parse_line_preference(text, known_lines):
    """Parse a comma-separated line preference string.

    Returns:
        tuple: ``(preferred_lines, unknown_tokens)``.
    """
    if not text:
        return [], []
    lookup = {line.casefold(): line for line in known_lines}
    preferred, unknown = [], []
    for token in text.split(","):
        token = _clean(token)
        if not token:
            continue
        canonical = lookup.get(token.casefold())
        if canonical is None:
            unknown.append(token)
            preferred.append(token)
        else:
            preferred.append(canonical)
    return preferred, unknown


def process_query(text, network, index, config, query_info, output_format):
    """Run one query end to end and return the rendered report text.

    Raises:
        QueryError: For input, station, path or fare errors.
    """
    raw_start, raw_end = parse_query(text)
    start, end = validate_query(raw_start, raw_end, index)

    try:
        route = plan_route(network, start, end, config)
    except PathNotFoundError as exc:
        raise QueryError(str(exc)) from exc
    except Exception as exc:  # defensive: unexpected path calculation failure
        raise QueryError(f"Path calculation failed: {exc}") from exc

    try:
        report = build_report_data(route, query_info)
    except (TypeError, ValueError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc

    return render_json(report) if output_format == "json" else render_text(report)


def run_interactive(network, index, config, query_info, output_format, output_file):
    """Run the continuous query loop until the user exits.

    Returns:
        int: Process exit code.
    """
    while True:
        try:
            line = input(QUERY_PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            return 0

        try:
            content = process_query(text, network, index, config,
                                    query_info, output_format)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # keep the session alive on unexpected errors
            print(f"Error: unexpected failure while answering the query: {exc}")
            continue

        print(content)
        if output_file:
            try:
                export_report(content, output_file)
                print(f"Result saved to {output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
        print()


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma-separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def main(argv=None):
    """Program entry point.

    Returns:
        int: Exit status code.
    """
    args = parse_args(argv)

    try:
        data = load_subway_data()
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_data_integrity(data)
        print(report.render())
        return 0 if report.ok else 1

    network = build_network(data)
    preferred, unknown = parse_line_preference(args.line_preference, network.lines())
    for token in unknown:
        print(f"Warning: line preference '{token}' is not a known subway line",
              file=sys.stderr)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    query_info = {
        "mode": args.mode,
        "max_transfers": args.max_transfers,
        "line_preference": ", ".join(preferred) if preferred else None,
    }
    index = StationIndex(network)

    print("Beijing Subway Fare Calculation System")
    print(f"Loaded {network.graph.num_vertices()} stations and "
          f"{network.graph.num_edges()} connections.")
    return run_interactive(network, index, config, query_info,
                           args.format, args.output_file)
