"""CLI entry point for the Beijing subway fare system."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from data_manager import build_network, check_data  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath  # noqa: E402
import report  # noqa: E402

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


def parse_query(text):
    """Return (start, end, error)."""
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None, FORMAT_ERR
    return parts[0], parts[1], None


def query(start, end, graph, s2n, n2s, config, fmt):
    if start not in s2n:
        return None, "Starting station '%s' does not exist, please check the station name" % start
    if end not in s2n:
        return None, "Ending station '%s' does not exist, please check the station name" % end
    if start == end:
        return None, "Starting station cannot be the same as the ending station"
    try:
        sp = ShortestPath(graph, s2n[start], config)
        nodes, edges = sp.path_with_edges(s2n[end])
        if not nodes:
            return None, "No route found between '%s' and '%s' (check transfer limit)" % (start, end)
        dist = sp.dist_to[s2n[end]]
        transfers = sp.get_transfer_count(s2n[end])
    except Exception as ex:
        return None, "Path calculation error: %s" % ex
    try:
        summary = report.build_summary(start, end, [n2s[n] for n in nodes], edges, dist, transfers)
    except Exception as ex:
        return None, "Fare calculation error: %s" % ex
    return (report.to_json(summary) if fmt == "json" else report.to_text(summary)), None


def main(argv=None):
    args = parse_args(argv)
    data = load_subway_data(DATA_FILE_PATH)
    if args.check_data:
        problems, summary = check_data(data)
        print("\n".join(summary))
        if problems:
            print("Problems found:")
            for pr in problems:
                print("  - " + pr)
        else:
            print("Data check passed.")
        return 0
    graph, s2n, n2s = build_network(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [args.line_preference]
    results = []
    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        start, end, err = parse_query(line)
        if err:
            print(err)
            continue
        out, err = query(start, end, graph, s2n, n2s, config, args.format)
        if err:
            print(err)
            continue
        print(out)
        results.append(out)
        if args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(results) + "\n")
            except OSError as ex:
                print("Cannot write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
