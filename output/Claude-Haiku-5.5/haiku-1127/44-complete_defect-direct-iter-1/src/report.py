"""Path visualization and export: console text, JSON and path summaries."""

import json


def format_distance(distance_m):
    """Format a distance using meters for short trips and kilometers for long trips.

    Short distances (< 1000 m) are shown in meters followed by kilometers;
    longer distances are shown in kilometers followed by meters.
    """
    if distance_m < 1000:
        return f"{distance_m} m ({distance_m / 1000:.2f} km)"
    return f"{distance_m / 1000:.2f} km ({distance_m} m)"


def generate_path_summary(result):
    """Extract key summary information from a query result.

    Returns:
        dict with total_distance_km, total_fare, transfer_count and estimated_time_min.
    """
    return {
        "total_distance_km": result["distance_km"],
        "total_fare": result["fare"],
        "transfer_count": result["transfer_count"],
        "estimated_time_min": result["estimated_time_min"],
    }


def format_text_report(result):
    """Render a query result as human-readable console text."""
    summary = generate_path_summary(result)
    query = result["query"]
    separator = "-" * 60
    lines = []

    lines.append("=" * 60)
    lines.append(f"Route: {query['start']} -> {query['end']}")
    lines.append(f"Mode: {query['mode']}")
    if query["max_transfers"] is not None:
        lines.append(f"Max transfers: {query['max_transfers']}")
    if query["preferred_lines"]:
        lines.append("Preferred lines: " + ", ".join(query["preferred_lines"]))
    lines.append(separator)

    lines.append(f"Stations ({len(result['path'])}):")
    for index, name in enumerate(result["path"], start=1):
        lines.append(f"  {index:>3}. {name}")
    lines.append(separator)

    lines.append("Line segments:")
    for segment in result["segments"]:
        stops = len(segment["stations"]) - 1
        lines.append(
            f"  [{segment['line']}] {segment['stations'][0]} -> {segment['stations'][-1]}"
            f" ({stops} stops, {format_distance(segment['distance_m'])})"
        )

    lines.append("Transfers:")
    if not result["transfers"]:
        lines.append("  None (direct travel)")
    else:
        for transfer in result["transfers"]:
            lines.append(
                f"  {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )
    lines.append("Lines involved: " + ", ".join(result["lines"]))
    lines.append(separator)

    lines.append(f"Total distance: {format_distance(result['distance_m'])}")
    lines.append(f"Transfer count: {summary['transfer_count']}")
    lines.append(f"Estimated time: {summary['estimated_time_min']} min")
    lines.append(f"Fare: {result['fare']} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json_report(result):
    """Render a query result as an indented JSON document."""
    return json.dumps(result, ensure_ascii=False, indent=2)


def render_result(result, output_format):
    """Render a result in the requested format ("text" or "json")."""
    if output_format == "json":
        return format_json_report(result)
    return format_text_report(result)
