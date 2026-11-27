"""CLI for the Beijing Subway fare calculator."""
import argparse
import difflib
import json
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import build_graph, check_data
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_query(text):
    for sep in (";", "；", ",", "，"):
        if sep in text:
            parts = [p.strip() for p in text.split(sep)]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts
            return None
    return None


def match_station(name, names):
    if name in names:
        return name, False
    subs = [n for n in names if name in n or n in name]
    if subs:
        return min(subs, key=lambda n: abs(len(n) - len(name))), True
    close = difflib.get_close_matches(name, names, n=1, cutoff=0.0)
    return (close[0], True) if close else (None, True)


def fmt_distance(d):
    return "%d m" % d if d < 1000 else "%.2f km" % (d / 1000.0)


def build_result(start, end, nodes, edges, n2s, sp, target):
    dist = sp.dist_to[target]
    transfers = sp.get_transfer_count(target)
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = n2s[e.dest]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfer_stations.append(n2s[e.source])
            segments.append({"line": e.line, "from": n2s[e.source], "to": n2s[e.dest], "stations": 1})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": start, "end": end},
        "path": [n2s[n] for n in nodes],
        "distance": dist,
        "fare": Sum_money(dist),
        "estimated_time": round(calculate_estimated_time(dist, transfers), 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: %d m (%.2f km) [%s]" % (r["distance"], r["distance"] / 1000.0, fmt_distance(r["distance"]))]
    for s in r["segments"]:
        out.append("  %s: %s -> %s (%d stops)" % (s["line"], s["from"], s["to"], s["stations"]))
    if r["transfer_stations"]:
        out.append("Transfer stations: " + ", ".join(r["transfer_stations"]))
    out.append("Transfers: %d" % r["transfer_count"])
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def run_query(text, ctx):
    q = parse_query(text)
    if q is None:
        return FORMAT_ERR, False
    a, b = q
    names = ctx["names"]
    s_name, s_fuzzy = match_station(a, names)
    e_name, e_fuzzy = match_station(b, names)
    if s_name is None:
        return "Starting station '%s' does not exist, please check the station name" % a, False
    if e_name is None:
        return "Ending station '%s' does not exist, please check the station name" % b, False
    if s_name == e_name:
        return "Starting station cannot be the same as the ending station", False
    notes = []
    if s_fuzzy:
        notes.append("Starting station '%s' matched to '%s'" % (a, s_name))
    if e_fuzzy:
        notes.append("Ending station '%s' matched to '%s'" % (b, e_name))
    try:
        s2n = ctx["s2n"]
        cfg = ctx["config"]
        sp = ShortestPath(ctx["graph"], s2n[s_name], cfg)
        target = s2n[e_name]
        nodes, edges = sp.path_with_edges(target)
        if not nodes or target not in sp.dist_to:
            return "No route found from '%s' to '%s' (check transfer limit)" % (s_name, e_name), False
    except Exception as ex:  # path calculation errors
        return "Path calculation failed: %s" % ex, False
    try:
        r = build_result(s_name, e_name, nodes, edges, ctx["n2s"], sp, target)
    except Exception as ex:
        return "Fare calculation failed: %s" % ex, False
    if ctx["format"] == "json":
        body = json.dumps(r, ensure_ascii=False, indent=2)
    else:
        body = format_text(r)
    if notes:
        if ctx["format"] == "json":
            r["notes"] = notes
            body = json.dumps(r, ensure_ascii=False, indent=2)
        else:
            body = "\n".join(notes) + "\n" + body
    return body, True


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        report, ok = check_data(data)
        print("\n".join(report))
        return 0 if ok else 1

    graph, s2n, n2s = build_graph(data)
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    cfg.preferred_lines = [args.line_preference] if args.line_preference else []
    ctx = {"graph": graph, "s2n": s2n, "n2s": n2s, "names": list(s2n.keys()),
           "config": cfg, "format": args.format}

    out_f = open(args.output_file, "w", encoding="utf-8") if args.output_file else None
    try:
        print("Enter 'Starting Station; Ending Station' (or 'q' to quit):")
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
            msg, ok = run_query(line, ctx)
            print(msg)
            if out_f and ok:
                out_f.write(msg + "\n\n")
                out_f.flush()
    finally:
        if out_f:
            out_f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
