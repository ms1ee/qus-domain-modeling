"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import json
import sys

from data_loader import DATA_FILE_PATH, DataError, build_network, load_subway_data
from data_manager import DataManager
from fare_calculator import Sum_money  # noqa: F401  (fare is computed in path_report)
from path_report import build_report, render_json, render_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    NoPathError,
    PathfindingConfig,
    find_route,
)

PROMPT = "Enter query ('Starting Station; Ending Station', or 'quit' to exit): "
FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = ("quit", "exit", "q")


class QueryError(Exception):
    """Base class for errors that are reported to the user without stopping the program."""


class InputFormatError(QueryError):
    """The query text does not match 'Starting Station; Ending Station'."""


class StationNotFoundError(QueryError):
    """A station name does not match any official station."""


class SameStationError(QueryError):
    """Starting and ending stations are identical."""


class PathCalculationError(QueryError):
    """No path could be computed."""


class FareCalculationError(QueryError):
    """The fare could not be calculated for the route."""


def _normalize(text):
    """Normalise a name for lenient comparison (case, spaces, hyphens, underscores)."""
    return "".join(ch for ch in text.lower() if ch not in " -_'")


def resolve_station(network, raw_name, role):
    """Map user input to an official station name, or raise StationNotFoundError."""
    name = raw_name.strip()
    if name in network.station_to_number:
        return name

    normalized = _normalize(name)
    matches = [station for station in network.station_names() if _normalize(station) == normalized]
    if len(matches) == 1:
        return matches[0]

    suggestions = difflib.get_close_matches(name, network.station_names(), n=3, cutoff=0.6)
    message = f"{role} station '{name}' does not exist, please check the station name"
    if suggestions:
        message += f". Did you mean: {', '.join(suggestions)}?"
    raise StationNotFoundError(message)


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw names."""
    parts = text.split(";")
    if len(parts) != 2:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    return start, end


def run_query(network, text, config):
    """Execute one query and return the structured summary dictionary."""
    start_raw, end_raw = parse_query(text)
    start = resolve_station(network, start_raw, "Starting")
    end = resolve_station(network, end_raw, "Ending")
    if start == end:
        raise SameStationError("Starting station cannot be the same as the ending station")

    try:
        route = find_route(network, start, end, config)
    except NoPathError as exc:
        raise PathCalculationError(f"No route found from '{start}' to '{end}': {exc}") from exc
    except ValueError as exc:
        raise PathCalculationError(f"Path calculation failed: {exc}") from exc

    query_info = {
        "start": start,
        "end": end,
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": list(config.preferred_lines),
    }
    try:
        return build_report(route, network, query_info)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc


def _non_negative_int(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


def build_parser():
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file (overwritten with the session history)")
    parser.add_argument("--format", dest="output_format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' (comma separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def _resolve_line_preferences(raw, network):
    """Validate and canonicalise the --line_preference argument."""
    if not raw:
        return []
    known = network.all_line_names()
    lookup = {_normalize(line): line for line in known}
    result = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        key = _normalize(text)
        if key not in lookup:
            raise ValueError(f"Unknown line '{text}'. Known lines: {', '.join(known)}")
        if lookup[key] not in result:
            result.append(lookup[key])
    return result


def _write_output_file(path, summaries, output_format):
    """Write the session history to the output file."""
    if output_format == "json":
        content = json.dumps(summaries, ensure_ascii=False, indent=2)
    else:
        content = "\n\n".join(render_text(summary) for summary in summaries)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content + "\n")


def interactive_loop(network, config, output_format, output_file=None,
                     input_func=input, output_func=print):
    """Run the continuous query loop until the user quits or input ends."""
    history = []
    output_func(f"Beijing Subway fare calculator - {len(network.station_to_number)} stations loaded.")
    output_func("Type 'quit' to exit.")

    while True:
        try:
            line = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break

        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            summary = run_query(network, text, config)
        except QueryError as exc:
            output_func(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never crash the interactive session
            output_func(f"Unexpected error while processing the query: {exc}")
            continue

        if output_format == "json":
            output_func(render_json(summary))
        else:
            output_func(render_text(summary))

        if output_file:
            history.append(summary)
            try:
                _write_output_file(output_file, history, output_format)
            except OSError as exc:
                output_func(f"Error: cannot write output file '{output_file}': {exc}")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = build_network(data)
    except DataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = DataManager(network).check_integrity()
        print(report.format())
        return 1 if report.has_errors() else 0

    try:
        preferences = _resolve_line_preferences(args.line_preference, network)
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferences,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return interactive_loop(
        network,
        config,
        output_format=args.output_format,
        output_file=args.output_file,
    )
