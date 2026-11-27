"""Command-line interface: argument parsing, interactive query loop and error handling."""
from __future__ import annotations

import argparse
from typing import Callable, List, Optional

from data_checker import check_network
from data_loader import DATA_FILE_PATH, load_subway_data
from network import SubwayNetwork
from pathfinding import PathfindingConfig
from report import render, write_report
from service import QueryError, QueryService

EXIT_WORDS = {"quit", "exit", "q"}


def _non_negative_int(value: str) -> int:
    """argparse type for non-negative integers."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest path + fare)."
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", dest="fmt", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(PathfindingConfig.MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def main(
    argv: Optional[List[str]] = None,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> int:
    """Program entry point. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data)
    except (OSError, ValueError) as exc:
        output_func(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        checker = check_network(network)
        if checker.is_valid:
            output_func("Data integrity check passed.")
            return 0
        output_func(f"Data integrity check found {len(checker.errors)} problem(s):")
        for err in checker.errors:
            output_func(f"  - {err}")
        return 1

    preferred = [args.line_preference] if args.line_preference else []
    if args.line_preference and args.line_preference not in network.line_names():
        output_func(f"Warning: line '{args.line_preference}' is not in the dataset; preference has no effect.")

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        output_func(f"Error: {exc}")
        return 2

    service = QueryService(network)
    output_func("Beijing Subway fare query. Enter 'Starting Station; Ending Station' "
                "(type 'quit' to exit).")

    while True:
        try:
            raw = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            query, route = service.run(text, config)
            content = render(route, query, args.fmt)
        except QueryError as exc:
            output_func(f"Error: {exc}")
            continue
        except ValueError as exc:
            output_func(f"Error: {exc}")
            continue

        output_func(content)
        if args.output_file:
            try:
                write_report(content, args.output_file)
            except OSError as exc:
                output_func(f"Error: could not write report to '{args.output_file}': {exc}")

    return 0
