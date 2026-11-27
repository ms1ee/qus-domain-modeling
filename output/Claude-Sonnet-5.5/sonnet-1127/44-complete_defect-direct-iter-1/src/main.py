"""CLI for the Beijing Subway fare calculation system."""
import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import build_graph, check_data
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


def format_distance(m):
    return "%d m" % m if m < 1000 else "%.2f km" % (m / 1000.0)


def compute(graph, s2n, n2s, start, end, config):
    sp = ShortestPath(graph, s2n[start], config)
    nodes, edges = sp.path_with_edges(s2n[end])
    if not nodes:
        raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
    dist = sp.dist_to[s2n[end]]
    transfers = sp.get_transfer_count(s2n[end])
    try:
        fare = Sum_money(dist)
    except Exception as e:
        raise RuntimeError("Fare calculation failed: %s" % e)
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = n2s[e.dest]
            segments[-1]["distance"] += e.distance
        else:
            if segments:
                transfer_stations.append(n2s[e.source])
            segments.append({"line": e.line, "from": n2s[e.source],
                             "to": n2s[e.dest], "distance": e.distance})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": start, "end": end, "mode": config.mode},
        "path": [n2s[n] for n in nodes],
        "segments": segments,
        "transfer_stations": transfer_stations,
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(calculate_estimated_time(dist, transfers), 1),
        "transfer_count": transfers,
        "lines": lines,
    }


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"]))]
    for s in r["segments"]:
        out.append("  %s: %s -> %s (%s)" % (s["line"], s["from"], s["to"], format_distance(s["distance"])))
    if r["transfer_stations"]:
        out.append("Transfers at: %s" % ", ".join(r["transfer_stations"]))
    out.append("Lines: %s" % ", ".join(r["lines"]))
    out.append("Total distance: %s" % format_distance(r["distance_m"]))
    out.append("Transfers: %d" % r["transfer_count"])
    out.append("Estimated time: %.0f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int)
    p.add_argument("--line_preference")
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


def parse_query(text):
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts


def main(argv=None):
    args = parse_args(argv)
    data = load_subway_data(DATA_FILE_PATH)
    if args.check_data:
        problems = check_data(data)
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for p in problems:
                print(" - " + p)
            return 1
        print("Data check passed.")
        return 0
    graph, s2n, n2s = build_graph(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if line.lower() in ("q", "quit", "exit"):
            break
        if not line:
            continue
        q = parse_query(line)
        if q is None:
            print("Input format incorrect, please use 'Starting Station; Ending Station' format")
            continue
        start, end = q
        if start not in s2n:
            print("Starting station '%s' does not exist, please check the station name" % start)
            continue
        if end not in s2n:
            print("Ending station '%s' does not exist, please check the station name" % end)
            continue
        if start == end:
            print("Starting station cannot be the same as the ending station")
            continue
        try:
            r = compute(graph, s2n, n2s, start, end, config)
        except Exception as e:
            print("Error: %s" % e)
            continue
        text = json.dumps(r, ensure_ascii=False, indent=2) if args.format == "json" else format_text(r)
        print(text)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n\n")
            except OSError as e:
                print("Could not write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
