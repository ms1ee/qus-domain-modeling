"""Path visualization, summary generation and report export (text and JSON)."""

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PathSummary:
    """Key figures extracted from a route result."""

    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A rendered report.

    Attributes:
        format: 'text' or 'json'.
        content: rendered report string.
        output_file_path: path the report was written to, if any.
    """

    format: str
    content: str
    output_file_path: Optional[str] = None


def summarize_route(result):
    """Build a PathSummary from a RouteResult."""
    return PathSummary(
        total_distance_km=result.total_distance_m / 1000.0,
        total_fare=result.fare,
        transfer_count=result.transfer_count,
        estimated_time_minutes=result.estimated_time_minutes,
    )


def format_distance(meters):
    """Format a distance: meters for short trips, kilometers for long trips."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km"


def _format_total_distance(meters):
    """Format the total distance in both meters and kilometers."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters:.0f} m ({km:.2f} km)"
    return f"{km:.2f} km ({meters:.0f} m)"


def format_text(result):
    """Render a console-friendly text report."""
    out = []
    add = out.append
    add("=" * 60)
    add("Beijing Subway Fare Query Result")
    add("=" * 60)
    add(f"Starting station : {result.start_station}")
    add(f"Ending station   : {result.end_station}")
    add(f"Query mode       : {result.mode}")
    max_t = "unlimited" if result.max_transfers is None else str(result.max_transfers)
    add(f"Max transfers    : {max_t}")
    pref = ", ".join(result.line_preference) if result.line_preference else "none"
    add(f"Line preference  : {pref}")
    add("")
    add(f"Station sequence ({len(result.stations)} stations):")
    for index, name in enumerate(result.stations, start=1):
        add(f"  {index:>3}. {name}")
    add("")
    add("Line segments:")
    for seg in result.segments:
        add(f"  [{seg.sequence_number}] {seg.line}: {seg.start_station} -> {seg.end_station} "
            f"({format_distance(seg.distance_m)}, {seg.station_count} stations)")
    add("")
    if result.transfers:
        add(f"Transfer stations ({len(result.transfers)}):")
        for t in result.transfers:
            add(f"  * {t.station}: {t.from_line} -> {t.to_line} "
                f"(lines at station: {', '.join(t.station_lines)})")
    else:
        add("Transfer stations: none")
    add("")
    add(f"Total distance   : {_format_total_distance(result.total_distance_m)}")
    add(f"Transfers        : {result.transfer_count}")
    add(f"Estimated time   : {result.estimated_time_minutes:.1f} minutes")
    add(f"Lines involved   : {', '.join(result.lines)}")
    add(f"Fare: {result.fare} yuan")
    add("=" * 60)
    return "\n".join(out)


def format_json(result):
    """Render a structured JSON report for programmatic use."""
    payload = {
        "query": {
            "start_station": result.start_station,
            "end_station": result.end_station,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.line_preference,
        },
        "path": result.stations,
        "segments": [
            {
                "sequence_number": seg.sequence_number,
                "line": seg.line,
                "start_station": seg.start_station,
                "end_station": seg.end_station,
                "distance_m": round(seg.distance_m, 2),
                "station_count": seg.station_count,
            }
            for seg in result.segments
        ],
        "distance": {
            "meters": round(result.total_distance_m, 2),
            "kilometers": round(result.total_distance_m / 1000.0, 3),
        },
        "fare": {"amount": result.fare, "currency": "CNY"},
        "estimated_time_minutes": round(result.estimated_time_minutes, 2),
        "transfer_count": result.transfer_count,
        "transfers": [
            {
                "station": t.station,
                "from_line": t.from_line,
                "to_line": t.to_line,
                "station_lines": t.station_lines,
            }
            for t in result.transfers
        ],
        "involved_lines": result.lines,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report(result, fmt="text"):
    """Render a RouteResult in the requested format ('text' or 'json')."""
    if fmt == "json":
        return Report(format="json", content=format_json(result))
    if fmt == "text":
        return Report(format="text", content=format_text(result))
    raise ValueError(f"Unsupported output format '{fmt}'")


def write_report(report, path):
    """Write a rendered report to a file (UTF-8). Overwrites existing content."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report.content)
        handle.write("\n")
    report.output_file_path = path
    return report
