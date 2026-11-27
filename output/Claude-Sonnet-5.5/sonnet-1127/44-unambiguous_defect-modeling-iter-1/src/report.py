"""Route summary and report generation."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


def build_summary(graph, source_name, dest_name, nodes, edges, mode="shortest_distance"):
    stations = [graph.number_to_station[n] for n in nodes]
    total = sum(e.distance for e in edges)
    transfer_stations = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfer_stations.append(graph.number_to_station[edges[i].source])
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    try:
        fare = Sum_money(total)
    except ValueError as ex:
        raise RuntimeError("Fare calculation failed: %s" % ex)
    tc = len(transfer_stations)
    return {
        "query": {"start": source_name, "end": dest_name, "mode": mode},
        "path": stations,
        "distance_m": total,
        "distance_km": round(total / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": calculate_estimated_time(total, tc),
        "transfer_count": tc,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": _segments(graph, nodes, edges),
    }


def _segments(graph, nodes, edges):
    segs = []
    for i, e in enumerate(edges):
        if segs and segs[-1]["line"] == e.line:
            segs[-1]["to"] = graph.number_to_station[e.dest]
            segs[-1]["stops"] += 1
            segs[-1]["distance_m"] += e.distance
        else:
            segs.append({"line": e.line, "from": graph.number_to_station[e.source],
                         "to": graph.number_to_station[e.dest], "stops": 1, "distance_m": e.distance})
    return segs


def format_distance(m):
    if m < 1000:
        return "%d m" % m
    return "%d m (%.2f km)" % (m, m / 1000.0)


def to_text(s):
    q = s["query"]
    out = ["Route: %s -> %s (mode: %s)" % (q["start"], q["end"], q["mode"]),
           "Stations (%d): %s" % (len(s["path"]), " -> ".join(s["path"])),
           "Total distance: %s" % format_distance(s["distance_m"]),
           "Estimated time: %.1f minutes" % s["estimated_time_min"],
           "Transfers: %d" % s["transfer_count"]]
    if s["transfer_stations"]:
        out.append("Transfer stations: " + ", ".join(s["transfer_stations"]))
    out.append("Lines: " + ", ".join(s["lines"]))
    out.append("Segments:")
    for g in s["segments"]:
        out.append("  [%s] %s -> %s (%d stops, %d m)" % (g["line"], g["from"], g["to"], g["stops"], g["distance_m"]))
    out.append("Fare: %d yuan" % s["fare"])
    return "\n".join(out)


def to_json(s):
    return json.dumps(s, ensure_ascii=False, indent=2)


def render(s, fmt="text"):
    return to_json(s) if fmt == "json" else to_text(s)
