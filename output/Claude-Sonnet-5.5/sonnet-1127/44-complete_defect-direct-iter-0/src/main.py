"""CLI for the Beijing Subway fare calculation system."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from models import Edge, Graph  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath  # noqa: E402
from fare_calculator import Sum_money, calculate_estimated_time  # noqa: E402
from data_manager import check_data  # noqa: E402

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def build_graph(data):
    graph = Graph()
    station_to_number = {}
    for s in data["stations"]:
        if s["name"] not in station_to_number:
            station_to_number[s["name"]] = len(station_to_number)
        graph.set_station_lines(s["name"], s.get("lines", []))
        graph.add_node(station_to_number[s["name"]])
    for c in data["connections"]:
        if c["source"] in station_to_number and c["dest"] in station_to_number:
            graph.add_edge(Edge(station_to_number[c["source"]], station_to_number[c["dest"]],
                                c["distance"], c["line"]))
    return graph, station_to_number


def format_distance(m):
    return "%d m" % m if m < 1000 else "%.2f km" % (m / 1000.0)


def query(graph, station_to_number, start, end, config):
    """Return result dict; raises ValueError on problems."""
    number_to_station = {v: k for k, v in station_to_number.items()}
    sp = ShortestPath(graph, station_to_number[start], config)
    target = station_to_number[end]
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        raise ValueError("No route found between '%s' and '%s'" % (start, end))
    distance = sp.dist_to[target]
    transfers = sp.get_transfer_count(target)
    try:
        fare = Sum_money(distance)
    except Exception as e:
        raise ValueError("Fare calculation failed: %s" % e)
    segments = []
    transfer_stations = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = number_to_station[e.dest]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfer_stations.append(number_to_station[e.source])
            segments.append({"line": e.line, "from": number_to_station[e.source],
                             "to": number_to_station[e.dest], "stations": 1})
    return {
        "query": {"start": start, "end": end, "mode": config.mode},
        "path": [number_to_station[n] for n in nodes],
        "distance_m": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(calculate_estimated_time(distance, transfers), 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": list(dict.fromkeys(e.line for e in edges)),
        "segments": segments,
    }


def render_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: %s" % format_distance(r["distance_m"]),
           "Lines: %s" % ", ".join(r["lines"])]
    for seg in r["segments"]:
        out.append("  [%s] %s -> %s (%d segments)" % (seg["line"], seg["from"], seg["to"], seg["stations"]))
    if r["transfer_stations"]:
        out.append("Transfer at: %s" % ", ".join(r["transfer_stations"]))
    out.append("Transfers: %d" % r["transfer_count"])
    out.append("Estimated time: %.1f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return render_text(r)


def process_line(line, graph, s2n, config, fmt):
    """Return (ok, message)."""
    line = line.replace("；", ";")
    parts = [p.strip() for p in line.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False, FORMAT_ERR
    a, b = parts
    if a not in s2n:
        return False, "Starting station '%s' does not exist, please check the station name" % a
    if b not in s2n:
        return False, "Ending station '%s' does not exist, please check the station name" % b
    if a == b:
        return False, "Starting station cannot be the same as the ending station"
    try:
        return True, render(query(graph, s2n, a, b, config), fmt)
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, "Path calculation error: %s" % e


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(PathfindingConfig.MODES), default="shortest_distance")
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
        ok, msgs = check_data(data)
        print("\n".join(msgs))
        print("Data check passed" if ok else "Data check found problems")
        return 0 if ok else 1

    graph, s2n = build_graph(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [args.line_preference]

    while True:
        try:
            line = input("Enter 'Starting Station; Ending Station' (q to quit): ")
        except EOFError:
            break
        if line.strip().lower() in ("q", "quit", "exit"):
            break
        if not line.strip():
            continue
        ok, msg = process_line(line, graph, s2n, config, args.format)
        print(msg)
        if ok and args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except OSError as e:
                print("Could not write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
