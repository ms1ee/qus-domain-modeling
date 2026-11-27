"""CLI for Beijing Subway fare calculation."""
import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath
from subway_system import SubwayNetwork


def parse_input(text):
    parts = [p.strip() for p in re.split(r"[;；,，]", text) if p.strip()]
    if len(parts) != 2:
        return None
    return parts


def build_result(net, src, dst, config):
    s, t = net.station_to_number[src], net.station_to_number[dst]
    sp = ShortestPath(net.graph, s, config)
    nodes, edges = sp.path_with_edges(t)
    if not nodes:
        raise RuntimeError("No route found from '%s' to '%s'" % (src, dst))
    dist = sp.dist_to[t]
    transfers = sp.get_transfer_count(t)
    fare = Sum_money(dist)
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = net.number_to_station[e.dest]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfer_stations.append(net.number_to_station[e.source])
            segments.append({"line": e.line, "from": net.number_to_station[e.source],
                             "to": net.number_to_station[e.dest], "stations": 1})
    return {
        "query": {"start": src, "end": dst, "mode": config.mode},
        "path": [net.number_to_station[n] for n in nodes],
        "distance": dist,
        "fare": fare,
        "estimated_time": round(calculate_estimated_time(dist, transfers), 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": list(dict.fromkeys(e.line for e in edges)),
        "segments": segments,
    }


def format_distance(m):
    return "%d m" % m if m < 1000 else "%.2f km" % (m / 1000.0)


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Distance: %s (%d m, %.2f km)" % (format_distance(r["distance"]), r["distance"], r["distance"] / 1000.0)]
    for seg in r["segments"]:
        out.append("  [%s] %s -> %s (%d stations)" % (seg["line"], seg["from"], seg["to"], seg["stations"]))
    if r["transfer_stations"]:
        out.append("Transfers (%d): %s" % (r["transfer_count"], ", ".join(r["transfer_stations"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines: %s" % ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def process(net, text, config, fmt):
    parts = parse_input(text)
    if parts is None:
        return "Input format incorrect, please use 'Starting Station; Ending Station' format"
    names = []
    for label, raw in zip(("Starting", "Ending"), parts):
        m, exact = net.match_station(raw)
        if m is None:
            return "%s station '%s' does not exist, please check the station name" % (label, raw)
        if not exact:
            print("Note: station '%s' not found, using nearest match '%s'" % (raw, m))
        names.append(m)
    if names[0] == names[1]:
        return "Starting station cannot be the same as the ending station"
    try:
        r = build_result(net, names[0], names[1], config)
    except ValueError as e:
        return "Fare calculation error: %s" % e
    except Exception as e:
        return "Path calculation error: %s" % e
    return json.dumps(r, ensure_ascii=False, indent=2) if fmt == "json" else format_text(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    ap.add_argument("--output_file")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                    default="shortest_distance")
    ap.add_argument("--max_transfers", type=int)
    ap.add_argument("--line_preference")
    ap.add_argument("--check_data", action="store_true")
    a = ap.parse_args(argv)

    try:
        net = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except Exception as e:
        print("Failed to load data: %s" % e)
        return 1

    if a.check_data:
        probs = net.check_data()
        print("Stations: %d, lines: %s" % (len(net.station_to_number), ", ".join(net.lines())))
        if probs:
            print("Found %d problem(s):" % len(probs))
            for p in probs[:50]:
                print(" -", p)
            return 1
        print("Data check passed")
        return 0

    cfg = PathfindingConfig()
    cfg.mode = a.mode
    cfg.max_transfers = a.max_transfers
    cfg.preferred_lines = [a.line_preference] if a.line_preference else []

    outputs = []
    print("Enter 'Starting Station; Ending Station' (or 'exit' to quit)")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        res = process(net, line, cfg, a.format)
        print(res)
        outputs.append(res)
        if a.output_file:
            try:
                with open(a.output_file, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(outputs) + "\n")
            except OSError as e:
                print("Cannot write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
