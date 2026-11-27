"""CLI for the Beijing Subway fare calculator."""
import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time
import data_manager

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


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


def parse_input(text):
    parts = [p.strip() for p in re.split(r"[;；,，]", text) if p.strip()]
    if len(parts) != 2 or re.search(r"[;；,，].*[;；,，].*[;；,，]", text):
        return None
    return parts


def resolve(name, names):
    if name in names:
        return name, False
    m = difflib.get_close_matches(name, names, n=1, cutoff=0.5)
    if m:
        return m[0], True
    return None, False


def segments(edges, number_to_station):
    segs = []
    for e in edges:
        if segs and segs[-1]["line"] == e.line:
            segs[-1]["to"] = number_to_station[e.dest]
            segs[-1]["distance"] += e.distance
            segs[-1]["stations"] += 1
        else:
            segs.append({"line": e.line, "from": number_to_station[e.source],
                         "to": number_to_station[e.dest], "distance": e.distance, "stations": 1})
    return segs


def fmt_distance(d):
    return "%d m" % d if d < 1000 else "%d m (%.2f km)" % (d, d / 1000.0)


def query(ctx, start, end, args):
    g, s2n, n2s = ctx
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    cfg.preferred_lines = [args.line_preference] if args.line_preference else []
    try:
        sp = ShortestPath(g, s2n[start], cfg)
        nodes, edges = sp.path_with_edges(s2n[end])
    except Exception as ex:
        raise RuntimeError("Path calculation failed: %s" % ex)
    if not nodes:
        raise RuntimeError("No route found from '%s' to '%s'" % (start, end))
    dist = sp.dist_to[s2n[end]]
    transfers = sp.get_transfer_count(s2n[end])
    try:
        fare = Sum_money(dist)
        minutes = calculate_estimated_time(dist, transfers)
    except Exception as ex:
        raise RuntimeError("Fare calculation failed: %s" % ex)
    segs = segments(edges, n2s)
    transfer_stations = [segs[i]["to"] for i in range(len(segs) - 1)]
    return {
        "query": {"start": start, "end": end, "mode": args.mode},
        "path": [n2s[n] for n in nodes],
        "distance": dist,
        "fare": fare,
        "estimated_time": round(minutes, 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": [s["line"] for s in segs],
        "segments": segs,
    }


def render_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"]))]
    for s in r["segments"]:
        out.append("  [%s] %s -> %s (%d stations, %s)" % (
            s["line"], s["from"], s["to"], s["stations"], fmt_distance(s["distance"])))
    out.append("Total distance: %s" % fmt_distance(r["distance"]))
    if r["transfer_stations"]:
        out.append("Transfers: %d at %s" % (r["transfer_count"], ", ".join(r["transfer_stations"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines: %s" % ", ".join(dict.fromkeys(r["lines"])))
    out.append("Estimated time: %.1f minutes" % r["estimated_time"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return render_text(r)


def handle(line, ctx, args):
    parsed = parse_input(line)
    if not parsed:
        return FORMAT_ERR
    names = list(ctx[1].keys())
    resolved = []
    notes = []
    for label, raw in zip(("Starting", "Ending"), parsed):
        n, fuzzy = resolve(raw, names)
        if n is None:
            return "%s station '%s' does not exist, please check the station name" % (label, raw)
        if fuzzy:
            notes.append("%s station '%s' matched to '%s'" % (label, raw, n))
        resolved.append(n)
    if resolved[0] == resolved[1]:
        return "Starting station cannot be the same as the ending station"
    try:
        r = query(ctx, resolved[0], resolved[1], args)
    except RuntimeError as ex:
        return str(ex)
    text = render(r, args.format)
    if args.format == "text" and notes:
        text = "\n".join(notes) + "\n" + text
    if args.output_file:
        try:
            with open(args.output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except OSError as ex:
            text += "\nFailed to write output file: %s" % ex
    return text


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
    except (OSError, ValueError) as ex:
        print("Failed to load data: %s" % ex)
        return 1
    if args.check_data:
        problems = data_manager.check_data(data)
        print("Stations: %d, connections: %d" % (len(data["stations"]), len(data["connections"])))
        if problems:
            for x in problems[:100]:
                print("PROBLEM:", x)
            return 1
        print("Data check passed")
        return 0

    ctx = build_graph(data)
    print("Beijing Subway fare calculator. Enter 'Start; End' (empty line or 'q' to quit).")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line or line.lower() in ("q", "quit", "exit"):
            break
        print(handle(line, ctx, args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
