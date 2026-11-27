"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --mode least_transfer --format json
    python src/main.py --max_transfers 2 --line_preference "Line 1"
    python src/main.py --output_file result.txt
    python src/main.py --check_data
"""
from __future__ import annotations

import argparse
import sys
from typing import Callable, Optional, Sequence

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import check_data_integrity
from fare_calculator import Sum_money, calculate_estimated_time
from models import NoPathError, SubwayError
from pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig, RouteResult, find_route
from report import format_json_report, format_text_report, write_report
from subway_network import SubwayNetwork

EXIT_WORDS = {"quit", "exit", "q"}
INPUT_PROMPT = "Enter query as 'Starting Station; Ending Station' ('quit' to exit): "
INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryInputError(SubwayError):
    """Raised when the user's query text is invalid."""


class FareCalculationError(SubwayError):
    """Raised when the fare or time estimate cannot be computed."""


def parse_query(text: str) -> tuple[str, str]:
    """Split 'Starting Station; Ending Station' into two raw station names."""
    if ";" not in text:
        raise QueryInputError(INPUT_FORMAT_MESSAGE)
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryInputError(INPUT_FORMAT_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryInputError(INPUT_FORMAT_MESSAGE)
    return start, end


def resolve_station(network: SubwayNetwork, raw: str, role: str) -> str:
    """Standardize a station name and verify that it exists."""
    name = network.normalize_station_name(raw)
    if name is None:
        raise QueryInputError(
            f"{role} station '{raw}' does not exist, please check the station name"
        )
    return name


def run_query(network: SubwayNetwork, text: str,
              config: PathfindingConfig) -> tuple[RouteResult, int, float]:
    """Validate a query, compute the route, the fare and the estimated time.

    Returns:
        (route, fare in yuan, estimated time in minutes)
    """
    start_raw, end_raw = parse_query(text)
    start = resolve_station(network, start_raw, "Starting")
    end = resolve_station(network, end_raw, "Ending")
    if start == end:
        raise QueryInputError("Starting station cannot be the same as the ending station")

    route = find_route(network, start, end, config)  # may raise NoPathError

    try:
        fare = Sum_money(route.distance_m)
        estimated = calculate_estimated_time(route.distance_m, route.transfers)
    except ValueError as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc
    return route, fare, estimated


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculator with Dijkstra shortest-path search."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_line_preference(value: Optional[str]) -> list[str]:
    """Turn a comma-separated preference string into a list of line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def run_interactive(network: SubwayNetwork, config: PathfindingConfig, args: argparse.Namespace,
                    input_fn: Callable[[str], str] = input,
                    out=None, err=None) -> int:
    """Run the continuous query loop until the user quits."""
    out = out or sys.stdout
    err = err or sys.stderr
    print("Beijing Subway Fare Calculation System", file=out)
    print("Type a query like 'Xizhimen; Zhichunlu', or 'quit' to exit.", file=out)

    output_started = False
    while True:
        try:
            text = input_fn(INPUT_PROMPT)
        except (EOFError, KeyboardInterrupt):
            print(file=out)
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            route, fare, estimated = run_query(network, text, config)
        except QueryInputError as exc:
            print(f"Error: {exc}", file=err)
            continue
        except NoPathError as exc:
            print(f"Error: {exc}", file=err)
            continue
        except FareCalculationError as exc:
            print(f"Error: {exc}", file=err)
            continue
        except SubwayError as exc:
            print(f"Error: path calculation failed: {exc}", file=err)
            continue
        except Exception as exc:  # last-resort guard keeps the session alive
            print(f"Error: unexpected failure: {exc}", file=err)
            continue

        if args.format == "json":
            rendered = format_json_report(route, fare, estimated)
        else:
            rendered = format_text_report(route, fare, estimated)
        print(rendered, file=out)

        if args.output_file:
            try:
                write_report(rendered, args.output_file, append=output_started)
                output_started = True
            except OSError as exc:
                print(f"Error: cannot write output file '{args.output_file}': {exc}", file=err)
    return 0


def main(argv: Optional[Sequence[str]] = None, input_fn: Callable[[str], str] = input) -> int:
    """Entry point of the CLI. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: cannot load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_data_integrity(data)
        print(report.render())
        return 0 if report.is_ok() else 1

    try:
        network = SubwayNetwork.from_data(data)
    except SubwayError as exc:
        print(f"Error: cannot build subway network: {exc}", file=sys.stderr)
        return 1

    preferred = parse_line_preference(args.line_preference)
    unknown = [line for line in preferred if line not in network.line_stations]
    if unknown:
        print(f"Warning: unknown line(s) in --line_preference ignored: {', '.join(unknown)}",
              file=sys.stderr)
        preferred = [line for line in preferred if line in network.line_stations]

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    return run_interactive(network, config, args, input_fn)
