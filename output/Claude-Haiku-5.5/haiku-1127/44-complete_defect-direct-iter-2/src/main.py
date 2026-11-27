"""Command-line entry point for the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --mode least_transfer --format json
    python src/main.py --max_transfers 2 --line_preference "Line 1,Line 2"
    python src/main.py --output_file results.txt
    python src/main.py --check_data
"""

import argparse
import json
import os
import sys

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from subway_network import SubwayNetwork  # noqa: E402
from pathfinding import MODES, PathfindingConfig, ShortestPath  # noqa: E402
from path_report import build_report, format_json, format_text  # noqa: E402

EXIT_COMMANDS = {"q", "quit", "exit"}
QUERY_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR = "-" * 60


class QueryError(Exception):
    """A user-facing error raised while processing one query."""


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two raw station names."""
    normalized = text.replace("\uff1b", ";")  # accept full-width semicolon too
    parts = normalized.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryError(QUERY_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def resolve_station(network, raw, role):
    """Standardize a station name or raise a user-facing error."""
    name = network.standardize_station_name(raw)
    if name is None:
        raise QueryError(f"{role} station '{raw}' does not exist, please check the station name")
    return name


def run_query(network, start_raw, end_raw, config):
    """Compute the route and report for one query.

    Returns:
        The report dictionary produced by path_report.build_report.

    Raises:
        QueryError: for any user-facing failure.
    """
    start = resolve_station(network, start_raw, "Starting")
    end = resolve_station(network, end_raw, "Ending")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        search = ShortestPath(network.graph, network.get_number(start), config)
        target = network.get_number(end)
        if not search.has_path_to(target):
            raise QueryError(
                f"No route found from '{start}' to '{end}' under the current constraints")
        node_numbers, edges = search.path_with_edges(target)
        transfer_count = search.get_transfer_count(target)
    except QueryError:
        raise
    except Exception as exc:  # defensive: any unexpected path error
        raise QueryError(f"Path calculation failed: {exc}") from exc

    names = [network.get_name(n) for n in node_numbers]
    try:
        return build_report(start, end, config, names, edges, transfer_count)
    except Exception as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc


def render(report, fmt):
    """Render a report in the requested output format."""
    return format_json(report) if fmt == "json" else format_text(report)


def save_output(path, fmt, session):
    """Persist the session results to ``path``.

    Text results are appended; JSON results are rewritten as a JSON array
    containing every result of the current session.

    Returns:
        (True, None) on success, or (False, error message) on failure.
    """
    try:
        if fmt == "json":
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(session, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        else:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(format_text(session[-1]))
                fh.write("\n" + SEPARATOR + "\n")
        return True, None
    except OSError as exc:
        return False, str(exc)


def parse_preferences(value):
    """Turn a comma separated --line_preference value into a list of lines."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def run_data_check(network):
    """Print the data integrity report and return an exit code."""
    problems = network.check_integrity()
    print(f"Stations: {network.station_count()}  "
          f"Connections: {len(network.connections)}  "
          f"Lines: {len(network.all_line_names())}")
    if not problems:
        print("Data integrity check passed: no problems found.")
        return 0
    for problem in problems:
        print(problem)
    errors = [p for p in problems if p.startswith("ERROR")]
    print(f"Data integrity check finished: {len(errors)} error(s), "
          f"{len(problems) - len(errors)} warning(s).")
    return 1 if errors else 0


def run_interactive(network, args, preferred):
    """Continuous query loop: keeps asking until the user quits."""
    session = []
    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit).")
    while True:
        try:
            raw_line = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw_line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            start_raw, end_raw = parse_query(text)
            config = PathfindingConfig(mode=args.mode,
                                       max_transfers=args.max_transfers,
                                       preferred_lines=preferred)
            report = run_query(network, start_raw, end_raw, config)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # keep the session alive on unexpected errors
            print(f"Error: unexpected failure while processing the query: {exc}")
            continue

        print(render(report, args.format))
        if args.output_file:
            session.append(report)
            ok, message = save_output(args.output_file, args.format, session)
            if ok:
                print(f"Result saved to {args.output_file}")
            else:
                print(f"Error: could not write output file: {message}")
    print("Goodbye.")
    return 0


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. \"Line 1\" or \"Line 1,Line 2\"")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except Exception as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_data_check(network)

    preferred = parse_preferences(args.line_preference)
    known_lines = set(network.all_line_names())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line preference '{line}' is not a known line", file=sys.stderr)

    return run_interactive(network, args, preferred)


if __name__ == "__main__":
    sys.exit(main())
