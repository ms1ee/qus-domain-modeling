"""CLI entry point for the Beijing Subway fare calculator."""
import argparse
import json
import re
import sys

from data_manager import SubwayNetwork
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_input(text):
    parts = [p.strip() for p in re.split(r"[;；,，]", text)]
    parts = [p for p in parts if p != ""]
    if len(parts) != 2:
        raise ValueError(FORMAT_ERR)
    return parts[0], parts[1]


def validate(net, start, end):
    if start not in net.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
    if end not in net.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")


def query(net, start, end, config):
    sp = ShortestPath(net.graph, net.station_to_number[start], config)
    t = net.station_to_number[end]
    try:
        nodes, edges = sp.path_with_edges(t)
    except Exception as e:
        raise RuntimeError("Path calculation failed: %s" % e)
    if not nodes:
        raise RuntimeError("No route found between '%s' and '%s' under the given constraints" % (start, end))
    distance = sum(e.distance for e in edges)
    transfers = sp.get_transfer_count(t)
    try:
        fare = Sum_money(distance)
        minutes = calculate_estimated_time(distance, transfers)
    except Exception as e:
        raise RuntimeError("Fare calculation failed: %s" % e)
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        name_to = net.number_to_station[e.dest]
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = name_to
            segments[-1]["stations"] += 1
            segments[-1]["distance"] += e.distance
        else:
            if segments:
                transfer_stations.append({"station": net.number_to_station[e.source],
                                          "from_line": segments[-1]["line"], "to_line": e.line})
            segments.append({"line": e.line, "from": net.number_to_station[e.source],
                             "to": name_to, "stations": 1, "distance": e.distance})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": start, "end": end, "mode": config.mode,
                  "max_transfers": config.max_transfers,
                  "line_preference": config.preferred_lines},
        "path": [net.number_to_station[n] for n in nodes],
        "distance_m": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": minutes,
        "transfer_count": transfers,
        "lines": lines,
        "segments": segments,
        "transfers": transfer_stations,
    }


def format_text(r):
    d = r["distance_m"]
    dist = "%d m (%.2f km)" % (d, d / 1000.0)
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: " + dist]
    for s in r["segments"]:
        out.append("  [%s] %s -> %s (%d stops, %.2f km)" % (
            s["line"], s["from"], s["to"], s["stations"], s["distance"] / 1000.0))
    out.append("Transfers: %d" % r["transfer_count"])
    for t in r["transfers"]:
        out.append("  Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return format_text(r)


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
        net = SubwayNetwork()
    except Exception as e:
        print("Failed to load subway data: %s" % e)
        return 1
    if args.check_data:
        ok, msgs = net.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1

    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    if args.line_preference:
        cfg.preferred_lines = [p.strip() for p in args.line_preference.split(",") if p.strip()]

    outputs = []
    while True:
        try:
            text = input("Enter 'Starting Station; Ending Station' (q to quit): ")
        except EOFError:
            break
        text = text.strip()
        if text.lower() in ("q", "quit", "exit"):
            break
        if not text:
            continue
        try:
            start, end = parse_input(text)
            validate(net, start, end)
            res = query(net, start, end, cfg)
        except (ValueError, RuntimeError) as e:
            print("Error: %s" % e)
            continue
        except Exception as e:
            print("Unexpected error: %s" % e)
            continue
        s = render(res, args.format)
        print(s)
        outputs.append(s)
        if args.output_file:
            try:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(outputs) + "\n")
            except OSError as e:
                print("Cannot write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
