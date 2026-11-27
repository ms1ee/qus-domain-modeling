"""Path visualization and report export.

Renders a ``Route`` as console text or structured JSON, builds path summaries
and writes reports to files.
"""

import json
import os

from models import Query, Report, Route

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)

SEPARATOR = "=" * 60
DIVIDER = "-" * 60


def format_distance(distance_m: float) -> str:
    """Format a distance: meters for short distances, kilometers for long ones.

    Examples: "850 m (0.85 km)" and "12.50 km (12500 m)".
    """
    if distance_m < 1000:
        return f"{distance_m:.0f} m ({distance_m / 1000:.2f} km)"
    return f"{distance_m / 1000:.2f} km ({distance_m:.0f} m)"


def build_summary(route: Route) -> dict:
    """Extract the key summary information of a route."""
    return {
        "total_distance_km": round(route.total_distance_m / 1000.0, 3),
        "total_distance_m": round(route.total_distance_m, 1),
        "total_fare_yuan": route.fare.amount_yuan,
        "transfer_count": route.transfer_count,
        "estimated_time_min": round(route.estimated_time_min, 1),
    }


def render_text(route: Route, query: Query) -> str:
    """Render the route as human-readable console text."""
    max_text = "unlimited" if query.max_transfers is None else str(query.max_transfers)
    preference = query.line_preference or "none"
    lines = [
        SEPARATOR,
        "Beijing Subway Fare Query Result",
        SEPARATOR,
        f"From: {route.start_station}",
        f"To: {route.end_station}",
        f"Mode: {route.mode}",
        f"Max transfers: {max_text}",
        f"Line preference: {preference}",
        DIVIDER,
        f"Station sequence ({len(route.stations)} stations):",
    ]
    for index, name in enumerate(route.stations, 1):
        lines.append(f"  {index:>3}. {name}")

    lines.append(DIVIDER)
    lines.append("Line segments:")
    for segment in route.segments:
        lines.append(
            f"  [{segment.line}] {segment.start_station} -> {segment.end_station} "
            f"({segment.stop_count} stops, {format_distance(segment.distance_m)})")

    lines.append(DIVIDER)
    lines.append("Transfer details:")
    if not route.transfers:
        lines.append("  None (direct route)")
    else:
        for index, transfer in enumerate(route.transfers, 1):
            lines.append(
                f"  {index}. {transfer.station_name}: {transfer.from_line} -> {transfer.to_line} "
                f"(lines involved: {', '.join(transfer.involved_lines)})")

    lines.append(DIVIDER)
    lines.append(f"Lines involved: {', '.join(route.lines)}")
    lines.append(f"Total distance: {format_distance(route.total_distance_m)}")
    lines.append(f"Transfer count: {route.transfer_count}")
    lines.append(f"Estimated time: {route.estimated_time_min:.1f} minutes")
    lines.append(f"Fare: {route.fare.amount_yuan} yuan")
    lines.append(SEPARATOR)
    return "\n".join(lines)


def render_json(route: Route, query: Query) -> str:
    """Render the route as a structured JSON document."""
    document = {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(route.stations),
        "distance_m": round(route.total_distance_m, 1),
        "distance_km": round(route.total_distance_m / 1000.0, 3),
        "fare_yuan": route.fare.amount_yuan,
        "rounded_distance_km": route.fare.rounded_distance_km,
        "estimated_time_min": round(route.estimated_time_min, 1),
        "transfer_count": route.transfer_count,
        "lines": route.lines,
        "transfers": [
            {
                "station": transfer.station_name,
                "from_line": transfer.from_line,
                "to_line": transfer.to_line,
            }
            for transfer in route.transfers
        ],
        "segments": [
            {
                "line": segment.line,
                "start_station": segment.start_station,
                "end_station": segment.end_station,
                "stations": list(segment.station_names),
                "distance_m": round(segment.distance_m, 1),
            }
            for segment in route.segments
        ],
        "summary": build_summary(route),
    }
    return json.dumps(document, indent=2, ensure_ascii=False)


def create_report(route: Route, query: Query, output_format: str = None) -> Report:
    """Create a ``Report`` in the requested format (defaults to the query's format).

    Raises:
        ValueError: If the format is not supported.
    """
    fmt = output_format or query.output_format or FORMAT_TEXT
    if fmt == FORMAT_TEXT:
        content = render_text(route, query)
    elif fmt == FORMAT_JSON:
        content = render_json(route, query)
    else:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return Report(format=fmt, content=content, output_file=query.output_file)


def export_report(report: Report, output_file: str) -> str:
    """Write the report content to ``output_file`` (UTF-8, overwriting).

    Returns:
        The path the report was written to.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as handle:
        handle.write(report.content)
        handle.write("\n")
    return output_file
