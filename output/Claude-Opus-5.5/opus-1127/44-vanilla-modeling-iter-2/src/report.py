"""
Route visualisation and export (console text and JSON).
"""

import json


def format_distance(meters):
    """Use meters for short distances (< 1 km), kilometers otherwise."""
    if meters < 1000:
        return f"{int(meters)} meters"
    return f"{meters / 1000.0:.2f} km"


def format_distance_both(meters):
    if meters < 1000:
        return f"{int(meters)} meters ({meters / 1000.0:.2f} km)"
    return f"{meters / 1000.0:.2f} km ({int(meters)} meters)"


def format_fare(fare):
    return f"Fare: {fare} yuan"


def summarize_route(route):
    """Key information of a route."""
    return {
        "total_distance_m": route.total_distance,
        "total_distance_km": round(route.total_distance / 1000.0, 3),
        "fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": round(route.estimated_time, 1),
    }


def build_text_report(route, config=None):
    """Console formatted report with segments, transfers and fare."""
    sep = "=" * 60
    sub = "-" * 60
    lines = [sep, f"Route: {route.start} -> {route.end}", f"Mode: {route.mode}"]
    if config is not None:
        if getattr(config, "max_transfers", None) is not None:
            lines.append(f"Max transfers: {config.max_transfers}")
        if getattr(config, "preferred_lines", None):
            lines.append(f"Line preference: {', '.join(config.preferred_lines)}")
    lines.append(sub)
    lines.append(f"Stations ({len(route.station_sequence)}): " + " -> ".join(route.station_sequence))
    lines.append("Line segments:")
    for i, seg in enumerate(route.segments, 1):
        stops = len(seg.stations) - 1
        lines.append(f"  {i}. [{seg.line}] " + " -> ".join(seg.stations)
                     + f" ({stops} stop{'s' if stops != 1 else ''}, {format_distance(seg.distance)})")
        if i <= len(route.transfers):
            tr = route.transfers[i - 1]
            lines.append(f"     >> Transfer at {tr.station}: {tr.from_line} -> {tr.to_line}")
    lines.append(sub)
    lines.append(f"Total distance: {format_distance_both(route.total_distance)}")
    if route.transfers:
        lines.append(f"Transfers: {route.transfer_count} (at "
                     + ", ".join(t.station for t in route.transfers) + ")")
    else:
        lines.append("Transfers: 0")
    lines.append("Lines involved: " + (", ".join(str(l) for l in route.involved_lines) or "-"))
    lines.append(f"Estimated time: {route.estimated_time:.1f} minutes")
    lines.append(format_fare(route.fare))
    lines.append(sep)
    return "\n".join(lines)


def build_json_report(route, config=None):
    """Structured (dict) report suitable for JSON export."""
    query = {"start": route.start, "end": route.end, "mode": route.mode}
    if config is not None:
        query["max_transfers"] = getattr(config, "max_transfers", None)
        query["line_preference"] = list(getattr(config, "preferred_lines", []) or [])
    return {
        "query": query,
        "path": list(route.station_sequence),
        "station_count": len(route.station_sequence),
        "distance": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 3),
        "fare": route.fare,
        "estimated_time": round(route.estimated_time, 1),
        "transfer_count": route.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line,
             "transfer_time": t.transfer_time, "transfer_distance": t.transfer_distance}
            for t in route.transfers
        ],
        "involved_lines": list(route.involved_lines),
        "segments": [
            {"line": s.line, "stations": list(s.stations), "distance": s.distance}
            for s in route.segments
        ],
    }


def render_report(route, fmt="text", config=None):
    if fmt == "json":
        return json.dumps(build_json_report(route, config), ensure_ascii=False, indent=2)
    return build_text_report(route, config)
