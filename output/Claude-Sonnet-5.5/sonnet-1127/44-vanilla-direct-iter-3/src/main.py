"""CLI for Beijing Subway fare calculation."""
import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time
import data_manager

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def build_graph(data):
    station_to_number = {}
    number_to_station = {}
    graph = Graph()
    for s in data["stations"]:
        if s["name"] not in station_to_number:
            n = len(station_to_number)
            station_to_number[s["name"]] = n
            number_to_station[n] = s["name"]
            graph.add_node(n)
        graph.set_station_lines(s["name"], s.get("lines", []))
    for c in data["connections"]:
        a, b = station_to_number.get(c["source"]), station_to_number.get(c["dest"])
        if a is None or b is None:
            continue
        graph.add_edge(Edge(a, b, c["distance"], c["line"]))
    return graph, station_to_number, number_to_station


def format_distance(d):
    return "%d m" % d if d < 1000 else "%.2f km" % (d / 1000.0)


def segments(names, edges):
    segs = []
    for i, e in enumerate(edges):
        if segs and segs[-1]["line"] == e.line:
            segs[-1]["to"] = names[i + 1]
            segs[-1]["distance"] += e.distance
        else:
            segs.append({"line": e.line, "from": names[i], "to": names[i + 1], "distance": e.distance})
    return segs


def query(graph, s2n, n2s, start, end, config):
    sp = ShortestPath(graph, s2n[start], config)
    target = s2n[end]
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
    names = [n2s[n] for n in nodes]
    dist = sp.dist_to[target]
    tc = sp.get_transfer_count(target)
    try:
        fare = Sum_money(dist)
    except Exception as ex:
        raise RuntimeError("Fare calculation failed: %s" % ex)
    segs = segments(names, edges)
    transfers = [segs[i]["from"] for i in range(1, len(segs))]
    return {
        "query": {"start": start, "end": end},
        "path": names,
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(calculate_estimated_time(dist, tc), 1),
        "transfer_count": tc,
        "transfer_stations": transfers,
        "lines": list(dict.fromkeys(s["line"] for s in segs)),
        "segments": segs,
    }


def render_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"]))]
    for s in r["segments"]:
        out.append("  [%s] %s -> %s (%s)" % (s["line"], s["from"], s["to"], format_distance(s["distance"])))
    out.append("Total distance: %s (%d m / %.2f km)" % (format_distance(r["distance_m"]), r["distance_m"], r["distance_km"]))
    if r["transfer_stations"]:
        out.append("Transfers: %d at %s" % (r["transfer_count"], ", ".join(r["transfer_stations"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines: %s" % ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def parse_input(line, s2n):
    """Return (start, end, error)."""
    text = line.strip().replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None, None, FORMAT_ERR
    a, b = parts[0].strip(), parts[1].strip()
    if a not in s2n:
        return None, None, "Starting station '%s' does not exist, please check the station name" % a
    if b not in s2n:
        return None, None, "Ending station '%s' does not exist, please check the station name" % b
    if a == b:
        return None, None, "Starting station cannot be the same as the ending station"
    return a, b, None


def emit(text, out_file):
    print(text)
    if out_file:
        try:
            with open(out_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except OSError as ex:
            print("Cannot write output file: %s" % ex)


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
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1

    if args.check_data:
        ok, msgs = data_manager.check_data(data)
        for m in msgs:
            print(m)
        print("Data check %s" % ("passed" if ok else "failed"))
        return 0 if ok else 1

    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [x.strip() for x in args.line_preference.split(",") if x.strip()]

    graph, s2n, n2s = build_graph(data)
    print("Enter 'Starting Station; Ending Station' (q to quit)")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line.strip().lower() in ("q", "quit", "exit"):
            break
        if not line.strip():
            continue
        a, b, err = parse_input(line, s2n)
        if err:
            print(err)
            continue
        try:
            r = query(graph, s2n, n2s, a, b, config)
        except Exception as ex:
            print("Path calculation error: %s" % ex)
            continue
        if args.format == "json":
            emit(json.dumps(r, ensure_ascii=False, indent=2), args.output_file)
        else:
            emit(render_text(r), args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
