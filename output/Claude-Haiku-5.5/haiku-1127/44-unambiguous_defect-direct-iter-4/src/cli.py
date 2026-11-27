"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import os
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import check_data_integrity
from input_validator import ValidationError, resolve_line, validate_query
from models import SubwayNetwork
from pathfinding import (
    DEFAULT_MODE,
    MODE_COMPREHENSIVE,
    MODE_LEAST_TRANSFER,
    MODE_SHORTEST_DISTANCE,
    PathfindingConfig,
    PathNotFoundError,
)
from report import format_json, format_json_session, format_text, format_text_session
from route_service import FareCalculationError, query_route

FORMAT_TEXT = "text"
FORMAT_JSON = "json"

HELP_TEXT = """Commands:
  Enter a query in the form 'Starting Station; Ending Station'
  (',' also works as separator), e.g.  西直门; 国贸
  help   - show this help
  quit   - exit the program"""


def _non_negative_int(value):
    """argparse type: a non-negative integer."""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"'{value}' is not an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra-based route planner).")
    parser.add_argument("--output_file", default=None,
                        help="Export query results to this file (rewritten with all results of the session).")
    parser.add_argument("--format", dest="format", choices=[FORMAT_TEXT, FORMAT_JSON],
                        default=FORMAT_TEXT, help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=[MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE],
                        default=DEFAULT_MODE,
                        help="Path query mode (default: comprehensive).")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="Maximum number of transfers allowed.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run data integrity check and exit.")
    return parser


def build_config(args, network) -> PathfindingConfig:
    """Build a PathfindingConfig from parsed arguments, resolving line preferences.

    Raises:
        ValueError: If a preferred line is unknown or other settings are invalid.
    """
    preferred = []
    if args.line_preference:
        for raw in args.line_preference.split(","):
            if not raw.strip():
                continue
            official = resolve_line(raw, network.lines())
            if official is None:
                raise ValueError(
                    f"Unknown line preference '{raw.strip()}'. Known lines: {', '.join(network.lines())}")
            if official not in preferred:
                preferred.append(official)
    return PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                             preferred_lines=preferred)


def write_output_file(path, results, fmt):
    """Write all session results to ``path`` in the requested format."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    if fmt == FORMAT_JSON:
        content = format_json_session(results)
    else:
        content = format_text_session(results)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content + "\n")


def process_query(network, text, config):
    """Validate a raw query string and compute the route result.

    Raises:
        ValidationError, PathNotFoundError, FareCalculationError, ValueError.
    """
    start, end = validate_query(text, network.station_names())
    return query_route(network, start, end, config)


def _print_error(message):
    print(f"Error: {message}")


def main(argv=None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    network = SubwayNetwork.from_data(data)

    if args.check_data:
        report = check_data_integrity(data, network)
        print(report.format())
        return 0 if report.passed else 1

    try:
        config = build_config(args, network)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway fare calculator")
    print(HELP_TEXT)
    print(f"Mode: {config.mode}"
          + (f", max transfers: {config.max_transfers}" if config.max_transfers is not None else "")
          + (f", line preference: {', '.join(config.preferred_lines)}" if config.preferred_lines else ""))

    results = []
    while True:
        try:
            raw = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in ("quit", "exit", "q"):
            break
        if lowered == "help":
            print(HELP_TEXT)
            continue

        try:
            result = process_query(network, text, config)
        except ValidationError as exc:
            _print_error(str(exc))
            continue
        except PathNotFoundError as exc:
            _print_error(f"{exc}. Try raising --max_transfers or changing --mode.")
            continue
        except FareCalculationError as exc:
            _print_error(str(exc))
            continue
        except ValueError as exc:
            _print_error(str(exc))
            continue
        except Exception as exc:  # keep the session alive for unexpected failures
            _print_error(f"Unexpected error while calculating the route: {exc}")
            continue

        if args.format == FORMAT_JSON:
            print(format_json(result))
        else:
            print(format_text(result))
        results.append(result)

        if args.output_file:
            try:
                write_output_file(args.output_file, results, args.format)
                print(f"Results saved to {args.output_file}")
            except OSError as exc:
                _print_error(f"Cannot write output file '{args.output_file}': {exc}")

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
