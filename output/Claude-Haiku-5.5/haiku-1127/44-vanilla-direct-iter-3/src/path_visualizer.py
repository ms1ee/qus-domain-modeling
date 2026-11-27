"""Path visualization, summary generation and report export (text and JSON)."""

import json


MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Minimum transfers",
    "comprehensive": "Comprehensive optimal",
}


def format_distance(distance_m) -> str:
    """Format a distance in meters and kilometers.

    Short distances (< 1 km) are shown primarily in meters, longer distances
    primarily in kilometers. Both units are always shown.
    """
    if distance_m < 1000:
        return f"{distance_m:.0f} m ({distance_m / 1000:.2f} km)"
    return f"{distance_m / 1000:.2f} km ({distance_m:.0f} m)"


def build_summary(route) -> dict:
    """Extract key figures from a route: distance, fare, transfers and time."""
    return {
        "total_distance_m": route.distance_m,
        "total_distance_km": round(route.distance_m / 1000.0, 2),
        "total_fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": round(route.estimated_time_min, 1),
    }


def format_text(route) -> str:
    """Render a route as a console-formatted text report."""
    out = []
    rule = "=" * 64
    out.append(rule)
    out.append(f"Route: {route.start} -> {route.end}")
    out.append(f"Query mode: {MODE_LABELS.get(route.mode, route.mode)}")
    if route.max_transfers is not None:
        out.append(f"Max transfers: {route.max_transfers}")
    if route.preferred_lines:
        out.append(f"Line preference: {', '.join(route.preferred_lines)}")
    out.append("-" * 64)

    out.append(f"Station sequence ({len(route.station_names)} stations):")
    for index, name in enumerate(route.station_names, start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for segment in route.segments:
        stations = segment["stations"]
        stops = len(stations) - 1
        out.append(
            f"  [{segment['line']}] {stations[0]} -> {stations[-1]} ({stops} stops)"
        )
    out.append("")

    out.append("Transfer stations:")
    if route.transfer_details:
        for transfer in route.transfer_details:
            all_lines = ", ".join(transfer["all_lines"])
            out.append(
                f"  {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
                f"  (interchange lines: {all_lines})"
            )
    else:
        out.append("  None (no transfer required)")
    out.append("")

    out.append(f"Lines involved: {', '.join(route.lines)}")
    out.append("-" * 64)
    out.append(f"Total distance: {format_distance(route.distance_m)}")
    out.append(f"Transfers: {route.transfer_count}")
    out.append(f"Estimated time: {route.estimated_time_min:.1f} min")
    out.append(f"Fare: {route.fare} yuan")
    out.append(rule)
    return "\n".join(out)


def to_json_dict(route) -> dict:
    """Build the structured (JSON-serialisable) representation of a route."""
    summary = build_summary(route)
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.preferred_lines,
        },
        "path": route.station_names,
        "segments": [
            {"line": segment["line"], "stations": segment["stations"]}
            for segment in route.segments
        ],
        "distance": {
            "meters": route.distance_m,
            "kilometers": summary["total_distance_km"],
        },
        "fare": route.fare,
        "estimated_time_min": summary["estimated_time_min"],
        "transfer_count": route.transfer_count,
        "transfer_stations": route.transfer_details,
        "lines": route.lines,
        "summary": summary,
    }


def to_json(route) -> str:
    """Render a route as a JSON string."""
    return json.dumps(to_json_dict(route), ensure_ascii=False, indent=2)


def render(route, fmt="text") -> str:
    """Render a route in the requested format ('text' or 'json')."""
    if fmt == "json":
        return to_json(route)
    if fmt == "text":
        return format_text(route)
    raise ValueError(f"Unsupported output format '{fmt}'")
