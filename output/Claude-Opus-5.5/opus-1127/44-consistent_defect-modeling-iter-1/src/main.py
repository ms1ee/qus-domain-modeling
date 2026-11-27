"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import json
import re
import sys

try:
    from data_loader import DATA_FILE_PATH
    from network import SubwayNetwork, check_data_integrity
    from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES
    from report import build_route, route_to_text, route_to_dict
except ImportError:  # pragma: no cover
    from .data_loader import DATA_FILE_PATH
    from .network import SubwayNetwork, check_data_integrity
    from .pathfinding import PathfindingConfig, ShortestPath, VALID_MODES
    from .report import build_route, route_to_text, route_to_dict

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"q", "quit", "exit"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None, help="export results to file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None,
                   help="preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be non-negative")
    return args


def parse_query(text):
    """Split input into (start, end); raises ValueError on bad format."""
    parts = [x.strip() for x in re.split(r"[;,；，]", text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERROR)
    return parts[0], parts[1]


def process_query(network, text, config):
    """Process one query line; returns (route, error message)."""
    try:
        start_raw, end_raw = parse_query(text)
    except ValueError as exc:
        return None, str(exc)
    start = network.find_station(start_raw)
    if start is None:
        return None, "Starting station '%s' does not exist, please check the station name" % start_raw
    end = network.find_station(end_raw)
    if end is None:
        return None, "Ending station '%s' does not exist, please check the station name" % end_raw
    if start == end:
        return None, "Starting station cannot be the same as the ending station"
    try:
        sp = ShortestPath(network.graph_obj, network.station_to_number[start], config)
    except Exception as exc:  # path calculation exception
        return None, "Path calculation error: %s" % exc
    try:
        route = build_route(network, sp, start, end, config.mode)
    except ValueError as exc:  # fare calculation exception
        return None, "Fare calculation error: %s" % exc
    except Exception as exc:
        return None, "Path calculation error: %s" % exc
    if route is None:
        return None, "No route found from '%s' to '%s'" % (start, end)
    return route, None


def run_check(network, out=sys.stdout):
    result = check_data_integrity(network)
    print("Data integrity check:", file=out)
    print("  Station coverage: %s" % ("OK" if result.station_coverage_valid else "FAILED"), file=out)
    print("  Connection integrity: %s" % ("OK" if result.connection_integrity_valid else "FAILED"), file=out)
    print("  Distance accuracy: %s" % ("OK" if result.distance_accuracy_valid else "FAILED"), file=out)
    for m in result.messages:
        print("  - " + m, file=out)
    return 0 if result.is_valid else 1


def _write_output(path, fmt, results):
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            json.dump(results, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(results) + "\n")


def main(argv=None, stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    args = parse_args(argv)
    try:
        network = SubwayNetwork(data_source=args.data_file)
    except (OSError, ValueError) as exc:
        print("Failed to load subway data: %s" % exc, file=stdout)
        return 1
    if args.check_data:
        return run_check(network, stdout)

    preferred = [x.strip() for x in (args.line_preference or "").split(",") if x.strip()]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)
    results = []
    print("Beijing Subway Fare Calculator (enter 'q' to quit)", file=stdout)
    while True:
        print("Enter 'Starting Station; Ending Station': ", end="", file=stdout)
        stdout.flush()
        line = stdin.readline()
        if not line:
            print("", file=stdout)
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in QUIT_WORDS:
            break
        route, error = process_query(network, text, config)
        if error:
            print(error, file=stdout)
            continue
        if args.format == "json":
            data = route_to_dict(route)
            print(json.dumps(data, ensure_ascii=False, indent=2), file=stdout)
            results.append(data)
        else:
            txt = route_to_text(route)
            print(txt, file=stdout)
            results.append(txt)
        if args.output_file:
            try:
                _write_output(args.output_file, args.format, results)
            except OSError as exc:
                print("Failed to write output file: %s" % exc, file=stdout)
    print("Goodbye!", file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
