"""Command-line interface: argument parsing, interactive continuous queries."""

import argparse
import sys

from data_integrity import run_integrity_check
from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from network import SubwayNetwork
from pathfinding import PathfindingConfig
from query_service import QueryError, SubwayQueryService
from report import FORMAT_TEXT, SUPPORTED_FORMATS, ReportError, export_report

EXIT_WORDS = ("quit", "exit", "q")


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra shortest path)."
    )
    parser.add_argument("--output_file", default=None,
                        help="write the query result to this file")
    parser.add_argument("--format", choices=SUPPORTED_FORMATS, default=FORMAT_TEXT,
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=PathfindingConfig.MODES,
                        default=PathfindingConfig.MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser


def normalize_line_name(text):
    """Normalize a line preference: '1' becomes 'Line 1'."""
    cleaned = " ".join(text.split())
    if cleaned.isdigit():
        return "Line " + cleaned
    return cleaned


def run_interactive(service, config, output_format, output_file,
                    input_func=input, output_func=print):
    """Run the continuous query loop until the user quits or input ends.

    Returns:
        Process exit code (0).
    """
    output_func("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' "
                "(or 'quit' to exit).")
    while True:
        try:
            text = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        try:
            route = service.query_from_text(text, config)
        except QueryError as exc:
            output_func("Error: {}".format(exc))
            continue
        except Exception as exc:  # defensive: never crash the loop
            output_func("Unexpected error while processing query: {}".format(exc))
            continue

        try:
            report = export_report(route, output_format, output_file)
        except ReportError as exc:
            output_func("Error: {}".format(exc))
            continue
        output_func(report.content)
        if report.output_file_path:
            output_func("Result written to {}".format(report.output_file_path))
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data, data_source=DATA_FILE_PATH)
    except (DataLoadError, TypeError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1

    if args.check_data:
        result = run_integrity_check(network)
        for message in result.messages:
            print(message)
        print("Integrity check result: {}".format("PASSED" if result.passed else "FAILED"))
        return 0 if result.passed else 1

    preferred = []
    if args.line_preference:
        line = normalize_line_name(args.line_preference)
        preferred = [line]
        if line not in network.line_names:
            print("Warning: line '{}' is not in the network dataset".format(line), file=sys.stderr)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 2

    service = SubwayQueryService(network)
    return run_interactive(service, config, args.format, args.output_file)


if __name__ == "__main__":
    sys.exit(main())
