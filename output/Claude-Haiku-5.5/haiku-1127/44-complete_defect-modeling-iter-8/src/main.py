"""Command-line entry point of the Beijing Subway fare calculation system.

Run either as ``python src/main.py`` or ``python -m src.main`` from the project root.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from data_loader import DATA_FILE_PATH  # noqa: E402
from data_manager import DataManager  # noqa: E402
from integrity import DataIntegrityChecker  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES  # noqa: E402
from report import SUPPORTED_FORMATS, build_report, export_report, make_query  # noqa: E402
from route import build_route  # noqa: E402

PROMPT = "Enter 'Starting Station; Ending Station' (or 'quit' to exit): "
FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = ("quit", "exit", "q")


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file (appended)")
    parser.add_argument("--format", choices=list(SUPPORTED_FORMATS), default="text",
                        help="output format: text or json")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="path query mode")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def parse_query_text(text):
    """Split 'Starting Station; Ending Station' into two stripped names.

    Returns:
        (start, end) tuple, or None if the format is invalid.
    """
    normalized = text.replace("\uff1b", ";")  # accept full-width semicolon too
    parts = normalized.split(";")
    if len(parts) != 2:
        return None
    start = parts[0].strip()
    end = parts[1].strip()
    if not start or not end:
        return None
    return start, end


def build_config(args):
    """Create the PathfindingConfig from command-line options."""
    preferred = [args.line_preference] if args.line_preference else []
    return PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )


def compute_path(manager, start, end, config):
    """Run Dijkstra between two stations. Returns (numbers, edges) or None if unreachable."""
    source = manager.station_numbers[start]
    target = manager.station_numbers[end]
    shortest = ShortestPath(manager.graph, source, config)
    if not shortest.has_path_to(target):
        return None
    return shortest.path_with_edges(target)


def process_query(manager, text, args, config, out):
    """Handle one 'Start; End' query. Returns True on success."""
    parsed = parse_query_text(text)
    if parsed is None:
        out.write(FORMAT_ERROR_MESSAGE + "\n")
        return False
    raw_start, raw_end = parsed

    start = manager.standardize_station_name(raw_start)
    if start is None:
        out.write(f"Starting station '{raw_start}' does not exist, please check the station name\n")
        return False
    end = manager.standardize_station_name(raw_end)
    if end is None:
        out.write(f"Ending station '{raw_end}' does not exist, please check the station name\n")
        return False
    if start == end:
        out.write("Starting station cannot be the same as the ending station\n")
        return False

    try:
        path = compute_path(manager, start, end, config)
    except Exception as exc:  # defensive: any search failure is reported, not fatal
        out.write(f"Path calculation error: {exc}\n")
        return False
    if path is None:
        out.write(f"No route found from '{start}' to '{end}' with the current settings\n")
        return False

    numbers, edges = path
    try:
        route = build_route(numbers, edges, manager.number_to_name)
    except Exception as exc:
        out.write(f"Fare calculation error: {exc}\n")
        return False

    query = make_query(start, end, config.mode, config.max_transfers,
                       config.preferred_lines[0] if config.preferred_lines else None)
    try:
        report = build_report(route, query, args.format, args.output_file)
    except Exception as exc:
        out.write(f"Report generation error: {exc}\n")
        return False

    out.write(report.content + "\n")
    if args.output_file:
        try:
            export_report(report)
            out.write(f"Result exported to {args.output_file}\n")
        except OSError as exc:
            out.write(f"Failed to export result: {exc}\n")
            return False
    return True


def run_interactive(manager, args, config, input_func, out):
    """Continuous query loop: keeps prompting until the user quits or input ends."""
    out.write("Beijing Subway fare calculator. Type 'quit' to exit.\n")
    while True:
        try:
            text = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            out.write("\n")
            break
        text = (text or "").strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        process_query(manager, text, args, config, out)
    out.write("Goodbye.\n")


def main(argv=None, input_func=input, out=None):
    """Program entry point. Returns the process exit code."""
    if out is None:
        out = sys.stdout
    args = parse_args(argv)

    try:
        manager = DataManager(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        out.write(f"Failed to load subway data: {exc}\n")
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(manager).run()
        out.write(checker.format_report())
        return 0 if checker.passed else 1

    if args.line_preference and args.line_preference not in manager.lines():
        sys.stderr.write(f"Warning: line '{args.line_preference}' is not a known line\n")

    config = build_config(args)
    run_interactive(manager, args, config, input_func, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
