"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import re
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import check_data_integrity
from models import SubwayNetwork
from path_report import build_report, render_json, render_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    find_path,
)

EXIT_COMMANDS = ("quit", "exit", "q")
NEAREST_MATCH_CUTOFF = 0.6
_SEPARATOR_PATTERN = re.compile(r"[;,，；]")
_NOISE_PATTERN = re.compile(r"[\s\-_'’·•]+")
_STATION_SUFFIXES = ("station", "站")


class QueryError(Exception):
    """User-facing error raised while answering a query."""


def normalize_station_name(name):
    """Normalize a station name for lookup (case, spacing, and suffixes ignored)."""
    text = _NOISE_PATTERN.sub("", name).lower()
    for suffix in _STATION_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[:-len(suffix)]
    return text


class StationResolver:
    """Maps user-entered station names onto official station names."""

    def __init__(self, station_names):
        self._names = list(station_names)
        self._exact = set(self._names)
        self._by_key = {}
        for name in self._names:
            self._by_key.setdefault(normalize_station_name(name), name)

    def resolve(self, raw, role):
        """Resolve a raw station name.

        Args:
            raw: Name typed by the user.
            role: "Starting" or "Ending", used in messages.

        Returns:
            tuple: (official station name, note string or None).

        Raises:
            QueryError: If the name is empty or no station is similar enough.
        """
        cleaned = " ".join(raw.split())
        if not cleaned:
            raise QueryError(f"{role} station name cannot be empty.")
        if cleaned in self._exact:
            return cleaned, None
        key = normalize_station_name(cleaned)
        if key in self._by_key:
            name = self._by_key[key]
            return name, f"Note: '{cleaned}' standardized to '{name}'."
        matches = difflib.get_close_matches(
            key, list(self._by_key), n=1, cutoff=NEAREST_MATCH_CUTOFF)
        if not matches:
            raise QueryError(
                f"{role} station '{cleaned}' does not exist, "
                f"please check the station name.")
        name = self._by_key[matches[0]]
        note = (f"Note: {role.lower()} station '{cleaned}' not found exactly; "
                f"matched to nearest station '{name}'.")
        return name, note


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw station names.

    Raises:
        QueryError: If the input does not contain exactly two non-empty parts.
    """
    parts = [part.strip() for part in _SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not all(parts):
        raise QueryError("Input format incorrect, please use "
                         "'Starting Station; Ending Station' format.")
    return parts[0], parts[1]


def parse_line_preference(value):
    """Parse a comma-separated list of preferred line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_arguments(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="file to which query results are appended")
    parser.add_argument("--format", dest="output_format", choices=("text", "json"),
                        default="text", help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must not be negative")
    return args


def run_data_check(data):
    """Run the data integrity check, print results, and return an exit code."""
    errors, warnings = check_data_integrity(data)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"Data integrity check FAILED: {len(errors)} error(s), "
              f"{len(warnings)} warning(s).")
        return 1
    print(f"Data integrity check passed with {len(warnings)} warning(s).")
    return 0


def answer_query(network, resolver, text, config, output_format):
    """Answer one 'Starting; Ending' query.

    Returns:
        tuple: (list of notes, rendered report string).

    Raises:
        QueryError: For any user-facing failure.
    """
    raw_start, raw_end = parse_query(text)
    notes = []
    start, note = resolver.resolve(raw_start, "Starting")
    if note:
        notes.append(note)
    end, note = resolver.resolve(raw_end, "Ending")
    if note:
        notes.append(note)
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station.")

    try:
        result = find_path(network.graph, network.number(start),
                           network.number(end), config)
    except (KeyError, ValueError, IndexError) as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc
    if result is None:
        raise QueryError(f"No route found from '{start}' to '{end}' under the "
                         f"current settings (mode, max transfers, line preference).")

    names = [network.name_of(number) for number in result.station_numbers]
    query = {
        "start": start,
        "end": end,
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": list(config.preferred_lines),
    }
    try:
        report = build_report(query, names, result.edges)
    except (TypeError, ValueError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc

    if output_format == "json":
        rendered = render_json(report)
    else:
        rendered = render_text(report)
    return notes, rendered


def append_to_file(path, content):
    """Append rendered output to a file."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content + "\n\n")


def interactive_loop(network, config, output_format, output_file=None):
    """Run the continuous query loop until the user quits."""
    resolver = StationResolver(network.stations())
    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query (type 'quit' to exit).")
    while True:
        try:
            raw = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            notes, rendered = answer_query(network, resolver, text, config,
                                           output_format)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # keep the session alive on unexpected errors
            print(f"Unexpected error while answering query: {exc}")
            continue
        for note in notes:
            print(note)
        print(rendered)
        if output_file:
            try:
                append_to_file(output_file, rendered)
            except OSError as exc:
                print(f"Warning: could not write output file: {exc}")
    print("Goodbye.")
    return 0


def main(argv=None):
    """CLI entry point. Returns a process exit code."""
    args = parse_arguments(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except DataLoadError as exc:
        print(f"Error: {exc}")
        return 1

    if args.check_data:
        return run_data_check(data)

    try:
        config = PathfindingConfig(args.mode, args.max_transfers,
                                   parse_line_preference(args.line_preference))
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    try:
        network = SubwayNetwork(data)
    except (KeyError, ValueError, TypeError) as exc:
        print(f"Error: could not build subway network: {exc}")
        return 1

    return interactive_loop(network, config, args.output_format, args.output_file)


if __name__ == "__main__":
    sys.exit(main())
