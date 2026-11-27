"""CLI for Beijing subway fare calculation."""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from data_manager import SubwayNetwork  # noqa: E402
from fare_calculator import Sum_money, calculate_estimated_time  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath, MODES  # noqa: E402


def parse_input(text):
    parts = [p.strip() for p in re.split(r"[;；,，]", text)]
    parts = [p for p in parts if p != ""]
    if len(parts) != 2:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0], parts[1]


def query(net, start, end, config):
    if start not in net.station_to_number:
        raise KeyError("Starting station '%s' does not exist, please check the station name" % start)
    if end not in net.station_to_number:
        raise KeyError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    try:
        s, t = net.station_to_number[start], net.station_to_number[end]
        sp = ShortestPath(net.graph, s, config)
        nodes, edges = sp.path_with_edges(t)
        if not nodes:
            raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
        dist = sum(e.distance for e in edges)
        transfers = sp.get_transfer_count(t)
    except RuntimeError:
        raise
    except Exception as ex:
        raise RuntimeError("Path calculation failed: %s" % ex)
    try:
        fare = Sum_money(dist)
        minutes = calculate_estimated_time(dist, transfers)
    except Exception as ex:
        raise RuntimeError("Fare calculation failed: %s" % ex)
    names = [net.number_to_station[n] for n in nodes]
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = names[i + 1]
            segments[-1]["distance"] += e.distance
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfer_stations.append(names[i])
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                             "distance": e.distance, "stations": 1})
    lines = []
    for sg in segments:
        if sg["line"] not in lines:
            lines.append(sg["line"])
    return {"query": {"start": start, "end": end, "mode": config.mode},
            "path": names, "distance_m": dist, "distance_km": round(dist / 1000.0, 2),
            "fare": fare, "estimated_time_min": round(minutes, 1),
            "transfer_count": transfers, "transfer_stations": transfer_stations,
            "lines": lines, "segments": segments}


def format_text(r):
    out = ["Route: %s -> %s (mode: %s)" % (r["query"]["start"], r["query"]["end"], r["query"]["mode"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])), ""]
    for sg in r["segments"]:
        out.append("  [%s] %s -> %s (%d stops, %d m)" % (
            sg["line"], sg["from"], sg["to"], sg["stations"], sg["distance"]))
    out.append("")
    d = r["distance_m"]
    out.append("Total distance: %d m (%.2f km)" % (d, d / 1000.0))
    out.append("Transfers: %d" % r["transfer_count"])
    if r["transfer_stations"]:
        out.append("Transfer stations: %s" % ", ".join(r["transfer_stations"]))
    out.append("Lines: %s" % ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return format_text(r)


def write_output(text, path):
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    ap.add_argument("--output_file", default=None)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    ap.add_argument("--max_transfers", type=int, default=None)
    ap.add_argument("--line_preference", default=None)
    ap.add_argument("--check_data", action="store_true")
    args = ap.parse_args(argv)

    try:
        net = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1

    if args.check_data:
        problems = net.check_data()
        print("Stations: %d, edges: %d" % (net.graph.V(), net.graph.E()))
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for p in problems:
                print(" - " + p)
            return 1
        print("Data check passed.")
        return 0

    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    cfg.preferred_lines = [args.line_preference] if args.line_preference else []

    print("Enter 'Starting Station; Ending Station' (or 'q' to quit):")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        if not line:
            continue
        try:
            a, b = parse_input(line)
            res = query(net, a, b, cfg)
        except (ValueError, KeyError, RuntimeError) as ex:
            msg = ex.args[0] if ex.args else str(ex)
            print("Error: %s" % msg)
            continue
        text = render(res, args.format)
        print(text)
        try:
            write_output(text, args.output_file)
        except OSError as ex:
            print("Error writing output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
