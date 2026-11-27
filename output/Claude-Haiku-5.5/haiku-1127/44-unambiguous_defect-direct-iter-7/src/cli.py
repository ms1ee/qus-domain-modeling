"""Command-line interface for the Beijing Subway fare calculator."""

from __future__ import annotations

import argparse
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import format_check_report, has_errors, run_integrity_check
from fare_calculator import FareCalculationError
from input_validator import ValidationError, parse_line_preferences, parse_query
from models import SubwayNetwork, build_network
from pathfinding import (
    MODE_COMPREHENSIVE,
    VALID_MODES,
    PathfindingConfig,
    PathNotFoundError,
)
from report import format_text_report, render_json, render_results
from route_service import query_route

EXIT_WORD_LIST = ("q", "quit", "exit")
HELP_WORD_LIST = ("help", "?")

HELP_TEXT = """Enter a query in the form 'Starting Station; Ending Station'.
Examples:  Xizhimen; Guomen
Commands:  help  - show this help
           q     - quit the program"""


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", dest="output_format", choices=["text", "json"],
                        default="text", help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_COMPREHENSIVE,
                        help="path query mode (default: comprehensive)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' (comma separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def _write_output_file(results, path: str, output_format: str) -> None:
    content = render_results(results, output_format)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def run_interactive(network: SubwayNetwork, config: PathfindingConfig,
                    output_format: str = "text", output_file: str = None,
                    input_func=input, out=print) -> int:
    """Run the continuous query loop until the user quits.

    Each successful query is printed and, if ``output_file`` is given, the
    file is rewritten with all results of the session so far.
    """
    results = []
    out("Beijing Subway fare calculator. Type 'help' for instructions.")
    while True:
        try:
            raw = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            out("")
            break
        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in EXIT_WORD_LIST:
            break
        if lowered in HELP_WORD_LIST:
            out(HELP_TEXT)
            continue

        try:
            start, end = parse_query(text)
            result = query_route(network, start, end, config)
        except ValidationError as exc:
            out(f"Error: {exc}")
            continue
        except PathNotFoundError as exc:
            out(f"Error: {exc}")
            continue
        except FareCalculationError as exc:
            out(f"Fare calculation error: {exc}")
            continue
        except Exception as exc:  # last-resort guard so the session keeps running
            out(f"Unexpected error while calculating the route: {exc}")
            continue

        results.append(result)
        if output_format == "json":
            out(render_json([result]))
        else:
            out(format_text_report(result))

        if output_file:
            try:
                _write_output_file(results, output_file, output_format)
                out(f"Results saved to {output_file}")
            except OSError as exc:
                out(f"Error: could not write output file '{output_file}': {exc}")
    return 0


def main(argv=None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        raw_data = load_subway_data(DATA_FILE_PATH)
        network = build_network(raw_data)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        issues = run_integrity_check(network)
        print(format_check_report(issues))
        return 1 if has_errors(issues) else 0

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must not be negative", file=sys.stderr)
        return 2

    try:
        preferred = parse_line_preferences(args.line_preference, network)
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except (ValidationError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_interactive(network, config, args.output_format, args.output_file)
