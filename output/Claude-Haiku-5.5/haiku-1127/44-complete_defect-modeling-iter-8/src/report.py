"""Path visualization and multi-format report export."""

import json
import os
from dataclasses import dataclass
from datetime import datetime

SUPPORTED_FORMATS = ("text", "json")


@dataclass
class Report:
    """A rendered path report.

    Attributes:
        format: "text" or "json".
        content: Rendered report content.
        output_file: Optional file path the report should be exported to.
    """

    format: str
    content: str
    output_file: str = None


def make_query(start, end, mode, max_transfers=None, line_preference=None):
    """Build the query information dictionary used by the renderers."""
    return {
        "start_station": start,
        "end_station": end,
        "mode": mode,
        "max_transfers": max_transfers,
        "line_preference": line_preference,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def format_distance(meters):
    """Format a distance showing meters for short and kilometers for long distances."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters:.0f} m ({km:.2f} km)"
    return f"{km:.2f} km ({meters:.0f} m)"


def summarize_route(route):
    """Extract key summary information from a route."""
    return {
        "total_distance_km": round(route.total_distance_km, 2),
        "total_fare_yuan": route.fare_yuan,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": route.estimated_time_minutes,
    }


def render_text(route, query):
    """Render the route as console-formatted text."""
    out = []
    out.append(f"Query: {query['start_station']} -> {query['end_station']}")
    settings = [f"mode={query['mode']}"]
    if query.get("max_transfers") is not None:
        settings.append(f"max_transfers={query['max_transfers']}")
    if query.get("line_preference"):
        settings.append(f"line_preference={query['line_preference']}")
    out.append("Settings: " + ", ".join(settings))
    out.append("")

    out.append(f"Station sequence ({len(route.station_sequence)} stations):")
    for index, station in enumerate(route.station_sequence, start=1):
        out.append(f"  {index}. {station}")
    out.append("")

    out.append("Line segments:")
    for segment in route.segments:
        out.append(
            f"  [{segment['line']}] {segment['start']} -> {segment['end']} "
            f"({format_distance(segment['distance_meters'])})"
        )
    out.append("")

    out.append("Transfer details:")
    if route.transfers:
        for transfer in route.transfers:
            out.append(
                f"  Transfer station '{transfer['station']}': "
                f"{transfer['from_line']} -> {transfer['to_line']}"
            )
    else:
        out.append("  No transfers required")
    out.append("")

    out.append(f"Total distance: {format_distance(route.total_distance_meters)}")
    out.append(f"Transfers: {route.transfer_count}")
    out.append(f"Lines involved: {', '.join(route.involved_lines)}")
    out.append(f"Estimated time: {route.estimated_time_minutes:.1f} minutes")
    out.append(f"Fare: {route.fare_yuan} yuan")
    return "\n".join(out)


def render_json(route, query):
    """Render the route as a JSON document for programmatic integration."""
    payload = {
        "query": {
            "start_station": query["start_station"],
            "end_station": query["end_station"],
            "mode": query["mode"],
            "max_transfers": query.get("max_transfers"),
            "line_preference": query.get("line_preference"),
            "timestamp": query.get("timestamp"),
        },
        "path": route.station_sequence,
        "distance_meters": round(route.total_distance_meters, 2),
        "distance_km": round(route.total_distance_km, 2),
        "fare_yuan": route.fare_yuan,
        "estimated_time_minutes": route.estimated_time_minutes,
        "transfer_count": route.transfer_count,
        "involved_lines": route.involved_lines,
        "transfers": route.transfers,
        "segments": route.segments,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report(route, query, fmt="text", output_file=None):
    """Render a route in the requested format and wrap it in a Report.

    Raises:
        ValueError: If the format is not supported.
    """
    if fmt == "text":
        content = render_text(route, query)
    elif fmt == "json":
        content = render_json(route, query)
    else:
        raise ValueError(f"Unsupported format '{fmt}', expected one of {SUPPORTED_FORMATS}")
    return Report(format=fmt, content=content, output_file=output_file)


def export_report(report):
    """Append the report content to its output file (if one is set).

    Returns:
        The output file path, or None if no output file is configured.

    Raises:
        OSError: If the file cannot be written.
    """
    if not report.output_file:
        return None
    directory = os.path.dirname(os.path.abspath(report.output_file))
    os.makedirs(directory, exist_ok=True)
    with open(report.output_file, "a", encoding="utf-8") as handle:
        handle.write(report.content)
        handle.write("\n\n")
    return report.output_file
