"""CLI for the Beijing Subway fare calculator."""
import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import build_graph, check_data
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def format_distance(d):
    if d < 1000:
        return f"{d} m"
    return f"{d / 1000:.2f} km"


def parse_query(text):
    text = text.replace("；", ";")
    parts = [p.strip() for p in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERR)
    return parts[0], parts[1]


def analyze(graph, start, end, config):
    s, t = graph.station_to_number[start], graph.station_to_number[end]
    sp = ShortestPath(graph, s, config)
    if t not in sp.dist_to:
        raise RuntimeError(f"No route found from '{start}' to '{end}'")
    nodes, edges = sp.path_with_edges(t)
    names = [graph.number_to_station[n] for n in nodes]
    dist = sp.dist_to[t]
    transfers_at = []
    for i in range(len(edges) - 1):
        if edges[i].line != edges[i + 1].line:
            transfers_at.append({"station": names[i + 1], "from_line": edges[i].line,
                                 "to_line": edges[i + 1].line})
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    segments = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = names[i + 1]
            segments[-1]["stops"] += 1
        else:
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1], "stops": 1})
    tc = len(transfers_at)
    try:
        fare = Sum_money(dist)
    except Exception as ex:
        raise RuntimeError(f"Fare calculation failed: {ex}")
    return {"start": start, "end": end, "path": names, "distance": dist, "fare": fare,
            "time": round(calculate_estimated_time(dist, tc), 1), "transfer_count": tc,
            "transfers": transfers_at, "lines": lines, "segments": segments}


def render_text(r, mode):
    out = [f"Route: {r['start']} -> {r['end']} (mode: {mode})",
           "Stations: " + " -> ".join(r["path"]),
           f"Total stations: {len(r['path'])}",
           f"Distance: {format_distance(r['distance'])} ({r['distance'] / 1000:.2f} km)"]
    out.append("Segments:")
    for sg in r["segments"]:
        out.append(f"  [{sg['line']}] {sg['from']} -> {sg['to']} ({sg['stops']} stops)")
    out.append(f"Transfers: {r['transfer_count']}")
    for t in r["transfers"]:
        out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append(f"Estimated time: {r['time']} minutes")
    out.append(f"Fare: {r['fare']} yuan")
    return "\n".join(out)


def render_json(r, mode):
    obj = {"query": {"start": r["start"], "end": r["end"], "mode": mode},
           "path": r["path"], "distance_meters": r["distance"],
           "distance_km": round(r["distance"] / 1000, 2), "fare": r["fare"],
           "estimated_time_minutes": r["time"], "transfer_count": r["transfer_count"],
           "transfers": r["transfers"], "lines": r["lines"], "segments": r["segments"]}
    return json.dumps(obj, ensure_ascii=False, indent=2)


def run_query(graph, text, args, config):
    try:
        start, end = parse_query(text)
    except ValueError as e:
        return str(e), False
    if start not in graph.station_to_number:
        return f"Starting station '{start}' does not exist, please check the station name", False
    if end not in graph.station_to_number:
        return f"Ending station '{end}' does not exist, please check the station name", False
    if start == end:
        return "Starting station cannot be the same as the ending station", False
    try:
        r = analyze(graph, start, end, config)
    except Exception as e:
        return f"Path calculation error: {e}", False
    return (render_json(r, args.mode) if args.format == "json" else render_text(r, args.mode)), True


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except Exception as e:
        print(f"Failed to load subway data: {e}")
        return 1
    if args.check_data:
        ok, msgs = check_data(data)
        print(f"Stations: {len(data.get('stations', []))}, "
              f"connections: {len(data.get('connections', []))}")
        for m in msgs[:50]:
            print("  - " + m)
        print("Data check passed" if ok else f"Data check found {len(msgs)} issue(s)")
        return 0 if ok else 1

    graph = build_graph(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []

    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            text = input("Query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in ("q", "quit", "exit"):
            break
        result, ok = run_query(graph, text, args, config)
        print(result)
        if ok and args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(result + "\n\n")
            except OSError as e:
                print(f"Failed to write output file: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
