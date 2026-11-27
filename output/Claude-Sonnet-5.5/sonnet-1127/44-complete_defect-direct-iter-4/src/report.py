"""Route summary, text and JSON reports."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return "%d meters" % meters
    return "%.2f km (%d meters)" % (meters / 1000.0, meters)


def build_summary(start, end, names, edges, distance, transfers):
    fare = Sum_money(distance)
    time_min = calculate_estimated_time(distance, transfers)
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
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": start, "end": end},
        "path": names,
        "distance_m": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(time_min, 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def to_text(s):
    out = ["Route: %s -> %s" % (s["query"]["start"], s["query"]["end"]),
           "Stations (%d): %s" % (len(s["path"]), " -> ".join(s["path"])),
           "Total distance: %s" % format_distance(s["distance_m"])]
    for seg in s["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (seg["line"], seg["from"], seg["to"], seg["stations"]))
    if s["transfer_stations"]:
        out.append("Transfers (%d): %s" % (s["transfer_count"], ", ".join(s["transfer_stations"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines: %s" % ", ".join(s["lines"]))
    out.append("Estimated time: %.0f minutes" % s["estimated_time_min"])
    out.append("Fare: %d yuan" % s["fare"])
    return "\n".join(out)


def to_json(s):
    return json.dumps(s, ensure_ascii=False, indent=2)
