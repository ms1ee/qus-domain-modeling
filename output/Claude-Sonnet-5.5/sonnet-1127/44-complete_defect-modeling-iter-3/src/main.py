"""CLI for the Beijing Subway fare calculation system."""
import argparse
import json
import sys

from data_manager import DataManager
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_input(text):
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError(FORMAT_ERR)
    return parts[0].strip(), parts[1].strip()


def fmt_distance(m):
    return "%d m" % m if m < 1000 else "%.2f km" % (m / 1000.0)


def build_result(dm, start, end, config):
    g = dm.graph
    s, t = g.station_to_number[start], g.station_to_number[end]
    sp = ShortestPath(g, s, config)
    if t not in sp.dist_to:
        raise RuntimeError("No route found (check --max_transfers setting)")
    nodes, edges = sp.path_with_edges(t)
    stations = [g.number_to_station[n] for n in nodes]
    dist = sp.dist_to[t]
    transfers = []
    segments = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = stations[i + 1]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfers.append({"station": stations[i], "from_line": segments[-1]["line"],
                                  "to_line": e.line})
            segments.append({"line": e.line, "from": stations[i], "to": stations[i + 1], "stations": 1})
    tc = sp.get_transfer_count(t)
    try:
        fare = Sum_money(dist)
    except Exception as ex:
        raise RuntimeError("Fare calculation failed: %s" % ex)
    return {
        "query": {"start": start, "end": end, "mode": config.mode,
                  "max_transfers": config.max_transfers,
                  "line_preference": config.preferred_lines},
        "path": stations,
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": calculate_estimated_time(dist, tc),
        "transfer_count": tc,
        "transfers": transfers,
        "segments": segments,
        "lines": list(dict.fromkeys(e.line for e in edges)),
    }


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: %s" % fmt_distance(r["distance_m"]),
           "Lines: %s" % ", ".join(r["lines"])]
    for sg in r["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (sg["line"], sg["from"], sg["to"], sg["stations"]))
    out.append("Transfers: %d" % r["transfer_count"])
    for t in r["transfers"]:
        out.append("  Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("Estimated time: %s minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    return json.dumps(r, ensure_ascii=False, indent=2) if fmt == "json" else format_text(r)


def run_query(dm, start, end, config, fmt, output_file):
    g = dm.graph
    if start not in g.station_to_number:
        print("Starting station '%s' does not exist, please check the station name" % start)
        return
    if end not in g.station_to_number:
        print("Ending station '%s' does not exist, please check the station name" % end)
        return
    if start == end:
        print("Starting station cannot be the same as the ending station")
        return
    try:
        r = build_result(dm, start, end, config)
    except Exception as ex:
        print("Path calculation error: %s" % ex)
        return
    text = render(r, fmt)
    print(text)
    if output_file:
        try:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
            print("Result saved to %s" % output_file)
        except OSError as ex:
            print("Could not write output file: %s" % ex)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    ap.add_argument("--output_file")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                    default="shortest_distance")
    ap.add_argument("--max_transfers", type=int)
    ap.add_argument("--line_preference")
    ap.add_argument("--check_data", action="store_true")
    args = ap.parse_args(argv)
    try:
        dm = DataManager()
    except Exception as ex:
        print("Failed to load data: %s" % ex)
        return 1
    if args.check_data:
        probs = dm.check_data()
        if probs:
            print("Data check found %d problem(s):" % len(probs))
            for p in probs:
                print(" -", p)
            return 1
        print("Data check passed: %d stations." % len(dm.graph.station_to_number))
        return 0
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []
    print("Enter 'Starting Station; Ending Station' (q to quit)")
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
        try:
            a, b = parse_input(line)
        except ValueError as ex:
            print(ex)
            continue
        run_query(dm, a, b, config, args.format, args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
