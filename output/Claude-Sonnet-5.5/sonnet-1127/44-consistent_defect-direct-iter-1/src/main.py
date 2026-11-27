"""Beijing Subway fare calculation CLI."""
import argparse
import difflib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import SubwayNetwork
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_input(text):
    for sep in (";", "；", ",", "，"):
        if sep in text:
            parts = [p.strip() for p in text.split(sep)]
            if len(parts) == 2 and all(parts):
                return parts
            return None
    return None


def match_station(net, name):
    if name in net.station_to_number:
        return name
    m = difflib.get_close_matches(name, list(net.station_to_number), n=1, cutoff=0.4)
    if m:
        return m[0]
    for n in net.station_to_number:
        if name in n or n in name:
            return n
    return None


def format_distance(d):
    return "%d m" % d if d < 1000 else "%.2f km (%d m)" % (d / 1000.0, d)


def build_result(net, start, end, config):
    s, t = net.station_to_number[start], net.station_to_number[end]
    sp = ShortestPath(net.graph, s, config)
    if not sp.has_path_to(t):
        return None
    nodes, edges = sp.path_with_edges(t)
    dist = sp.dist_to[t]
    transfers = sp.get_transfer_count(t)
    try:
        fare = Sum_money(dist)
    except Exception as e:
        raise RuntimeError("Fare calculation failed: %s" % e)
    names = [net.number_to_station[n] for n in nodes]
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = names[i + 1]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfer_stations.append(names[i])
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1], "stations": 1})
    return {
        "query": {"start": start, "end": end, "mode": config.mode},
        "path": names,
        "distance": dist,
        "fare": fare,
        "estimated_time": calculate_estimated_time(dist, transfers),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": sorted({e.line for e in edges}),
        "segments": segments,
    }


def render_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: " + format_distance(r["distance"])]
    for sg in r["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (sg["line"], sg["from"], sg["to"], sg["stations"]))
    if r["transfer_stations"]:
        out.append("Transfers (%d): %s" % (r["transfer_count"], ", ".join(r["transfer_stations"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return render_text(r)


def run_query(net, text, config, fmt):
    parts = parse_input(text)
    if parts is None:
        return None, FORMAT_ERR
    a, b = parts
    sa, sb = match_station(net, a), match_station(net, b)
    if sa is None:
        return None, "Starting station '%s' does not exist, please check the station name" % a
    if sb is None:
        return None, "Ending station '%s' does not exist, please check the station name" % b
    if sa == sb:
        return None, "Starting station cannot be the same as the ending station"
    try:
        r = build_result(net, sa, sb, config)
    except RuntimeError as e:
        return None, str(e)
    except Exception as e:
        return None, "Path calculation error: %s" % e
    if r is None:
        return None, "No route found between '%s' and '%s' under the current settings" % (sa, sb)
    return render(r, fmt), None


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
        net = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except Exception as e:
        print("Failed to load data: %s" % e)
        return 1
    if args.check_data:
        ok, rep = net.check_data()
        print(rep)
        return 0 if ok else 1

    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []

    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break
        if text.lower() in ("q", "quit", "exit"):
            break
        if not text:
            continue
        res, err = run_query(net, text, config, args.format)
        if err:
            print(err)
            continue
        print(res)
        if args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(res + "\n")
                print("Saved to %s" % args.output_file)
            except OSError as e:
                print("Could not write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
