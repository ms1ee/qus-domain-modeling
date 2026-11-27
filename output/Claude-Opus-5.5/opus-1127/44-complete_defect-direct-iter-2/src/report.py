"""Path visualization, summary and export."""

import json


def format_distance(meters):
    """Meters for short distances, kilometres for long distances."""
    if meters < 1000:
        return "%d meters" % round(meters)
    return "%.2f km" % (meters / 1000.0)


def build_segments(station_names, edges):
    """Group consecutive edges on the same line into segments."""
    segments = []
    for i, edge in enumerate(edges):
        if segments and segments[-1]["line"] == edge.line:
            seg = segments[-1]
            seg["stations"].append(station_names[i + 1])
            seg["distance"] += edge.distance
        else:
            segments.append({
                "line": edge.line,
                "stations": [station_names[i], station_names[i + 1]],
                "distance": edge.distance,
            })
    return segments


def build_result(start, end, mode, station_names, edges, distance, fare, estimated_time, transfer_count):
    segments = build_segments(station_names, edges)
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    transfers = []
    for i in range(1, len(segments)):
        transfers.append({
            "station": segments[i]["stations"][0],
            "from_line": segments[i - 1]["line"],
            "to_line": segments[i]["line"],
        })
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": list(station_names),
        "station_count": len(station_names),
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "estimated_time": estimated_time,
        "transfer_count": transfer_count,
        "lines": lines,
        "transfers": transfers,
        "segments": segments,
    }


def format_text(result):
    out = []
    q = result["query"]
    out.append("=" * 50)
    out.append("Route: %s -> %s (mode: %s)" % (q["start"], q["end"], q["mode"]))
    out.append("-" * 50)
    out.append("Station sequence (%d stations):" % result["station_count"])
    out.append("  " + " -> ".join(result["path"]))
    out.append("Line segments:")
    for i, seg in enumerate(result["segments"]):
        if i > 0:
            t = result["transfers"][i - 1]
            out.append("  ** Transfer at %s: %s -> %s **" % (t["station"], t["from_line"], t["to_line"]))
        out.append("  [%s] %s (%d stops, %s)" % (
            seg["line"], " -> ".join(seg["stations"]), len(seg["stations"]) - 1, format_distance(seg["distance"])))
    meters = result["distance"]["meters"]
    out.append("Total distance: %d meters (%.2f km) [%s]" % (round(meters), meters / 1000.0, format_distance(meters)))
    out.append("Transfers: %d" % result["transfer_count"])
    if result["transfers"]:
        out.append("Transfer stations: " + ", ".join(t["station"] for t in result["transfers"]))
    out.append("Lines involved: " + ", ".join(str(l) for l in result["lines"]))
    out.append("Estimated time: %.1f minutes" % result["estimated_time"])
    out.append("Fare: %d yuan" % result["fare"])
    out.append("=" * 50)
    return "\n".join(out)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)
