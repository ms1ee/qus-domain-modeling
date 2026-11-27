"""Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--format text|json] [--output_file PATH]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"]
                   [--check_data]

Enter queries as 'Starting Station; Ending Station'. Type 'quit' to exit.
"""

import argparse
import sys

from data_loader import DATA_FILE_PATH
from data_manager import DataIntegrityChecker, SubwayNetwork
from fare_calculator import FareCalculationError
from pathfinding import PathfindingConfig, VALID_MODES
from report import export_results, render
from route_planner import PathCalculationError, QueryValidationError, RoutePlanner

EXIT_COMMANDS = {"q", "quit", "exit"}
PROMPT = "Please enter 'Starting Station; Ending Station' (or 'quit' to exit): "


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", "--output-file", dest="output_file", default=None,
                        help="Export query results to this file")
    parser.add_argument("--format", dest="format", choices=["text", "json"], default="text",
                        help="Output format")
    parser.add_argument("--mode", dest="mode", choices=list(VALID_MODES),
                        default="shortest_distance", help="Path query mode")
    parser.add_argument("--max_transfers", "--max-transfers", dest="max_transfers",
                        type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", "--line-preference", dest="line_preference",
                        default=None, help="Preferred line(s), comma separated")
    parser.add_argument("--check_data", "--check-data", dest="check_data",
                        action="store_true", help="Run data integrity check and exit")
    parser.add_argument("--data_file", dest="data_file", default=DATA_FILE_PATH,
                        help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def build_config(args, network, out):
    preferred = []
    if args.line_preference:
        for raw in args.line_preference.replace("，", ",").split(","):
            raw = raw.strip()
            if not raw:
                continue
            line = network.resolve_line(raw)
            if line is None:
                print("Warning: line '{}' does not exist, preference ignored".format(raw),
                      file=out)
            else:
                preferred.append(line)
    return PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                             preferred_lines=preferred)


def run_interactive(planner, args, inp=None, out=None):
    inp = inp if inp is not None else sys.stdin
    out = out if out is not None else sys.stdout
    results = []
    while True:
        out.write(PROMPT)
        out.flush()
        try:
            line = inp.readline()
        except KeyboardInterrupt:
            out.write("\n")
            break
        if not line:
            out.write("\n")
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            result = planner.query(text)
        except QueryValidationError as exc:
            print("Error: {}".format(exc), file=out)
            continue
        except PathCalculationError as exc:
            print("Path calculation error: {}".format(exc), file=out)
            continue
        except FareCalculationError as exc:
            print("Fare calculation error: {}".format(exc), file=out)
            continue
        except Exception as exc:  # defensive: keep the CLI alive
            print("Unexpected error: {}".format(exc), file=out)
            continue
        print(render(result, args.format), file=out)
        results.append(result)
        if args.output_file:
            try:
                export_results(results, args.output_file, args.format)
                print("Result exported to {}".format(args.output_file), file=out)
            except OSError as exc:
                print("Error: cannot write output file: {}".format(exc), file=out)
    print("Goodbye!", file=out)
    return results


def main(argv=None):
    args = parse_args(argv)
    out = sys.stdout
    try:
        network = SubwayNetwork(args.data_file)
    except (OSError, ValueError) as exc:
        print("Error: failed to load subway data: {}".format(exc), file=out)
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(network)
        checker.run()
        print(checker.format_report(), file=out)
        return 0

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=out)
        return 1

    config = build_config(args, network, out)
    planner = RoutePlanner(network, config)
    print("Beijing Subway Fare Calculation System ({} stations loaded)".format(
        len(network.station_to_number)), file=out)
    run_interactive(planner, args, sys.stdin, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
