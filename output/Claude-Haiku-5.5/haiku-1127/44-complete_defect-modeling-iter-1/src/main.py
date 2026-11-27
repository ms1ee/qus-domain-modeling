"""Command-line interface for the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --format json --output_file result.json
    python src/main.py --mode least_transfer --max_transfers 2
    python src/main.py --line_preference "Line 1"
    python src/main.py --check_data

Inside the interactive loop, enter queries as "Starting Station; Ending Station".
Type "quit", "exit", or "q" to leave the program.
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple

from data_loader import load_subway_data
from fare_calculator import Sum_money
from integrity import check_network
from models import Route
from network import SubwayNetwork
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    PathNotFoundError,
    ShortestPath,
    build_route,
)
from report import format_json, format_text, write_report

EXIT_WORDS = {"quit", "exit", "q"}


class QueryError(Exception):
    """Base class for user-facing query errors."""


class QueryFormatError(QueryError):
    """The input does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(QueryError):
    """A station name does not match any official station."""


class QueryLogicError(QueryError):
    """The query is logically invalid (e.g., same start and end station)."""


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma-separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser.parse_args(argv)


def parse_query(text: str) -> Tuple[str, str]:
    """Split 'Starting Station; Ending Station' into its two parts.

    Raises:
        QueryFormatError: If the format is wrong.
    """
    parts = text.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryFormatError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0].strip(), parts[1].strip()


def resolve_station(network: SubwayNetwork, raw: str, role: str) -> str:
    """Return the official station name for ``raw``.

    Args:
        role: 'Starting' or 'Ending', used in the error message.

    Raises:
        StationNotFoundError: If no official station matches.
    """
    official = network.standardize_name(raw)
    if official is None:
        raise StationNotFoundError(f"{role} station '{raw}' does not exist, please check the station name")
    return official


def parse_preferred_lines(text: Optional[str]) -> List[str]:
    """Split a comma-separated line preference into a list of line names."""
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def compute_route(network: SubwayNetwork, start: str, end: str, config: PathfindingConfig) -> Route:
    """Compute the route between two official station names.

    Raises:
        QueryLogicError: If start and end are the same station.
        QueryError: If no route exists or path calculation fails.
    """
    if start == end:
        raise QueryLogicError("Starting station cannot be the same as the ending station")
    try:
        start_number = network.graph.number_of(start)
        end_number = network.graph.number_of(end)
        finder = ShortestPath(network.graph, start_number, config)
        if not finder.has_path_to(end_number):
            raise QueryError(
                f"No route found from '{start}' to '{end}' under the current constraints"
            )
        numbers, edges = finder.path_with_edges(end_number)
        return build_route(network.graph, numbers, edges, config.mode)
    except QueryError:
        raise
    except PathNotFoundError as exc:
        raise QueryError(f"No route found from '{start}' to '{end}': {exc}") from exc
    except (ValueError, KeyError, IndexError) as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc


def process_query(network: SubwayNetwork, text: str, config: PathfindingConfig, fmt: str,
                  max_transfers: Optional[int], preferred: List[str]) -> str:
    """Run one query end-to-end and return the rendered report.

    Raises:
        QueryError: For any user-facing error (format, station, logic, path, fare).
    """
    raw_start, raw_end = parse_query(text)
    start = resolve_station(network, raw_start, "Starting")
    end = resolve_station(network, raw_end, "Ending")
    route = compute_route(network, start, end, config)

    try:
        fare = Sum_money(route.total_distance_m)
    except (TypeError, ValueError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc

    query: Dict[str, object] = {
        "start": start,
        "end": end,
        "mode": config.mode,
        "max_transfers": max_transfers,
        "line_preference": ",".join(preferred) if preferred else None,
    }
    if fmt == "json":
        return format_json(route, fare, query)
    return format_text(route, fare, query)


def run_integrity_check(network: SubwayNetwork) -> int:
    """Print the integrity check report and return a process exit code."""
    result = check_network(network)
    if result.passed:
        print("Data integrity check passed.")
        return 0
    print("Data integrity check found the following issues:")
    for issue in result.issues:
        print(f"  - {issue}")
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data()
        network = SubwayNetwork(data)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_integrity_check(network)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must not be negative", file=sys.stderr)
        return 2

    preferred = parse_preferred_lines(args.line_preference)
    known_lines = set(network.lines())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not in the network data")

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway fare calculator.")
    print("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")

    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            content = process_query(network, text, config, args.format,
                                    args.max_transfers, preferred)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never crash the interactive loop
            print(f"Error: unexpected failure while processing query: {exc}")
            continue

        print(content)
        if args.output_file:
            try:
                write_report(content, args.output_file)
            except OSError as exc:
                print(f"Warning: could not write output file '{args.output_file}': {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
