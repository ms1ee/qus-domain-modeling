"""
Command-line interface for the Beijing Subway fare calculation system.

Runs an interactive loop where the user enters "Starting Station; Ending Station"
queries. Command-line arguments control output format, output file, query mode,
transfer limit, line preference and data checking.
"""

import argparse
import os
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import DataManager
from fare_calculator import Sum_money  # noqa: F401  (fare is computed inside the summary)
from network import SubwayNetwork
from path_report import build_path_summary, format_json_report, format_text_report
from pathfinding import VALID_MODES, PathfindingConfig, ShortestPath

EXIT_COMMANDS = ("quit", "exit", "q")


class QueryError(Exception):
    """Raised for any user-facing query error (format, station, logic, path, fare)."""


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra-based route planner).")
    parser.add_argument("--output_file", default=None,
                        help="Append query results to this file.")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of allowed transfers.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line name, e.g. \"Line 1\" (comma-separated for several).")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def parse_preferences(value):
    """Convert the --line_preference value into a list of line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_query(text):
    """
    Split a query of the form "Starting Station; Ending Station".

    Raises:
        QueryError: If the format is wrong.
    """
    message = "Input format incorrect, please use 'Starting Station; Ending Station' format"
    if text.count(";") != 1:
        raise QueryError(message)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise QueryError(message)
    return start, end


def answer_query(network, text, args):
    """
    Validate a query and compute the route summary.

    Args:
        network: SubwayNetwork instance.
        text: Raw query text entered by the user.
        args: Parsed command-line arguments.

    Returns:
        dict: Route summary (see path_report.build_path_summary).

    Raises:
        QueryError: For any validation, path or fare calculation problem.
    """
    start_raw, end_raw = parse_query(text)

    start = network.resolve_name(start_raw)
    if start is None:
        raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
    end = network.resolve_name(end_raw)
    if end is None:
        raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=parse_preferences(args.line_preference),
        )
        source_number = network.number_of(start)
        target_number = network.number_of(end)
        path_search = ShortestPath(network.graph, source_number, config)
        if not path_search.has_path_to(target_number):
            raise QueryError("No route found between these stations under the current constraints")
        vertices, edges = path_search.path_with_edges(target_number)
        transfer_count = path_search.get_transfer_count(target_number)
    except (ValueError, KeyError) as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    station_names = [network.name_of(number) for number in vertices]
    try:
        return build_path_summary(start, end, args.mode, station_names, edges, transfer_count)
    except (ValueError, TypeError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc


def render(summary, output_format):
    """Render a summary in the requested format."""
    if output_format == "json":
        return format_json_report(summary)
    return format_text_report(summary)


def export_result(content, path):
    """Append rendered content to the output file. Returns an error message or None."""
    try:
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(content + "\n")
        return None
    except OSError as exc:
        return f"Could not write output file '{path}': {exc}"


def format_integrity_report(report):
    """Render the data integrity report as text."""
    lines = ["=== Subway Data Integrity Check ==="]
    info = report.get("info", {})
    lines.append(f"Stations: {info.get('station_count', 0)}, "
                 f"connections: {info.get('connection_count', 0)}")
    lines.append(f"Errors: {len(report['errors'])}")
    for message in report["errors"]:
        lines.append(f"  [ERROR] {message}")
    lines.append(f"Warnings: {len(report['warnings'])}")
    for message in report["warnings"]:
        lines.append(f"  [WARN] {message}")
    lines.append("Result: PASSED" if report["ok"] else "Result: FAILED")
    return "\n".join(lines)


def run_check_data(data):
    """Run the integrity check and return the process exit code."""
    report = DataManager(data).check_integrity()
    print(format_integrity_report(report))
    return 0 if report["ok"] else 1


def run_interactive(network, args, input_func=input, output=print):
    """
    Run the continuous query loop until the user quits or input ends.

    Returns:
        int: Number of successful queries.
    """
    output("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station'"
           " (or 'quit' to exit).")
    successful = 0
    while True:
        try:
            text = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            output("")
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            summary = answer_query(network, text, args)
        except QueryError as exc:
            output(f"Error: {exc}")
            continue

        rendered = render(summary, args.format)
        output(rendered)
        successful += 1

        if args.output_file:
            error = export_result(rendered, args.output_file)
            if error:
                output(f"Error: {error}")
    return successful


def main(argv=None):
    """Entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: could not load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_check_data(data)

    try:
        network = SubwayNetwork(data)
    except (ValueError, KeyError) as exc:
        print(f"Error: subway network is invalid: {exc}", file=sys.stderr)
        return 1

    for line in parse_preferences(args.line_preference):
        if line not in network.lines():
            print(f"Warning: preferred line '{line}' does not exist in the network")

    run_interactive(network, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
