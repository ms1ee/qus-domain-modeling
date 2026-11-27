"""CLI entry point for the Beijing subway fare calculator."""
import argparse
import sys

from data_manager import SubwayNetwork
from pathfinding import ShortestPath, PathfindingConfig, INF
import report

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


def validate(net, text):
    """Return (start, end, error)."""
    parts = text.replace("；", ";").split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None, None, FORMAT_ERR
    a, b = parts[0].strip(), parts[1].strip()
    if a not in net.station_to_number:
        return None, None, "Starting station '%s' does not exist, please check the station name" % a
    if b not in net.station_to_number:
        return None, None, "Ending station '%s' does not exist, please check the station name" % b
    if a == b:
        return None, None, "Starting station cannot be the same as the ending station"
    return a, b, None


def query(net, a, b, args):
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    cfg.preferred_lines = [args.line_preference] if args.line_preference else []
    try:
        sp = ShortestPath(net.graph, net.station_to_number[a], cfg)
        t = net.station_to_number[b]
        if sp.dist_to.get(t, INF) == INF:
            return None, "No route found between '%s' and '%s' under the given constraints" % (a, b)
        nodes, edges = sp.path_with_edges(t)
        transfers = sp.get_transfer_count(t)
        dist = sum(e.weight for e in edges)
    except Exception as ex:
        return None, "Path calculation error: %s" % ex
    try:
        summary = report.build_summary(net, a, b, nodes, edges, dist, transfers)
    except Exception as ex:
        return None, "Fare calculation error: %s" % ex
    return summary, None


def main(argv=None):
    args = parse_args(argv)
    try:
        net = SubwayNetwork()
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = net.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1
    first = True
    print("Enter 'Starting Station; Ending Station' (or 'exit' to quit)")
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
        a, b, err = validate(net, line)
        if err:
            print(err)
            continue
        summary, err = query(net, a, b, args)
        if err:
            print(err)
            continue
        out = report.to_json(summary) if args.format == "json" else report.to_text(summary)
        print(out)
        if args.output_file:
            try:
                with open(args.output_file, "w" if first else "a", encoding="utf-8") as f:
                    f.write(out + "\n")
                first = False
            except OSError as ex:
                print("Cannot write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
