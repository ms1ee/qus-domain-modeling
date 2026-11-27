"""Command line interface."""
import argparse
import sys

from data_manager import DataManager
from pathfinding import PathfindingConfig, ShortestPath
import report

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = {"q", "quit", "exit", "退出"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


def parse_input(text):
    """Return (start, end) or raise ValueError with a user message."""
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise ValueError(FORMAT_ERR)
    a, b = parts[0].strip(), parts[1].strip()
    if not a or not b:
        raise ValueError(FORMAT_ERR)
    return a, b


def run_query(dm, line, args):
    start, end = parse_input(line)
    if not dm.has_station(start):
        raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
    if not dm.has_station(end):
        raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    if args.line_preference:
        resolved = dm.resolve_line(args.line_preference)
        if resolved is None:
            print("Warning: line preference '%s' not recognized, ignored" % args.line_preference)
        else:
            cfg.preferred_lines = [resolved]
    try:
        sp = ShortestPath(dm.graph, dm.station_to_number[start], cfg)
        if not sp.has_path_to(dm.station_to_number[end]):
            raise ValueError("No route found between '%s' and '%s' under the given constraints"
                             % (start, end))
    except ValueError:
        raise
    except Exception as ex:
        raise ValueError("Path calculation failed: %s" % ex)
    try:
        result = report.build_result(dm, start, end, sp)
    except ValueError:
        raise
    except Exception as ex:
        raise ValueError("Fare calculation failed: %s" % ex)
    return report.to_json(result) if args.format == "json" else report.to_text(result)


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = dm.check_integrity()
        for m in msgs:
            print(m)
        print("Data check passed" if ok else "Data check FAILED")
        return 0 if ok else 1
    out = None
    if args.output_file:
        try:
            out = open(args.output_file, "w", encoding="utf-8")
        except OSError as ex:
            print("Cannot open output file: %s" % ex)
            return 1
    print("Beijing Subway fare query. Enter 'Starting Station; Ending Station' (q to quit).")
    try:
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if line.strip().lower() in EXIT_WORDS:
                break
            if not line.strip():
                continue
            try:
                text = run_query(dm, line, args)
            except ValueError as ex:
                print(ex)
                continue
            except Exception as ex:
                print("Unexpected error: %s" % ex)
                continue
            print(text)
            if out:
                out.write(text + "\n\n")
                out.flush()
    finally:
        if out:
            out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
