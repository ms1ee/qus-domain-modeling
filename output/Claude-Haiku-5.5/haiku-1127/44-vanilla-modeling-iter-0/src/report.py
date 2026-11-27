"""
Path visualization and export.

Renders a Route as console text or as a structured JSON document, builds the
path summary (distance in km, fare, transfers, estimated time), and appends
rendered reports to output files.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from pathfinding import (
    MODE_COMPREHENSIVE,
    MODE_LEAST_TRANSFER,
    MODE_SHORTEST_DISTANCE,
)
from route_planner import Route

MODE_LABELS = {
    MODE_SHORTEST_DISTANCE: "Shortest distance",
    MODE_LEAST_TRANSFER: "Minimum transfers",
    MODE_COMPREHENSIVE: "Comprehensive optimal",
}
SEPARATOR = "=" * 60


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_km: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_min: float


@dataclass
class Report:
    """A rendered report."""

    format: str
    content: str
    output_file: str | None = None


def build_summary(route: Route) -> PathSummary:
    """Extract the path summary from a route."""
    return PathSummary(
        total_distance_km=route.total_distance_m / 1000.0,
        total_fare_yuan=route.fare_yuan,
        transfer_count=route.transfer_count,
        estimated_time_min=route.estimated_time_min,
    )


def format_distance(distance_m: float) -> str:
    """Show short distances in meters and long distances in kilometers (with meters)."""
    if distance_m < 1000:
        return f"{distance_m:.0f} m"
    return f"{distance_m / 1000.0:.2f} km ({distance_m:.0f} m)"


def format_text(route: Route) -> str:
    """Render the route as console-formatted text."""
    summary = build_summary(route)
    max_transfers = "unlimited" if route.max_transfers is None else str(route.max_transfers)
    preference = ", ".join(route.line_preference) if route.line_preference else "none"

    lines = [
        SEPARATOR,
        f"Query: {route.start_station} -> {route.end_station}",
        f"Mode: {MODE_LABELS.get(route.mode, route.mode)}",
        f"Max transfers: {max_transfers}",
        f"Line preference: {preference}",
        "",
        f"Route ({route.station_count} stations):",
    ]
    for index, name in enumerate(route.stations, start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("")
    lines.append("Line segments:")
    if not route.segments:
        lines.append("  (no travel required)")
    for segment in route.segments:
        lines.append(
            f"  [{segment.line}] {segment.start_station} -> {segment.end_station} "
            f"({segment.segment_count} segment(s), {format_distance(segment.distance_m)})"
        )

    lines.append("")
    lines.append("Transfers:")
    if not route.transfers:
        lines.append("  None")
    for transfer in route.transfers:
        lines.append(f"  {transfer.station}: {transfer.from_line} -> {transfer.to_line}")

    lines.append("")
    lines.append(f"Total distance: {format_distance(summary.total_distance_km * 1000)}")
    lines.append(f"Transfers required: {summary.transfer_count}")
    lines.append(f"Lines involved: {', '.join(route.lines) if route.lines else 'none'}")
    lines.append(f"Estimated time: {summary.estimated_time_min:.1f} min")
    lines.append(f"Fare: {summary.total_fare_yuan} yuan")
    lines.append(SEPARATOR)
    return "\n".join(lines)


def route_to_dict(route: Route) -> dict:
    """Convert a route into a JSON-serialisable dictionary."""
    summary = build_summary(route)
    return {
        "query": {
            "start_station": route.start_station,
            "end_station": route.end_station,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": list(route.line_preference),
        },
        "path": list(route.stations),
        "station_count": route.station_count,
        "total_distance_m": round(route.total_distance_m, 2),
        "total_distance_km": round(summary.total_distance_km, 3),
        "fare_yuan": summary.total_fare_yuan,
        "estimated_time_min": round(summary.estimated_time_min, 2),
        "transfer_count": summary.transfer_count,
        "lines": list(route.lines),
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "segments": [
            {
                "line": s.line,
                "start_station": s.start_station,
                "end_station": s.end_station,
                "segment_count": s.segment_count,
                "distance_m": round(s.distance_m, 2),
            }
            for s in route.segments
        ],
    }


def format_json(route: Route, indent: int | None = 2) -> str:
    """Render the route as a JSON document."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=indent)


def render_report(route: Route, fmt: str, compact: bool = False) -> Report:
    """Render a route in the requested format ('text' or 'json').

    Args:
        route: The route to render.
        fmt: 'text' or 'json'.
        compact: For JSON, produce a single-line document (used for file export).
    """
    if fmt == "json":
        return Report(format="json", content=format_json(route, indent=None if compact else 2))
    if fmt == "text":
        return Report(format="text", content=format_text(route))
    raise ValueError(f"Unsupported output format '{fmt}'")


def export_report(report: Report, output_file: str) -> None:
    """Append a rendered report to a file, creating parent directories if needed.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(report.content)
        handle.write("\n")
    report.output_file = output_file
