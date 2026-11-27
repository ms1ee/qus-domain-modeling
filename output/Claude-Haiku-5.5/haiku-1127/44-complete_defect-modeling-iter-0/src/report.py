"""Path visualization and export: console text, JSON and file output."""

import json
import os
from dataclasses import dataclass
from typing import Optional

from query_service import Route

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)
SHORT_DISTANCE_THRESHOLD_M = 1000.0


class ReportError(Exception):
    """Raised when a report cannot be generated or written."""


@dataclass
class Report:
    """A generated report.

    Attributes:
        format: "text" or "json".
        output_file_path: path the content was written to, or None.
        content: the formatted report text.
    """

    format: str
    output_file_path: Optional[str]
    content: str


def format_distance(distance_m):
    """Format a distance using meters for short trips and kilometers for long ones."""
    km = distance_m / 1000.0
    if distance_m < SHORT_DISTANCE_THRESHOLD_M:
        return "{:.0f} m ({:.2f} km)".format(distance_m, km)
    return "{:.2f} km ({:.0f} m)".format(km, distance_m)


def generate_summary(route):
    """Extract key figures of a route: distance in km, fare, transfers, time."""
    return {
        "total_distance_km": round(route.total_distance_m / 1000.0, 2),
        "fare_yuan": route.fare_yuan,
        "transfer_count": route.transfer_count,
        "estimated_time_min": round(route.estimated_time_min, 1),
    }


def format_text(route):
    """Render a route as console-friendly text."""
    out = []
    out.append("=" * 50)
    out.append("Beijing Subway Route Report")
    out.append("=" * 50)
    out.append("Starting station : {}".format(route.start_station))
    out.append("Ending station   : {}".format(route.end_station))
    out.append("Query mode       : {}".format(route.mode))
    out.append("Max transfers    : {}".format(
        "unlimited" if route.max_transfers is None else route.max_transfers))
    out.append("Line preference  : {}".format(
        ", ".join(route.line_preference) if route.line_preference else "none"))
    out.append("")
    out.append("Station sequence ({} stations):".format(len(route.stations)))
    transfer_map = {item["station"]: item for item in route.transfers}
    for index, name in enumerate(route.stations, 1):
        marker = ""
        if name in transfer_map:
            item = transfer_map[name]
            marker = "  [transfer: {} -> {}]".format(item["from_line"], item["to_line"])
        out.append("  {:>3}. {}{}".format(index, name, marker))
    out.append("")
    out.append("Total distance   : {}".format(format_distance(route.total_distance_m)))
    out.append("Transfers        : {}".format(route.transfer_count))
    out.append("Estimated time   : {:.1f} min".format(route.estimated_time_min))
    out.append("Lines involved   : {}".format(", ".join(route.lines)))
    out.append("")
    out.append("Route segments:")
    for line, segment_stations in route.segments:
        out.append("  {}: {}".format(line, " -> ".join(segment_stations)))
    if route.transfers:
        out.append("")
        out.append("Transfer stations:")
        for item in route.transfers:
            out.append("  {} ({} -> {})".format(item["station"], item["from_line"], item["to_line"]))
    out.append("")
    out.append("Fare: {} yuan".format(route.fare_yuan))
    return "\n".join(out)


def format_json(route):
    """Render a route as a JSON document for programmatic use."""
    payload = {
        "query": {
            "start_station": route.start_station,
            "end_station": route.end_station,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.line_preference,
        },
        "path": route.stations,
        "distance": {
            "meters": round(route.total_distance_m, 2),
            "kilometers": round(route.total_distance_m / 1000.0, 3),
        },
        "fare_yuan": route.fare_yuan,
        "estimated_time_min": round(route.estimated_time_min, 1),
        "transfer_count": route.transfer_count,
        "transfers": route.transfers,
        "lines": route.lines,
        "segments": [{"line": line, "stations": seg} for line, seg in route.segments],
        "summary": generate_summary(route),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_report(route, fmt=FORMAT_TEXT, output_file=None):
    """Generate a report in the requested format and optionally write it to a file.

    Raises:
        ReportError: for unsupported formats or file write failures.
    """
    if fmt == FORMAT_TEXT:
        content = format_text(route)
    elif fmt == FORMAT_JSON:
        content = format_json(route)
    else:
        raise ReportError("Unsupported output format '{}'".format(fmt))

    if output_file:
        try:
            directory = os.path.dirname(os.path.abspath(output_file))
            os.makedirs(directory, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as handle:
                handle.write(content + "\n")
        except OSError as exc:
            raise ReportError("Cannot write output file '{}': {}".format(output_file, exc)) from exc
    return Report(format=fmt, output_file_path=output_file or None, content=content)
