"""Path visualisation and report export.

Renders a ``QueryResult`` as console text or as structured JSON.
"""

import json
from dataclasses import dataclass

from .fare_calculator import calculate_estimated_time  # noqa: F401  (documented dependency)

SUPPORTED_FORMATS = ("text", "json")


@dataclass
class Report:
    """A rendered report."""

    format: str
    content: str


def format_distance(meters):
    """Format a distance in both meters and kilometers."""
    return f"{meters:.0f} m ({meters / 1000.0:.2f} km)"


def render_text(result):
    """Render a query result as human-readable console text."""
    query = result.query
    route = result.route
    summary = result.summary
    lines = []
    lines.append("=" * 50)
    lines.append("Beijing Subway Route")
    lines.append("=" * 50)
    lines.append(f"From: {query.origin_station}")
    lines.append(f"To:   {query.destination_station}")
    lines.append(f"Mode: {query.mode}")
    if query.max_transfers is not None:
        lines.append(f"Max transfers: {query.max_transfers}")
    if query.line_preference:
        lines.append(f"Line preference: {query.line_preference}")
    lines.append("")
    lines.append("Station sequence (end -> start):")
    lines.append("  " + " -> ".join(route.station_sequence))
    lines.append("")
    lines.append("Route segments:")
    for segment in route.segments:
        lines.append(
            f"  - {segment.line_name}: {format_distance(segment.distance_meters)}, "
            f"{segment.station_count} stations"
        )
    lines.append("")
    lines.append(f"Total distance: {format_distance(summary.total_distance_meters)}")
    lines.append(f"Transfers: {summary.transfer_count}")
    if route.transfers:
        lines.append("Transfer details:")
        for transfer in route.transfers:
            lines.append(
                f"  - Transfer at {transfer.station_name}: "
                f"{transfer.from_line} -> {transfer.to_line}"
            )
    else:
        lines.append("Transfer details: none")
    lines.append("Lines involved: " + (", ".join(route.lines_involved) or "none"))
    lines.append(f"Estimated time: {summary.estimated_time_minutes:.1f} minutes")
    lines.append(f"Fare: {summary.total_fare_yuan} yuan")
    lines.append("=" * 50)
    return "\n".join(lines)


def result_to_dict(result):
    """Convert a query result to a JSON-serialisable dictionary."""
    query = result.query
    route = result.route
    summary = result.summary
    return {
        "query": {
            "origin_station": query.origin_station,
            "destination_station": query.destination_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(route.stations),
        "distance_meters": round(summary.total_distance_meters, 1),
        "fare_yuan": summary.total_fare_yuan,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        "transfer_count": summary.transfer_count,
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines_involved": route.lines_involved,
        "segments": [
            {
                "line": seg.line_name,
                "distance_meters": round(seg.distance_meters, 1),
                "station_count": seg.station_count,
            }
            for seg in route.segments
        ],
    }


def render_json(result):
    """Render a query result as a JSON string."""
    return json.dumps(result_to_dict(result), ensure_ascii=False, indent=2)


def make_report(result, fmt="text"):
    """Create a ``Report`` in the requested format ("text" or "json")."""
    if fmt == "text":
        return Report(format="text", content=render_text(result))
    if fmt == "json":
        return Report(format="json", content=render_json(result))
    raise ValueError(f"Unsupported output format '{fmt}'; expected one of {SUPPORTED_FORMATS}")
