"""
Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python main.py
    python main.py --mode least_transfer --format json --output_file out.json
    python main.py --check_data
"""

import argparse
import re
import sys

try:
    from data_manager import SubwayNetwork
    from pathfinding import PathfindingConfig, VALID_MODES
    from route_service import (plan_route, StationNotFoundError, PathNotFoundError,
                               PathCalculationError, FareError)
    from report import render, export_routes
except ImportError:  # pragma: no cover
    from .data_manager import SubwayNetwork
    from .pathfinding import PathfindingConfig, VALID_MODES
    from .route_service import (plan_route, StationNotFoundError, PathNotFoundError,
                                PathCalculationError, FareError)
    from .report import render, export_routes

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATORS = r"[;；,，]"
EXIT_COMMANDS = {"q", "quit", "exit"}


class InputFormatError(Exception):
    pass


class QueryValidationError(Exception):
    pass


def parse_query_input(text):
    """Split 'Start; End' input into two raw station names."""
    if text is None:
        raise InputFormatError(FORMAT_ERROR)
    parts = re.split(SEPARATORS, text.strip())
    if len(parts) != 2:
        raise InputFormatError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError(FORMAT_ERROR)
    return start, end


def validate_query(network, start_raw, end_raw):
    """Return canonical (start, end) or raise QueryValidationError."""
    start = network.resolve_station(start_raw)
    if start is None:
        msg = f"Starting station '{start_raw}' does not exist, please check the station name"
        sug = network.suggest_stations(start_raw)
        if sug:
            msg += f" (did you mean: {', '.join(sug)}?)"
        raise QueryValidationError(msg)
    end = network.resolve_station(end_raw)
    if end is None:
        msg = f"Ending station '{end_raw}' does not exist, please check the station name"
        sug = network.suggest_stations(end_raw)
        if sug:
            msg += f" (did you mean: {', '.join(sug)}?)"
        raise QueryValidationError(msg)
    if start == end:
        raise QueryValidationError("Starting station cannot be the same as the ending station")
    return start, end


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance", help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=None, help="Alternative subway data file")
    p.add_argument("--start", default=None, help="Starting station (single query mode)")
    p.add_argument("--end", default=None, help="Ending station (single query mode)")
    return p


def run_query(network, config, text, fmt):
    """Process one input line; return (Route or None, message to print)."""
    start_raw, end_raw = parse_query_input(text)
    start, end = validate_query(network, start_raw, end_raw)
    route = plan_route(network, start, end, config)
    return route, render(route, fmt)


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        network = SubwayNetwork(data_file=args.data_file)
    except FileNotFoundError as exc:
        print(f"Error: data file not found: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = network.check_data()
        print(report.format_text())
        return 0 if report.is_valid else 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    preferred = []
    if args.line_preference:
        for raw in re.split(r"[,，;；]", args.line_preference):
            raw = raw.strip()
            if not raw:
                continue
            line = network.resolve_line(raw)
            if line is None:
                print(f"Warning: preferred line '{raw}' not found in network data, ignored")
            else:
                preferred.append(line)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=preferred)

    routes = []

    def handle(text):
        try:
            route, output = run_query(network, config, text, args.format)
        except (InputFormatError, QueryValidationError, StationNotFoundError) as exc:
            print(f"Error: {exc}")
            return False
        except PathNotFoundError as exc:
            print(f"Error: {exc}")
            return False
        except PathCalculationError as exc:
            print(f"Path calculation error: {exc}")
            return False
        except FareError as exc:
            print(f"Fare calculation error: {exc}")
            return False
        except Exception as exc:  # last-resort safety net
            print(f"Unexpected error: {exc}")
            return False
        print(output)
        routes.append(route)
        if args.output_file:
            try:
                export_routes(routes, args.output_file, args.format)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Error: cannot write output file '{args.output_file}': {exc}")
        return True

    if args.start or args.end:
        if not (args.start and args.end):
            print(f"Error: {FORMAT_ERROR}")
            return 2
        return 0 if handle(f"{args.start};{args.end}") else 1

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, 'help' for help, 'quit' to exit.")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd = text.strip()
        if not cmd:
            continue
        if cmd.lower() in EXIT_COMMANDS:
            break
        if cmd.lower() == "help":
            print("Input format: Starting Station; Ending Station  (separators: ';' or ',')")
            print("Commands: help, lines, quit")
            continue
        if cmd.lower() == "lines":
            print(", ".join(str(l) for l in network.all_lines()))
            continue
        handle(cmd)
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
