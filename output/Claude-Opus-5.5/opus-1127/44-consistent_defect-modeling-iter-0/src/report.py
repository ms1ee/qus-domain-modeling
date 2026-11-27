"""
Path visualization and export (console text and JSON).
"""

import json


def format_distance(meters):
    """Display distance in meters and kilometers."""
    if meters < 1000:
        return f"{meters} meters ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters} meters)"


def route_summary(route):
    """Key information extracted from a route (distance kept in meters)."""
    return {
        "distance": route.total_distance,
        "fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time": round(route.estimated_time, 1),
    }


def route_to_dict(route):
    return {
        "query": {"start": route.start, "end": route.end, "mode": route.mode},
        "path": list(route.station_sequence),
        "distance": route.total_distance,
        "distance_km": round(route.total_distance / 1000, 3),
        "fare": route.fare,
        "estimated_time": round(route.estimated_time, 1),
        "transfer_count": route.transfer_count,
        "lines": list(route.involved_lines),
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "segments": [
            {"line": s["line"], "stations": list(s["stations"]), "distance": s["distance"]}
            for s in route.segments
        ],
    }


def format_json(route):
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=2)


def format_text(route):
    lines = []
    lines.append("=" * 50)
    lines.append(f"Route: {route.start} -> {route.end}  (mode: {route.mode})")
    lines.append("-" * 50)
    lines.append("Stations: " + " -> ".join(route.station_sequence))
    lines.append(f"Number of stations: {len(route.station_sequence)}")
    lines.append("Segments:")
    for i, seg in enumerate(route.segments, 1):
        lines.append(f"  {i}. [{seg['line']}] " + " -> ".join(seg["stations"])
                     + f" ({format_distance(seg['distance'])})")
    if route.transfers:
        lines.append("Transfers:")
        for t in route.transfers:
            lines.append(f"  Transfer at {t.station_name}: {t.from_line} -> {t.to_line}")
    else:
        lines.append("Transfers: none")
    lines.append("Lines involved: " + (", ".join(route.involved_lines) or "-"))
    lines.append(f"Total distance: {format_distance(route.total_distance)}")
    lines.append(f"Transfer count: {route.transfer_count}")
    lines.append(f"Estimated time: {route.estimated_time:.1f} minutes")
    lines.append(f"Fare: {route.fare} yuan")
    lines.append("=" * 50)
    return "\n".join(lines)


def format_route(route, fmt="text"):
    return format_json(route) if fmt == "json" else format_text(route)
