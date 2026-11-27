"""Path visualization and export: console text, JSON and summary generation."""

import json

MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Minimum transfers",
    "comprehensive": "Comprehensive optimal",
}


def format_distance(meters):
    """Format a distance: meters for short trips, meters plus kilometers for long trips."""
    if meters < 1000:
        return f"{meters} m"
    return f"{meters} m ({meters / 1000:.2f} km)"


def build_summary(result):
    """Extract key figures of a route as a dictionary (distance kept in meters)."""
    return {
        "total_distance_m": result.distance_m,
        "total_fare": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": round(result.estimated_time_min, 1),
    }


def to_json_dict(result):
    """Build the structured (JSON-serializable) representation of a route."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "start_input": result.start_input,
            "end_input": result.end_input,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": list(result.line_preference),
        },
        "path": list(result.stations),
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_m / 1000, 2),
        },
        "fare": result.fare,
        "estimated_time_min": round(result.estimated_time_min, 1),
        "transfer_count": result.transfer_count,
        "transfers": [dict(t) for t in result.transfers],
        "lines": list(result.lines),
        "summary": build_summary(result),
    }


def format_text(result):
    """Render a route as console-formatted text."""
    bar = "=" * 60
    out = [bar]
    out.append(f"Route: {result.start} -> {result.end}")
    out.append(f"Query mode: {MODE_LABELS.get(result.mode, result.mode)}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.line_preference:
        out.append("Line preference: " + ", ".join(result.line_preference))
    out.append("")

    out.append("Station sequence (listed from end to start):")
    for index, name in enumerate(reversed(result.stations), 1):
        out.append(f"  {index:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for line, stations in result.segments():
        out.append(f"  [{line}] " + " -> ".join(stations))
    out.append("")

    out.append(f"Total distance: {format_distance(result.distance_m)}")
    out.append(f"Transfers: {result.transfer_count}")
    out.append("Transfer details:")
    if result.transfers:
        for t in result.transfers:
            out.append(f"  - {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("  No transfers required")
    out.append("Lines involved: " + (", ".join(result.lines) if result.lines else "none"))
    out.append(f"Estimated time: {result.estimated_time_min:.1f} minutes")
    out.append(f"Fare: {result.fare} yuan")
    out.append(bar)
    return "\n".join(out)


def render(result, output_format):
    """Render a route for the console in the requested format ('text' or 'json')."""
    if output_format == "json":
        return json.dumps(to_json_dict(result), ensure_ascii=False, indent=2)
    return format_text(result)


def render_compact(result, output_format):
    """Render a route for file export: JSON Lines for json, text otherwise."""
    if output_format == "json":
        return json.dumps(to_json_dict(result), ensure_ascii=False)
    return format_text(result)
