"""Route report generation (text and JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return "%d meters (%.2f km)" % (meters, meters / 1000.0)
    return "%.2f km (%d meters)" % (meters / 1000.0, meters)


def build_route_info(start, end, mode, nodes, edges, number_to_station):
    names = [number_to_station[n] for n in nodes]
    distance = int(sum(e.weight for e in edges))
    segments = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["to"] = names[i + 1]
            seg["stops"] += 1
            seg["distance"] += e.weight
        else:
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                             "stops": 1, "distance": e.weight})
    transfers = []
    for i in range(1, len(segments)):
        transfers.append({"station": segments[i]["from"],
                          "from_line": segments[i - 1]["line"],
                          "to_line": segments[i]["line"]})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    tcount = len(transfers)
    fare = Sum_money(distance)
    est = calculate_estimated_time(distance, tcount)
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": names,
        "station_count": len(names),
        "distance": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time": round(est, 1),
        "transfer_count": tcount,
        "transfers": transfers,
        "lines": lines,
        "segments": segments,
    }


def format_text(info):
    out = []
    q = info["query"]
    out.append("=" * 50)
    out.append("Route: %s -> %s  (mode: %s)" % (q["start"], q["end"], q["mode"]))
    out.append("Stations (%d): %s" % (info["station_count"], " -> ".join(info["path"])))
    out.append("Segments:")
    for s in info["segments"]:
        out.append("  [%s] %s -> %s (%d stops, %d m)" % (s["line"], s["from"], s["to"], s["stops"], s["distance"]))
    if info["transfers"]:
        out.append("Transfer stations:")
        for t in info["transfers"]:
            out.append("  %s (%s -> %s)" % (t["station"], t["from_line"], t["to_line"]))
    else:
        out.append("Transfer stations: none")
    out.append("Lines involved: %s" % (", ".join(info["lines"]) or "-"))
    out.append("Total distance: %s" % format_distance(info["distance"]))
    out.append("Transfers: %d" % info["transfer_count"])
    out.append("Estimated time: %.1f minutes" % info["estimated_time"])
    out.append("Fare: %d yuan" % info["fare"])
    out.append("=" * 50)
    return "\n".join(out)


def format_json(info):
    return json.dumps(info, ensure_ascii=False, indent=2)
