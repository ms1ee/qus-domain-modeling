"""
Route summary generation, visualization and export (text / JSON).
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import count_transfers


def format_distance(meters):
    """Meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return "%d m" % round(meters)
    return "%.2f km" % (meters / 1000.0)


def build_segments(stations, edges):
    """Group consecutive edges on the same line into ride segments."""
    segments = []
    for i, edge in enumerate(edges):
        a, b = stations[i], stations[i + 1]
        if segments and segments[-1]["line"] == edge.line:
            seg = segments[-1]
            seg["to"] = b
            seg["stations"].append(b)
            seg["distance"] += edge.weight
        else:
            segments.append({"line": edge.line, "from": a, "to": b,
                             "stations": [a, b], "distance": edge.weight})
    for seg in segments:
        seg["stops"] = len(seg["stations"]) - 1
    return segments


def build_route_info(stations, edges, query, fare_func=Sum_money):
    """Build the structured route summary dict."""
    distance = sum(e.weight for e in edges)
    transfers = count_transfers(edges)
    segments = build_segments(stations, edges)
    transfer_stations = [seg["from"] for seg in segments[1:]]
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    fare = fare_func(distance)
    est = calculate_estimated_time(distance, transfers)
    return {
        "query": dict(query),
        "path": list(stations),
        "station_count": len(stations),
        "segments": segments,
        "distance_meters": distance,
        "distance_km": round(distance / 1000.0, 3),
        "fare": fare,
        "estimated_time_minutes": round(est, 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
    }


def format_text(info):
    sep = "=" * 50
    q = info["query"]
    out = [sep, "Route: %s -> %s" % (q.get("start"), q.get("end"))]
    if q.get("mode"):
        out.append("Mode: %s" % q["mode"])
    out.append("-" * 50)
    out.append("Station sequence (%d stations):" % info["station_count"])
    out.append("  " + " -> ".join(info["path"]))
    out.append("Line segments:")
    for i, seg in enumerate(info["segments"]):
        if i > 0:
            prev = info["segments"][i - 1]
            out.append("  >> Transfer at %s: %s -> %s" % (seg["from"], prev["line"], seg["line"]))
        out.append("  [%s] %s -> %s (%d stops, %s)" % (
            seg["line"], seg["from"], seg["to"], seg["stops"], format_distance(seg["distance"])))
    out.append("Transfer details:")
    out.append("  Transfers: %d" % info["transfer_count"])
    out.append("  Transfer stations: %s" % (", ".join(info["transfer_stations"]) or "None"))
    out.append("  Lines involved: %s" % (", ".join(info["lines"]) or "None"))
    d = info["distance_meters"]
    out.append("Total distance: %s (%d meters, %.2f kilometers)" % (format_distance(d), round(d), d / 1000.0))
    out.append("Estimated time: %.1f minutes" % info["estimated_time_minutes"])
    out.append("Fare: %d yuan" % info["fare"])
    out.append(sep)
    return "\n".join(out)


def format_json(info, indent=2):
    return json.dumps(info, ensure_ascii=False, indent=indent)


def format_report(info, fmt="text"):
    return format_json(info) if fmt == "json" else format_text(info)
