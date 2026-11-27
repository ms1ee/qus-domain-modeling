"""Route visualization and export (console text and JSON)."""

import json


def format_distance(meters):
    """Format a distance in both meters and kilometers."""
    km = meters / 1000.0
    if float(meters).is_integer():
        meters_text = f"{int(meters)} m"
    else:
        meters_text = f"{meters:.1f} m"
    return f"{meters_text} ({km:.2f} km)"


def format_text_report(route):
    """Return a console-formatted text report for a planned route."""
    query = route["query"]
    width = 60
    out = ["=" * width,
           f"Route: {query['start']} -> {query['end']}",
           f"Mode: {query['mode']}"]
    if query.get("max_transfers") is not None:
        out.append(f"Max transfers: {query['max_transfers']}")
    if query.get("line_preference"):
        out.append(f"Line preference: {', '.join(query['line_preference'])}")
    out.append("-" * width)
    out.append(f"Stations ({route['station_count']}):")
    out.append("  " + " -> ".join(route["path"]))
    out.append("")
    out.append("Segments:")
    segments = route["segments"]
    for i, seg in enumerate(segments):
        out.append(
            f"  [{seg['line']}] {seg['from']} -> {seg['to']} "
            f"({seg['stops']} stop(s), {format_distance(seg['distance'])})")
        out.append("      " + " - ".join(seg["stations"]))
        if i + 1 < len(segments):
            out.append(
                f"  >> Transfer at {seg['to']}: {seg['line']} -> {segments[i + 1]['line']}")
    out.append("-" * width)
    out.append(f"Total distance: {format_distance(route['distance']['meters'])}")
    transfers = route["transfer_count"]
    if transfers:
        out.append(f"Transfers: {transfers} (at {', '.join(route['transfer_stations'])})")
    else:
        out.append("Transfers: 0 (direct)")
    out.append(f"Lines involved: {', '.join(route['lines'])}")
    if route.get("estimated_time_minutes") is not None:
        out.append(f"Estimated time: {route['estimated_time_minutes']} min")
    out.append(route.get("fare_text") or f"Fare: {route['fare']} yuan")
    out.append("=" * width)
    return "\n".join(out)


def format_json_report(route_or_routes):
    """Return a JSON string for one route dict or a list of them."""
    return json.dumps(route_or_routes, ensure_ascii=False, indent=2)


def render(route, fmt="text"):
    if fmt == "json":
        return format_json_report(route)
    return format_text_report(route)


def build_summary(route):
    """Extract key summary information from a route."""
    return {
        "distance_km": route["distance"]["kilometers"],
        "fare": route["fare"],
        "transfer_count": route["transfer_count"],
        "estimated_time_minutes": route.get("estimated_time_minutes"),
    }
