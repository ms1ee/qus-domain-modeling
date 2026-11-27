"""Path summary and report generation (console text and JSON)."""

import json
import os
from dataclasses import dataclass

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import (
    MODE_COMPREHENSIVE,
    MODE_LEAST_TRANSFER,
    MODE_SHORTEST_DISTANCE,
)

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)

MODE_DESCRIPTIONS = {
    MODE_SHORTEST_DISTANCE: "Shortest distance",
    MODE_LEAST_TRANSFER: "Minimum transfers",
    MODE_COMPREHENSIVE: "Comprehensive optimal",
}


class ReportError(Exception):
    """Raised when a report cannot be generated or written."""


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A generated report."""

    format: str
    content: str
    output_file_path: str = ""


def summarize_route(route):
    """Build a PathSummary from a Route (distance, fare, transfers, time)."""
    distance = route.total_distance_meters
    return PathSummary(
        total_distance_km=round(distance / 1000.0, 3),
        total_fare=Sum_money(distance),
        transfer_count=route.transfer_count,
        estimated_time_minutes=calculate_estimated_time(distance, route.transfer_count),
    )


def format_distance(meters):
    """Format a distance in both meters and kilometers."""
    return f"{meters:.0f} m ({meters / 1000.0:.2f} km)"


def format_text(start, end, route, summary, config):
    """Render the route as console-formatted text."""
    lines = []
    lines.append("=" * 60)
    lines.append("Beijing Subway Route Report")
    lines.append("=" * 60)
    lines.append(f"From: {start}")
    lines.append(f"To:   {end}")
    lines.append(f"Mode: {MODE_DESCRIPTIONS.get(config.mode, config.mode)}")
    max_text = "unlimited" if config.max_transfers is None else str(config.max_transfers)
    lines.append(f"Max transfers: {max_text}")
    preference = ", ".join(config.preferred_lines) if config.preferred_lines else "none"
    lines.append(f"Line preference: {preference}")
    lines.append("")
    lines.append(f"Stations ({len(route.station_sequence)}):")
    lines.append("  " + " -> ".join(route.station_sequence))
    lines.append("")
    lines.append("Line segments:")
    if not route.segments:
        lines.append("  (no travel required)")
    for index, seg in enumerate(route.segments, start=1):
        stops = len(seg.stations) - 1
        lines.append(
            f"  {index}. {seg.line}: {seg.start} -> {seg.end} "
            f"({stops} stops, {format_distance(seg.distance_meters)})"
        )
    lines.append("")
    lines.append("Transfers:")
    if not route.transfers:
        lines.append("  None")
    for transfer in route.transfers:
        lines.append(
            f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line} "
            f"(lines at station: {', '.join(transfer.all_lines)})"
        )
    lines.append("")
    lines.append(f"Total distance: {format_distance(route.total_distance_meters)}")
    lines.append(f"Transfer count: {summary.transfer_count}")
    lines.append(f"Estimated time: {summary.estimated_time_minutes:.1f} min")
    lines.append(f"Fare: {summary.total_fare} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(start, end, route, summary, config):
    """Render the route as a JSON document for programmatic use."""
    payload = {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": list(route.station_sequence),
        "distance_meters": round(route.total_distance_meters, 2),
        "distance_km": summary.total_distance_km,
        "fare": summary.total_fare,
        "estimated_time_minutes": summary.estimated_time_minutes,
        "transfer_count": summary.transfer_count,
        "involved_lines": route.involved_lines,
        "segments": [
            {
                "line": seg.line,
                "start": seg.start,
                "end": seg.end,
                "stops": len(seg.stations) - 1,
                "distance_meters": round(seg.distance_meters, 2),
            }
            for seg in route.segments
        ],
        "transfers": [
            {
                "station": t.station,
                "from_line": t.from_line,
                "to_line": t.to_line,
                "all_lines": list(t.all_lines),
            }
            for t in route.transfers
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report(fmt, start, end, route, config):
    """Generate a Report in the requested format.

    Raises:
        ReportError: if the format is unsupported.
    """
    if fmt not in SUPPORTED_FORMATS:
        raise ReportError(f"Unsupported output format '{fmt}'")
    summary = summarize_route(route)
    if fmt == FORMAT_JSON:
        content = format_json(start, end, route, summary, config)
    else:
        content = format_text(start, end, route, summary, config)
    return Report(format=fmt, content=content)


def write_report(report, output_file):
    """Write the report content to ``output_file`` (overwriting it).

    Returns:
        the path written.

    Raises:
        ReportError: if the file cannot be written.
    """
    try:
        directory = os.path.dirname(os.path.abspath(output_file))
        os.makedirs(directory, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as fh:
            fh.write(report.content)
            fh.write("\n")
    except OSError as exc:
        raise ReportError(f"Cannot write output file '{output_file}': {exc}") from exc
    report.output_file_path = output_file
    return output_file
