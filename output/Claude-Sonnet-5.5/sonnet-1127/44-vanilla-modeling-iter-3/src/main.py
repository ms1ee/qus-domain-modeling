"""Command-line interface for the Beijing Subway fare system."""
import argparse
import sys

from data_manager import DataManager
from pathfinding import PathfindingConfig, ShortestPath
from report import ReportExporter, build_summary

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


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


def validate(dm, text):
    """Return (start, end, error)."""
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None, FORMAT_ERR
    s, e = parts
    if not dm.has_station(s):
        return None, None, "Starting station '%s' does not exist, please check the station name" % s
    if not dm.has_station(e):
        return None, None, "Ending station '%s' does not exist, please check the station name" % e
    if s == e:
        return None, None, "Starting station cannot be the same as the ending station"
    return s, e, None


def run_query(dm, start, end, config):
    try:
        sp = ShortestPath(dm.graph, dm.station_to_number[start], config)
        target = dm.station_to_number[end]
        nodes, edges = sp.path_with_edges(target)
    except Exception as ex:  # path calculation failure
        return None, "Path calculation failed: %s" % ex
    if not nodes:
        return None, "No route found between '%s' and '%s' under the given constraints" % (start, end)
    try:
        return build_summary(dm, start, end, nodes, edges), None
    except Exception as ex:  # fare failure
        return None, "Fare calculation failed: %s" % ex


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as ex:
        print("Failed to load data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("Data check passed." if ok else "Data check found issues:")
        for m in msgs:
            print(" - " + m)
        return 0 if ok else 1
    config = PathfindingConfig(args.mode, args.max_transfers,
                               [args.line_preference] if args.line_preference else [])
    exporter = ReportExporter(args.format, args.output_file)
    print("Enter 'Starting Station; Ending Station' (or 'exit' to quit):")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if line.lower() in ("exit", "quit", "q"):
            break
        if not line:
            continue
        s, e, err = validate(dm, line)
        if err:
            print(err)
            continue
        summary, err = run_query(dm, s, e, config)
        if err:
            print(err)
            continue
        print(exporter.export(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
