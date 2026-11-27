"""Path visualization and export."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return "%d meters" % meters
    return "%.2f km (%d meters)" % (meters / 1000.0, meters)


def build_route_info(sp, target, number_to_station, query=None):
    stations, edges = sp.path_with_edges(target)
    if not stations:
        raise ValueError("No path found")
    names = [number_to_station.get(s, str(s)) for s in stations]
    distance = sum(e.weight for e in edges)
    transfers = sp.get_transfer_count(target)
    fare = Sum_money(distance)
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["stations"].append(number_to_station.get(e.dest, str(e.dest)))
            segments[-1]["distance"] += e.weight
        else:
            segments.append({
                "line": e.line,
                "stations": [number_to_station.get(e.source, str(e.source)),
                             number_to_station.get(e.dest, str(e.dest))],
                "distance": e.weight,
            })
    transfer_stations = [seg["stations"][0] for seg in segments[1:]]
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    return {
        "query": query or {"start": names[0], "end": names[-1]},
        "path": names,
        "distance": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time": round(calculate_estimated_time(distance, transfers), 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def summarize(info):
    return {
        "distance": info["distance"],
        "fare": info["fare"],
        "transfer_count": info["transfer_count"],
        "estimated_time": info["estimated_time"],
    }


def format_text(info):
    out = []
    q = info.get("query", {})
    out.append("=" * 50)
    out.append("Route: %s -> %s" % (q.get("start", info["path"][0]), q.get("end", info["path"][-1])))
    if q.get("mode"):
        out.append("Mode: %s" % q["mode"])
    out.append("-" * 50)
    for i, seg in enumerate(info["segments"], 1):
        out.append("Segment %d [%s]: %s (%s)" % (i, seg["line"], " -> ".join(seg["stations"]),
                                                format_distance(seg["distance"])))
        if i < len(info["segments"]):
            out.append("  Transfer at: %s" % seg["stations"][-1])
    out.append("-" * 50)
    out.append("Station sequence (from end to start): %s" % " <- ".join(reversed(info["path"])))
    out.append("Stations passed: %d" % len(info["path"]))
    out.append("Total distance: %s" % format_distance(info["distance"]))
    out.append("Transfers: %d%s" % (info["transfer_count"],
                                     (" (at " + ", ".join(info["transfer_stations"]) + ")")
                                     if info["transfer_stations"] else ""))
    out.append("Lines involved: %s" % ", ".join(str(l) for l in info["lines"]))
    out.append("Estimated time: %.1f minutes" % info["estimated_time"])
    out.append("Fare: %d yuan" % info["fare"])
    out.append("=" * 50)
    return "\n".join(out)


def format_json(info):
    data = {
        "query": info.get("query", {}),
        "path": info["path"],
        "distance": info["distance"],
        "fare": info["fare"],
        "estimated_time": info["estimated_time"],
        "transfer_count": info["transfer_count"],
        "transfer_stations": info["transfer_stations"],
        "lines": info["lines"],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
