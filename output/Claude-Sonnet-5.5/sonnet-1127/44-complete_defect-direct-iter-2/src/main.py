"""CLI for the Beijing Subway fare calculation system."""
import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time
import data_manager


def build_graph(data):
    station_to_number = {}
    number_to_station = {}
    g = Graph()
    for s in data["stations"]:
        if s["name"] not in station_to_number:
            n = len(station_to_number)
            station_to_number[s["name"]] = n
            number_to_station[n] = s["name"]
            g.add_node(n)
        g.set_station_lines(s["name"], s.get("lines", []))
    for c in data["connections"]:
        if c["source"] in station_to_number and c["dest"] in station_to_number:
            g.add_edge(Edge(station_to_number[c["source"]], station_to_number[c["dest"]],
                            c["distance"], c["line"]))
    return g, station_to_number, number_to_station


def format_distance(m):
    return "%d m" % m if m < 1000 else "%.2f km (%d m)" % (m / 1000.0, m)


def query(g, s2n, n2s, start, end, config):
    src, dst = s2n[start], s2n[end]
    try:
        sp = ShortestPath(g, src, config)
        nodes, edges = sp.path_with_edges(dst)
    except Exception as e:
        raise RuntimeError("Path calculation failed: %s" % e)
    if not nodes:
        raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
    dist = sp.dist_to[dst]
    transfers = sp.get_transfer_count(dst)
    try:
        fare = Sum_money(dist)
        minutes = calculate_estimated_time(dist, transfers)
    except Exception as e:
        raise RuntimeError("Fare calculation failed: %s" % e)
    segments = []
    transfer_stations = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["stations"].append(n2s[e.dest])
        else:
            if segments:
                transfer_stations.append(n2s[e.source])
            segments.append({"line": e.line, "stations": [n2s[e.source], n2s[e.dest]]})
    lines = []
    for sg in segments:
        if sg["line"] not in lines:
            lines.append(sg["line"])
    return {
        "query": {"start": start, "end": end, "mode": config.mode},
        "path": [n2s[n] for n in nodes],
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(minutes, 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"]))]
    for sg in r["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (sg["line"], sg["stations"][0],
                                                   sg["stations"][-1], len(sg["stations"]) - 1))
    out.append("Total distance: %s" % format_distance(r["distance_m"]))
    out.append("Transfers: %d" % r["transfer_count"])
    if r["transfer_stations"]:
        out.append("Transfer stations: %s" % ", ".join(r["transfer_stations"]))
    out.append("Lines: %s" % ", ".join(r["lines"]))
    out.append("Estimated time: %.0f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return format_text(r)


def parse_input(line):
    line = line.replace("；", ";")
    parts = line.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    return parts[0].strip(), parts[1].strip()


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int)
    p.add_argument("--line_preference")
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except Exception as e:
        print("Failed to load data: %s" % e)
        return 1
    if args.check_data:
        problems = data_manager.check_data(data)
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for x in problems:
                print(" -", x)
            return 1
        print("Data check passed: %d stations, %d connections" %
              (len(data["stations"]), len(data["connections"])))
        return 0

    g, s2n, n2s = build_graph(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []

    print("Beijing Subway Fare Calculator. Input 'Starting Station; Ending Station' (q to quit).")
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
        parsed = parse_input(line)
        if not parsed:
            print("Input format incorrect, please use 'Starting Station; Ending Station' format")
            continue
        start, end = parsed
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
            r = query(g, s2n, n2s, start, end, config)
        except RuntimeError as e:
            print(e)
            continue
        text = render(r, args.format)
        print(text)
        if args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(text + "\n")
                print("Result saved to %s" % args.output_file)
            except OSError as e:
                print("Failed to write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
