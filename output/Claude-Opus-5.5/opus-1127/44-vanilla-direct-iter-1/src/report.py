"""Route visualization and export (console text and JSON)."""

import json


def format_distance(meters):
    """Meters for short distances (<1 km), kilometers otherwise."""
    if meters < 1000:
        return "%d meters" % round(meters)
    return "%.2f km" % (meters / 1000.0)


def format_fare(fare):
    return "Fare: %d yuan" % fare


def build_summary(route):
    return {
        "total_distance_km": round(route["distance"] / 1000.0, 3),
        "total_fare": route["fare"],
        "transfer_count": route["transfer_count"],
        "estimated_time_minutes": round(route["estimated_time"], 1),
    }


def to_json_dict(route):
    return {
        "query": {
            "start": route["start"],
            "end": route["end"],
            "mode": route["mode"],
            "max_transfers": route.get("max_transfers"),
            "line_preference": route.get("preferred_lines", []),
        },
        "path": route["path"],
        "station_count": len(route["path"]),
        "distance": {
            "meters": route["distance"],
            "kilometers": round(route["distance"] / 1000.0, 3),
        },
        "fare": route["fare"],
        "estimated_time": round(route["estimated_time"], 1),
        "transfer_count": route["transfer_count"],
        "transfer_stations": route["transfer_stations"],
        "lines": route["lines"],
        "segments": [
            {"line": s["line"], "stations": s["stations"], "distance": s["distance"]}
            for s in route["segments"]
        ],
        "summary": build_summary(route),
    }


def format_json(route):
    return json.dumps(to_json_dict(route), ensure_ascii=False, indent=2)


def format_text(route):
    lines = []
    lines.append("=" * 50)
    lines.append("Route: %s -> %s" % (route["start"], route["end"]))
    lines.append("Mode: %s" % route["mode"])
    lines.append("-" * 50)
    lines.append("Stations (%d): %s" % (len(route["path"]), " -> ".join(route["path"])))
    lines.append("Segments:")
    segs = route["segments"]
    for i, seg in enumerate(segs):
        lines.append("  [%s] %s (%d stops, %s)" % (
            seg["line"], " -> ".join(seg["stations"]),
            len(seg["stations"]) - 1, format_distance(seg["distance"])))
        if i + 1 < len(segs):
            lines.append("  >> Transfer at %s: %s -> %s" % (
                segs[i + 1]["stations"][0], seg["line"], segs[i + 1]["line"]))
    d = route["distance"]
    lines.append("Total distance: %s (%d meters, %.2f km)" % (
        format_distance(d), round(d), d / 1000.0))
    lines.append("Transfers: %d" % route["transfer_count"])
    if route["transfer_stations"]:
        lines.append("Transfer stations: %s" % ", ".join(route["transfer_stations"]))
    lines.append("Lines involved: %s" % ", ".join(str(x) for x in route["lines"]))
    lines.append("Estimated time: %.1f minutes" % route["estimated_time"])
    lines.append(format_fare(route["fare"]))
    lines.append("=" * 50)
    return "\n".join(lines)


def render(route, fmt="text"):
    return format_json(route) if fmt == "json" else format_text(route)
