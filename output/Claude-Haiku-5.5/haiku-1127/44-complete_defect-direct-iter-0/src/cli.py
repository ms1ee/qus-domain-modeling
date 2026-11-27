"""Command-line interface for the Beijing Subway fare calculation system.

Supports:
    * interactive continuous queries of the form "Starting Station; Ending Station"
    * command-line options (--output_file, --format, --mode, --max_transfers,
      --line_preference, --check_data)
    * input validation and graceful error reporting
"""

import argparse
import re
import sys
from typing import Callable, List, Optional, Sequence, Tuple

from data_loader import DATA_FILE_PATH, load_subway_data
from path_summary import QueryError, compute_route_summary
from pathfinding import VALID_MODES, PathfindingConfig
from subway_network import SubwayNetwork
from visualization import export_to_file, render_summary

EXIT_WORDS = ("quit", "exit", "q")
SEPARATOR_PATTERN = re.compile(r"[;\uff1b]")  # ASCII and full-width semicolon
FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class InputFormatError(QueryError):
    """Raised when the user input does not follow the required format."""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation and route query system"
    )
    parser.add_argument("--output_file", default=None,
                        help="export each query result to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser.parse_args(argv)


def parse_query(text: str) -> Tuple[str, str]:
    """Split a 'Starting Station; Ending Station' input into two station names.

    Raises:
        InputFormatError: If the input does not contain exactly two non-empty parts.
    """
    parts = SEPARATOR_PATTERN.split(text)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def build_config(args: argparse.Namespace, network: SubwayNetwork) -> PathfindingConfig:
    """Create a PathfindingConfig from parsed command-line arguments.

    Raises:
        ValueError: If an argument value is invalid.
    """
    config = PathfindingConfig()
    config.mode = args.mode
    if args.max_transfers is not None:
        if args.max_transfers < 0:
            raise ValueError("--max_transfers must be a non-negative integer")
        config.max_transfers = args.max_transfers
    if args.line_preference:
        preferences = [item.strip() for item in args.line_preference.split(",") if item.strip()]
        known = set(network.lines())
        for line in preferences:
            if line not in known:
                print(f"Warning: line '{line}' is not a known subway line", file=sys.stderr)
        config.preferred_lines = preferences
    config.validate()
    return config


def run_integrity_check(network: SubwayNetwork,
                        output_func: Callable[[str], None] = print) -> int:
    """Run the data integrity check and print the report.

    Returns:
        0 if no issues were found, 1 otherwise.
    """
    report = network.check_integrity()
    total = 0
    for section in ("coverage", "connections", "distances"):
        issues = report[section]
        total += len(issues)
        status = "OK" if not issues else f"{len(issues)} issue(s)"
        output_func(f"[{section}] {status}")
        for issue in issues:
            output_func(f"  - {issue}")
    if total == 0:
        output_func("Data integrity check passed.")
        return 0
    output_func(f"Data integrity check finished with {total} issue(s).")
    return 1


def process_query(network: SubwayNetwork, text: str, config: PathfindingConfig, fmt: str) -> str:
    """Answer one query string and return the rendered result.

    Raises:
        QueryError: For input format, station, route or fare problems.
    """
    start_raw, end_raw = parse_query(text)
    summary = compute_route_summary(network, start_raw, end_raw, config)
    return render_summary(summary, fmt)


def run_query_loop(network: SubwayNetwork, config: PathfindingConfig, fmt: str,
                   output_file: Optional[str],
                   input_func: Callable[[str], str] = input,
                   output_func: Callable[[str], None] = print) -> int:
    """Interactive continuous query loop. Returns the process exit code."""
    output_func("Beijing Subway fare calculator")
    output_func("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")
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
            rendered = process_query(network, text, config, fmt)
        except QueryError as exc:
            output_func(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort safety net to keep the session alive
            output_func(f"Unexpected error while processing the query: {exc}")
            continue
        output_func(rendered)
        if output_file:
            try:
                export_to_file(rendered, output_file)
                output_func(f"Result exported to {output_file}")
            except OSError as exc:
                output_func(f"Failed to write output file: {exc}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)
    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data from '{DATA_FILE_PATH}': {exc}", file=sys.stderr)
        return 1

    try:
        network = SubwayNetwork(data)
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Subway data is malformed: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_integrity_check(network)

    try:
        config = build_config(args, network)
    except ValueError as exc:
        print(f"Invalid option: {exc}", file=sys.stderr)
        return 2

    return run_query_loop(network, config, args.format, args.output_file)
