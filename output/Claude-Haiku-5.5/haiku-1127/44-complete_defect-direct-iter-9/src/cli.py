"""Command-line interface: argument parsing, continuous query loop and error handling."""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import DataManager
from models import NetworkBuildError, SubwayNetwork
from pathfinding import SHORTEST_DISTANCE, VALID_MODES
from query_service import (
    QueryError,
    parse_line_preference,
    parse_query,
    resolve_station,
    run_query,
)
from visualizer import render, summary_to_dict, write_output_file

EXIT_WORDS = {"quit", "exit", "q"}
PROMPT = "Enter query ('Starting Station; Ending Station', or 'quit' to exit): "


def build_parser():
    """Create the argument parser for the command-line interface."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation system (Dijkstra-based route search).",
    )
    parser.add_argument("--output_file", default=None,
                        help="write query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def _write_result(args, summary, rendered, session):
    """Write one query result to the output file.

    In text mode results are appended to the file. In JSON mode the file holds
    a JSON array containing every result of this session.

    Returns:
        bool: True if the output file has been started during this session.
    """
    if args.format == "json":
        session["json_results"].append(summary_to_dict(summary))
        content = json.dumps(session["json_results"], ensure_ascii=False, indent=2) + "\n"
        write_output_file(args.output_file, content, append=False)
        return True
    content = rendered + "\n\n"
    write_output_file(args.output_file, content, append=session["output_started"])
    return True


def main(argv=None):
    """Entry point of the CLI.

    Args:
        argv: Optional list of command-line arguments (defaults to sys.argv[1:]).

    Returns:
        int: Process exit status.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork.from_data(data)
    except (DataLoadError, NetworkBuildError) as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = DataManager(data).check_integrity()
        print(report.format())
        return 0 if report.passed else 1

    try:
        preferred_lines = parse_line_preference(args.line_preference, network.lines)
    except QueryError as exc:
        print(f"Error: {exc}")
        return 2

    print("Beijing Subway Fare Calculation System")
    print(f"Stations: {len(network.station_to_number)}, connections: {network.graph.num_edges}")
    for warning in network.warnings:
        print(f"Data warning: {warning}")

    session = {"output_started": False, "json_results": []}
    while True:
        try:
            raw = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            start_raw, end_raw = parse_query(text)
            start = resolve_station(network, start_raw, "Starting")
            end = resolve_station(network, end_raw, "Ending")
            summary = run_query(network, start, end, args.mode, args.max_transfers, preferred_lines)
            rendered = render(summary, args.format)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # unexpected failure must not terminate the session
            print(f"Error: unexpected failure while processing the query: {exc}")
            continue

        print(rendered)
        if args.output_file:
            try:
                session["output_started"] = _write_result(args, summary, rendered, session)
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}")
    return 0
