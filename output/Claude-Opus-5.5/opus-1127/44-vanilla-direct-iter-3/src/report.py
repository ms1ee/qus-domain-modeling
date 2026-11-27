"""Route visualization and export (console text and JSON)."""

import json

MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Least transfers",
    "comprehensive": "Comprehensive optimal",
}


def format_distance(meters):
    """Meters for short distances, kilometers for long ones (both shown)."""
    km = meters / 1000.0
    m = int(round(meters))
    if meters < 1000:
        return "%d meters (%.2f km)" % (m, km)
    return "%.2f km (%d meters)" % (km, m)


def build_segments(edges, name_of):
    segments = []
    for e in edges:
        if not segments or segments[-1]["line"] != e.line:
            segments.append({"line": e.line, "stations": [name_of(e.source)], "distance": 0})
        segments[-1]["stations"].append(name_of(e.dest))
        segments[-1]["distance"] += e.weight
    return segments


def build_route_info(start, end, mode, station_numbers, edges, distance, fare,
                     estimated_time, transfer_count, graph, config=None):
    name_of = graph.get_station_name
    stations = [name_of(n) for n in station_numbers]
    segments = build_segments(edges, name_of)
    transfers = []
    for a, b in zip(segments, segments[1:]):
        transfers.append({"station": b["stations"][0], "from_line": a["line"], "to_line": b["line"]})
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": mode,
            "max_transfers": getattr(config, "max_transfers", None),
            "line_preference": list(getattr(config, "preferred_lines", []) or []),
        },
        "path": stations,
        "station_count": len(stations),
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 3)},
        "fare": fare,
        "estimated_time_minutes": round(estimated_time, 1),
        "transfer_count": transfer_count,
        "transfers": transfers,
        "lines": lines,
        "segments": segments,
    }


def format_text(info):
    q = info["query"]
    out = []
    out.append("=" * 60)
    out.append("Route: %s -> %s  [%s]" % (q["start"], q["end"], MODE_LABELS.get(q["mode"], q["mode"])))
    out.append("-" * 60)
    out.append("Stations (%d): %s" % (info["station_count"], " -> ".join(info["path"])))
    out.append("Line segments:")
    for i, seg in enumerate(info["segments"]):
        out.append("  [%s] %s  (%d stops, %s)" % (
            seg["line"], " -> ".join(seg["stations"]), len(seg["stations"]) - 1,
            format_distance(seg["distance"])))
        if i < len(info["transfers"]):
            t = info["transfers"][i]
            out.append("  >> Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("Total distance: %s" % format_distance(info["distance"]["meters"]))
    if info["transfers"]:
        out.append("Transfers: %d (at %s)" % (
            info["transfer_count"], ", ".join(t["station"] for t in info["transfers"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines involved: %s" % ", ".join(str(l) for l in info["lines"]))
    out.append("Estimated time: %.1f minutes" % info["estimated_time_minutes"])
    out.append("Fare: %d yuan" % info["fare"])
    out.append("=" * 60)
    return "\n".join(out)


def format_json(info):
    return json.dumps(info, ensure_ascii=False, indent=2)


def format_summary(info):
    return "%s -> %s: %.2f km, %d transfer(s), ~%.1f min, Fare: %d yuan" % (
        info["query"]["start"], info["query"]["end"], info["distance"]["kilometers"],
        info["transfer_count"], info["estimated_time_minutes"], info["fare"])
