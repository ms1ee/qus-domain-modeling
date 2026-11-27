"""
Path visualization and export (text and JSON) plus route summary generation.
"""

import json


def format_distance(meters):
    """Human-readable distance: meters for short trips, kilometers for long."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{int(round(meters))} meters ({km:.2f} km)"
    return f"{km:.2f} km ({int(round(meters))} meters)"


def build_segments(path_names, edges, number_to_station):
    """Group consecutive edges on the same line into segments."""
    segments = []
    for e in edges:
        src = number_to_station[e.source]
        dst = number_to_station[e.dest]
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["stations"].append(dst)
            seg["distance"] += e.distance
        else:
            segments.append({"line": e.line, "stations": [src, dst], "distance": e.distance})
    for seg in segments:
        seg["stops"] = len(seg["stations"]) - 1
    return segments


def build_route_result(start, end, mode, path_nodes, edges, number_to_station,
                       distance, fare, estimated_time, transfer_count):
    """Build a structured route summary dict."""
    path_names = [number_to_station[n] for n in path_nodes]
    segments = build_segments(path_names, edges, number_to_station)
    transfer_stations = []
    for i in range(1, len(segments)):
        transfer_stations.append({
            "station": segments[i]["stations"][0],
            "from_line": segments[i - 1]["line"],
            "to_line": segments[i]["line"],
        })
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": path_names,
        "station_count": len(path_names),
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "estimated_time": estimated_time,
        "transfer_count": transfer_count,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def format_text(result):
    """Console-formatted text report."""
    q = result["query"]
    out = ["=" * 60,
           f"Route: {q['start']} -> {q['end']}  (mode: {q['mode']})",
           "-" * 60,
           f"Station sequence ({result['station_count']} stations):",
           "  " + " -> ".join(result["path"]),
           "Line segments:"]
    for i, seg in enumerate(result["segments"]):
        if i > 0:
            ts = result["transfer_stations"][i - 1]
            out.append(f"  * Transfer at {ts['station']}: {ts['from_line']} -> {ts['to_line']}")
        out.append(f"  [{seg['line']}] {' -> '.join(seg['stations'])} "
                   f"({seg['stops']} stops, {format_distance(seg['distance'])})")
    out.append(f"Total distance: {format_distance(result['distance']['meters'])}")
    ts_names = ", ".join(t["station"] for t in result["transfer_stations"]) or "none"
    out.append(f"Transfers: {result['transfer_count']} (transfer stations: {ts_names})")
    out.append(f"Lines involved: {', '.join(result['lines'])}")
    out.append(f"Estimated time: {result['estimated_time']} minutes")
    out.append(f"Fare: {result['fare']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(result):
    """JSON report for programmatic integration."""
    return json.dumps(result, ensure_ascii=False, indent=2)


def summarize(result):
    """Key information summary."""
    return {
        "total_distance_km": result["distance"]["kilometers"],
        "fare": result["fare"],
        "transfer_count": result["transfer_count"],
        "estimated_time": result["estimated_time"],
    }
