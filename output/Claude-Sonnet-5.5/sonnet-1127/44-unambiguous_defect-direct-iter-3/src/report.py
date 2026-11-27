"""Route report generation."""
import json

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


def compute_route(dm, start, end, config=None):
    """Compute route summary dict."""
    config = config or PathfindingConfig()
    s, e = dm.station_to_number[start], dm.station_to_number[end]
    sp = ShortestPath(dm.graph, s, config)
    nodes, edges = sp.path_with_edges(e)
    if not nodes:
        raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
    dist = sp.dist_to[e]
    transfers = []
    segments = []
    for ed in edges:
        if segments and segments[-1]["line"] == ed.line:
            segments[-1]["to"] = dm.number_to_station[ed.dest]
            segments[-1]["stops"] += 1
        else:
            if segments:
                transfers.append({"station": dm.number_to_station[ed.source],
                                  "from_line": segments[-1]["line"], "to_line": ed.line})
            segments.append({"line": ed.line, "from": dm.number_to_station[ed.source],
                             "to": dm.number_to_station[ed.dest], "stops": 1})
    try:
        fare = Sum_money(dist)
    except Exception as ex:
        raise RuntimeError("Fare calculation failed: %s" % ex)
    return {
        "query": {"start": start, "end": end, "mode": config.mode,
                  "max_transfers": config.max_transfers,
                  "line_preference": list(config.preferred_lines)},
        "path": [dm.number_to_station[n] for n in nodes],
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(calculate_estimated_time(dist, len(transfers)), 1),
        "transfer_count": len(transfers),
        "transfers": transfers,
        "segments": segments,
        "lines": list(dict.fromkeys(sg["line"] for sg in segments)),
    }


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: %d m (%.2f km)" % (r["distance_m"], r["distance_km"]),
           "Segments:"]
    for sg in r["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (sg["line"], sg["from"], sg["to"], sg["stops"]))
    out.append("Transfers: %d" % r["transfer_count"])
    for t in r["transfers"]:
        out.append("  Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def format_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)
