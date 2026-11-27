"""Route result building and report formatting."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return "%d m" % meters
    return "%.2f km" % (meters / 1000.0)


def build_result(dm, start, end, sp):
    """Build result dict from ShortestPath sp for stations start/end."""
    target = dm.station_to_number[end]
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        raise ValueError("No route found")
    names = [dm.number_to_station[n] for n in nodes]
    total = sum(e.distance for e in edges)
    segments, transfers = [], []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = names[i + 1]
            segments[-1]["distance"] += e.distance
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfers.append({"station": names[i], "from_line": segments[-1]["line"],
                                  "to_line": e.line})
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                             "distance": e.distance, "stations": 1})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    tc = len(transfers)
    return {
        "query": {"start": start, "end": end},
        "path": names,
        "segments": segments,
        "transfers": transfers,
        "distance_m": total,
        "distance_km": round(total / 1000.0, 2),
        "fare": Sum_money(total),
        "estimated_time_min": calculate_estimated_time(total, tc),
        "transfer_count": tc,
        "lines": lines,
    }


def to_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def to_text(result):
    out = []
    q = result["query"]
    out.append("Route: %s -> %s" % (q["start"], q["end"]))
    out.append("Stations (%d): %s" % (len(result["path"]), " -> ".join(result["path"])))
    out.append("Total distance: %s" % format_distance(result["distance_m"]))
    out.append("Segments:")
    for s in result["segments"]:
        out.append("  [%s] %s -> %s (%d stops, %s)" %
                   (s["line"], s["from"], s["to"], s["stations"], format_distance(s["distance"])))
    if result["transfers"]:
        out.append("Transfers (%d):" % result["transfer_count"])
        for t in result["transfers"]:
            out.append("  %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    else:
        out.append("Transfers: none")
    out.append("Lines involved: %s" % ", ".join(result["lines"]))
    out.append("Estimated time: %.1f minutes" % result["estimated_time_min"])
    out.append("Fare: %d yuan" % result["fare"])
    return "\n".join(out)
