"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import json
import sys

from data_manager import SubwayNetwork
from errors import SubwayError
from pathfinding import VALID_MODES, PathfindingConfig
from report import export_report, to_json_dict, write_report
from route_service import RouteService, parse_query_input

EXIT_WORDS = ("q", "quit", "exit")
PROMPT = "Enter 'Starting Station; Ending Station' (or 'quit' to exit): "


def build_parser():
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare and route calculator (Dijkstra-based).",
    )
    parser.add_argument("--output_file", default=None,
                        help="Export query results to this file.")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="Output format: text (default) or json.")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance",
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of allowed transfers.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name(s), comma-separated, e.g. 'Line 1'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    return parser


def parse_line_preference(raw):
    """Split a comma-separated line preference string into a list of names."""
    if raw is None:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _write_output(output_file, result, fmt, session):
    """Write a query result to the output file.

    Text reports are appended. JSON output is rewritten as an array containing
    every result of the current session so the file always stays valid JSON.
    """
    if fmt == "json":
        session.append(result)
        payload = [to_json_dict(item) for item in session]
        write_report(output_file, json.dumps(payload, ensure_ascii=False, indent=2), append=False)
    else:
        write_report(output_file, export_report(result, "text") + "\n", append=True)


def run_interactive(service, config, output_file=None, fmt="text", input_func=input):
    """Run the continuous query loop until the user quits."""
    session = []
    print("Beijing Subway fare calculator. Type 'quit' to exit.")
    while True:
        try:
            raw = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            start, end = parse_query_input(text)
            result = service.query(start, end, config)
        except SubwayError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # path calculation / fare calculation failures
            print(f"Error: unexpected failure while computing the route ({exc})")
            continue

        try:
            rendered = export_report(result, fmt)
        except Exception as exc:
            print(f"Error: unable to format the result ({exc})")
            continue
        print(rendered)

        if output_file:
            try:
                _write_output(output_file, result, fmt, session)
                print(f"Result saved to {output_file}")
            except OSError as exc:
                print(f"Error: could not write output file '{output_file}' ({exc})")
    print("Goodbye.")


def main(argv=None):
    """Entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork.from_file()
    except Exception as exc:
        print(f"Error: unable to load subway data ({exc})", file=sys.stderr)
        return 1

    if args.check_data:
        report = network.check_data_integrity()
        print(report.render())
        return 0 if report.is_ok else 1

    preferred = []
    for raw_line in parse_line_preference(args.line_preference):
        canonical = network.resolve_line_name(raw_line)
        if canonical is None:
            print(f"Error: line preference '{raw_line}' does not exist in the dataset", file=sys.stderr)
            return 2
        preferred.append(canonical)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))

    service = RouteService(network)
    run_interactive(service, config, output_file=args.output_file, fmt=args.format)
    return 0
