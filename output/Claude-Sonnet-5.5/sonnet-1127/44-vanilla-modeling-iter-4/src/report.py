"""Route building and report generation."""
import json

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


def compute_route(dm, start, end, mode="shortest_distance", max_transfers=None, line_preference=None):
    g = dm.graph
    cfg = PathfindingConfig(mode, max_transfers, [line_preference] if line_preference else [])
    sp = ShortestPath(g, g.station_to_number[start], cfg)
    target = g.station_to_number[end]
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        raise LookupError("No route found from '%s' to '%s'" % (start, end))
    names = [g.number_to_station[n] for n in nodes]
    dist = sum(e.weight for e in edges)
    transfers = []
    for i, (a, b) in enumerate(zip(edges, edges[1:])):
        if a.line != b.line:
            transfers.append({"station": names[i + 1], "from": a.line, "to": b.line})
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    segments = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["end"] = names[i + 1]
            segments[-1]["stations"] += 1
        else:
            segments.append({"line": e.line, "start": names[i], "end": names[i + 1], "stations": 1})
    tc = len(transfers)
    try:
        fare = Sum_money(dist)
    except Exception as ex:
        raise ArithmeticError("Fare calculation failed: %s" % ex)
    return {
        "query": {"start": start, "end": end, "mode": mode,
                  "max_transfers": max_transfers, "line_preference": line_preference},
        "path": names,
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(calculate_estimated_time(dist, tc), 1),
        "transfer_count": tc,
        "transfers": transfers,
        "lines": lines,
        "segments": segments,
    }


def format_distance(m):
    return "%d m" % m if m < 1000 else "%.2f km" % (m / 1000.0)


def format_text(r):
    q = r["query"]
    out = ["Route: %s -> %s (mode: %s)" % (q["start"], q["end"], q["mode"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: %s (%d m / %.2f km)" % (format_distance(r["distance_m"]),
                                                    r["distance_m"], r["distance_km"])]
    out.append("Line segments:")
    for s in r["segments"]:
        out.append("  [%s] %s -> %s (%d segments)" % (s["line"], s["start"], s["end"], s["stations"]))
    if r["transfers"]:
        out.append("Transfers (%d):" % r["transfer_count"])
        for t in r["transfers"]:
            out.append("  %s: %s -> %s" % (t["station"], t["from"], t["to"]))
    else:
        out.append("Transfers: 0")
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def format_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)
