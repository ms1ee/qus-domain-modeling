"""Route visualization and export (console text and JSON)."""

import json

from fare_calculator import format_fare

MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Least transfer",
    "comprehensive": "Comprehensive optimal",
}


def format_distance(meters):
    """Format a distance using an appropriate unit."""
    if meters < 1000:
        return "%d m" % round(meters)
    return "%.2f km" % (meters / 1000.0)


def summarize_route(route):
    """Extract key information from a route."""
    return {
        "total_distance_m": route.total_distance,
        "total_distance_km": round(route.total_distance / 1000.0, 2),
        "fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": route.estimated_time,
    }


def format_text_report(route):
    """Return a console-formatted report for a route."""
    out = ["=" * 56]
    out.append("Route: %s -> %s" % (route.start, route.end))
    mode = route.query.get("mode")
    if mode:
        out.append("Query mode: %s" % MODE_LABELS.get(mode, mode))
    out.append("-" * 56)
    out.append("Station sequence (%d stations):" % len(route.stations))
    out.append("  " + " -> ".join(route.stations))
    out.append("")
    out.append("Route details:")
    for i, seg in enumerate(route.segments):
        out.append("  %d. [%s] %s -> %s (%d stop%s, %s)" % (
            seg.order, seg.line, seg.stations[0], seg.stations[-1], seg.stop_count,
            "" if seg.stop_count == 1 else "s", format_distance(seg.distance)))
        out.append("     " + " -> ".join(seg.stations))
        if i < len(route.segments) - 1:
            out.append("     >> Transfer at %s: %s -> %s" % (
                seg.stations[-1], seg.line, route.segments[i + 1].line))
    out.append("")
    out.append("Total distance: %d meters (%.2f km)" % (round(route.total_distance),
                                                       route.total_distance / 1000.0))
    if route.transfer_count:
        out.append("Transfers: %d (at %s)" % (route.transfer_count, ", ".join(route.transfer_stations)))
    else:
        out.append("Transfers: 0 (direct)")
    out.append("Lines involved: %s" % ", ".join(route.lines))
    out.append("Estimated time: %.1f minutes" % route.estimated_time)
    out.append(format_fare(route.fare))
    out.append("=" * 56)
    return "\n".join(out)


def build_json_report(route):
    """Return a JSON-serializable dict describing a route."""
    return {
        "query": dict(route.query),
        "path": list(route.stations),
        "segments": [{"order": s.order, "line": s.line, "stations": list(s.stations),
                      "distance": s.distance, "stops": s.stop_count} for s in route.segments],
        "distance": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 2),
        "fare": route.fare,
        "fare_text": format_fare(route.fare),
        "estimated_time": route.estimated_time,
        "transfer_count": route.transfer_count,
        "transfer_stations": list(route.transfer_stations),
        "lines": list(route.lines),
    }


def format_json_report(route):
    return json.dumps(build_json_report(route), ensure_ascii=False, indent=2)


def generate_report(route, fmt="text"):
    """Generate a report in the requested format ("text" or "json")."""
    if fmt == "json":
        return format_json_report(route)
    return format_text_report(route)


def export_reports(routes, path, fmt="text"):
    """Write one or more route reports to a file."""
    with open(path, "w", encoding="utf-8") as handle:
        if fmt == "json":
            items = [build_json_report(r) for r in routes]
            payload = items[0] if len(items) == 1 else items
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        else:
            handle.write("\n\n".join(format_text_report(r) for r in routes))
            handle.write("\n")
