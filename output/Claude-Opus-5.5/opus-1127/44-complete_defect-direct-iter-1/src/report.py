"""
Path visualization and export: builds route reports and renders them as
console text or JSON.
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time, format_fare


def format_distance(meters):
    """Meters for short distances, kilometers for long ones (both shown)."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{int(round(meters))} meters ({km:.2f} km)"
    return f"{km:.2f} km ({int(round(meters))} meters)"


def build_segments(edges):
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e["line"]:
            seg = segments[-1]
            seg["to"] = e["dest"]
            seg["stations"].append(e["dest"])
            seg["distance"] += e["distance"]
        else:
            segments.append({"line": e["line"], "from": e["source"], "to": e["dest"],
                             "stations": [e["source"], e["dest"]],
                             "distance": e["distance"]})
    return segments


class FareError(Exception):
    pass


def build_route_report(start, end, route, config):
    """Create the structured report dict from a route computed by SubwayNetwork."""
    distance = route["distance"]
    segments = build_segments(route["edges"])
    transfer_stations = [seg["to"] for seg in segments[:-1]]
    transfer_count = len(transfer_stations)
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    try:
        fare = Sum_money(distance)
    except (TypeError, ValueError) as exc:
        raise FareError(str(exc)) from exc
    est = calculate_estimated_time(distance, transfer_count)
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": list(route["stations"]),
        "station_count": len(route["stations"]),
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "estimated_time": est,
        "estimated_time_unit": "minutes",
        "transfer_count": transfer_count,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": [
            {"line": s["line"], "from": s["from"], "to": s["to"],
             "stations": s["stations"], "stops": len(s["stations"]) - 1,
             "distance": s["distance"]}
            for s in segments
        ],
    }


def summarize(report):
    """Key information summary of a report."""
    return {
        "total_distance_km": report["distance"]["kilometers"],
        "total_fare": report["fare"],
        "transfer_count": report["transfer_count"],
        "estimated_time_minutes": report["estimated_time"],
    }


def format_text_report(report):
    q = report["query"]
    sep = "=" * 60
    out = [sep, f"Route: {q['start']} -> {q['end']}", f"Mode: {q['mode']}"]
    if q["max_transfers"] is not None:
        out.append(f"Max transfers: {q['max_transfers']}")
    if q["line_preference"]:
        out.append(f"Line preference: {', '.join(q['line_preference'])}")
    out.append("-" * 60)
    out.append(f"Station sequence ({report['station_count']} stations):")
    out.append("  " + " -> ".join(report["path"]))
    out.append("Line segments:")
    segs = report["segments"]
    for i, s in enumerate(segs, 1):
        out.append(f"  {i}. [{s['line']}] {s['from']} -> {s['to']} "
                   f"({s['stops']} stops, {format_distance(s['distance'])})")
        if i < len(segs):
            out.append(f"     >> Transfer at {s['to']}: {s['line']} -> {segs[i]['line']}")
    ts = report["transfer_stations"]
    out.append(f"Transfer stations: {', '.join(ts) if ts else 'None'}")
    out.append(f"Lines involved: {', '.join(report['lines'])}")
    out.append(f"Number of transfers: {report['transfer_count']}")
    out.append(f"Total distance: {format_distance(report['distance']['meters'])}")
    out.append(f"Estimated time: {report['estimated_time']} minutes")
    out.append(format_fare(report["fare"]))
    out.append(sep)
    return "\n".join(out)


def format_json_report(report):
    return json.dumps(report, ensure_ascii=False, indent=2)
