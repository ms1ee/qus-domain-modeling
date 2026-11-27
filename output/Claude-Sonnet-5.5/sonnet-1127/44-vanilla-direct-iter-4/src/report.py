"""Route reports (text and JSON)."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(m):
    return "%d meters" % m if m < 1000 else "%.2f kilometers" % (m / 1000.0)


def build_summary(net, start, end, nodes, edges, dist, transfers):
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
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    return {
        "query": {"start": start, "end": end},
        "path": names,
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": Sum_money(dist),
        "estimated_time_min": round(calculate_estimated_time(dist, transfers), 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def to_json(summary):
    return json.dumps(summary, ensure_ascii=False, indent=2)


def to_text(s):
    out = ["Route: %s -> %s" % (s["query"]["start"], s["query"]["end"]),
           "Stations: " + " -> ".join(s["path"]),
           "Total distance: " + format_distance(s["distance_m"]) +
           " (%.2f km)" % s["distance_km"]]
    for seg in s["segments"]:
        out.append("  [%s] %s -> %s (%d segments)" % (seg["line"], seg["from"], seg["to"], seg["stations"]))
    out.append("Transfers: %d" % s["transfer_count"])
    if s["transfer_stations"]:
        out.append("Transfer stations: " + ", ".join(s["transfer_stations"]))
    out.append("Lines: " + ", ".join(str(l) for l in s["lines"]))
    out.append("Estimated time: %.1f minutes" % s["estimated_time_min"])
    out.append("Fare: %d yuan" % s["fare"])
    return "\n".join(out)
