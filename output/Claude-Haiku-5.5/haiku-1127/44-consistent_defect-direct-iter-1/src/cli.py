"""Command-line interface of the Beijing Subway fare calculation system."""

import argparse
import re
import sys

import data_loader
import data_manager
import fare_calculator
import models
import pathfinding
import report


SEPARATOR_PATTERN = re.compile(r"[;,]")
EXIT_WORDS = ("q", "quit", "exit")


class QueryError(Exception):
    """Raised for user-facing query errors (input, station or path problems)."""


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=pathfinding.VALID_MODES,
                        default=pathfinding.MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query(text):
    """Split 'Starting Station; Ending Station' input into two names.

    Both ';' and ',' are accepted as separators.

    Raises:
        QueryError: If the input does not contain exactly two station names.
    """
    parts = [part.strip() for part in SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise QueryError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0], parts[1]


def parse_line_preference(text):
    """Split a comma-separated line preference string into a list."""
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def resolve_endpoint(network, raw, label):
    """Resolve one endpoint name. Returns (official_name, matched_fuzzy)."""
    try:
        return network.resolve_station(raw)
    except models.UnknownStationError:
        raise QueryError(
            f"{label} station '{raw}' does not exist, please check the station name")


def answer_query(network, text, config, fmt):
    """Process one query and return (rendered_output, notes).

    Raises:
        QueryError: For any user-facing problem with the query.
    """
    start_raw, end_raw = parse_query(text)
    start, start_fuzzy = resolve_endpoint(network, start_raw, "Starting")
    end, end_fuzzy = resolve_endpoint(network, end_raw, "Ending")

    notes = []
    if start_fuzzy:
        notes.append(f"Note: starting station '{start_raw}' matched to nearest station '{start}'")
    if end_fuzzy:
        notes.append(f"Note: ending station '{end_raw}' matched to nearest station '{end}'")

    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        route = pathfinding.find_route(network, start, end, config)
    except pathfinding.PathNotFoundError as exc:
        raise QueryError(str(exc))
    except (KeyError, ValueError) as exc:
        raise QueryError(f"Path calculation failed: {exc}")

    try:
        fare = fare_calculator.Sum_money(route.distance)
    except (TypeError, ValueError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}")

    query = {
        "start": start,
        "end": end,
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": config.preferred_lines,
    }
    if fmt == "json":
        rendered = report.format_json(query, route, fare)
    else:
        rendered = report.format_text(query, route, fare)
    return rendered, notes


def write_output(path, content):
    """Append rendered content to the output file."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content + "\n\n")


def run_data_check(network):
    """Print integrity check results. Returns the process exit code."""
    messages = data_manager.check_integrity(network)
    print("Data integrity check")
    print("-" * 40)
    if not messages:
        print("No problems found.")
    for message in messages:
        print(message)
    errors = sum(1 for m in messages if m.startswith("[ERROR]"))
    warnings = len(messages) - errors
    print("-" * 40)
    print(f"Stations: {len(network.station_to_number)}, "
          f"connections: {network.graph.edge_count}, "
          f"lines: {len(network.line_names)}")
    print(f"Errors: {errors}, warnings: {warnings}")
    return 1 if errors else 0


def run_interactive(network, config, fmt, output_file):
    """Run the continuous query loop until the user quits."""
    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
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
            rendered, notes = answer_query(network, text, config, fmt)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # keep the session alive on unexpected errors
            print(f"Unexpected error while processing query: {exc}")
            continue

        for note in notes:
            print(note)
        print(rendered)

        if output_file:
            try:
                write_output(output_file, rendered)
            except OSError as exc:
                print(f"Error: cannot write output file '{output_file}': {exc}")
    print("Goodbye.")


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = data_loader.load_subway_data(data_loader.DATA_FILE_PATH)
    except data_loader.DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        network = models.build_network(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Error: cannot build subway network: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(network)

    preferred = parse_line_preference(args.line_preference)
    try:
        config = pathfinding.PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    for line in preferred:
        if line not in network.line_names:
            print(f"Warning: preferred line '{line}' is not in the network data")

    run_interactive(network, config, args.format, args.output_file)
    return 0
