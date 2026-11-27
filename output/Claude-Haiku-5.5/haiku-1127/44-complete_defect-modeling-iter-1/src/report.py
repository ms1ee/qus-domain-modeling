"""Path visualization and report export.

Produces three representations of a query result:
  * console text (station sequence, segments, transfers, distance, fare),
  * structured JSON (query info, path, distance, fare, time, transfers, lines),
  * a path summary dictionary used by both formats.
"""

import json
from dataclasses import dataclass
from typing import Dict, Optional

from models import Route


@dataclass
class Report:
    """An exported report.

    Attributes:
        format: ``text`` or ``json``.
        content: Rendered report content.
        output_file: Destination file path, or None if not exported.
    """

    format: str
    content: str
    output_file: Optional[str] = None


def format_distance(meters: float) -> str:
    """Format a distance using meters for short trips and kilometers for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km"


def build_path_summary(route: Route, fare: int) -> Dict[str, object]:
    """Extract key figures from a route: distance in km, fare, transfers, time."""
    return {
        "total_distance_km": round(route.total_distance_km, 3),
        "total_fare": fare,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": route.estimated_time,
    }


def build_summary(route: Route, fare: int, query: Dict[str, object]) -> Dict[str, object]:
    """Build the structured summary used for JSON output."""
    return {
        "query": {
            "start": query.get("start"),
            "end": query.get("end"),
            "mode": query.get("mode"),
            "max_transfers": query.get("max_transfers"),
            "line_preference": query.get("line_preference"),
        },
        "path": list(route.station_sequence),
        "distance": {
            "meters": round(route.total_distance_m, 1),
            "kilometers": round(route.total_distance_km, 3),
        },
        "fare": fare,
        "fare_text": f"Fare: {fare} yuan",
        "estimated_time_minutes": route.estimated_time,
        "transfer_count": route.transfer_count,
        "lines": list(route.lines),
        "segments": [
            {
                "line": segment.line_name,
                "start": segment.start_station,
                "end": segment.end_station,
                "distance_m": round(segment.distance, 1),
            }
            for segment in route.segments
        ],
        "transfers": [
            {"station": station, "from_line": from_line, "to_line": to_line}
            for station, from_line, to_line in route.transfers
        ],
        "summary": build_path_summary(route, fare),
    }


def format_text(route: Route, fare: int, query: Dict[str, object]) -> str:
    """Render a human-readable console report."""
    transfer_stations = {station for station, _, _ in route.transfers}
    lines = []
    lines.append("=" * 60)
    lines.append(f"From: {query.get('start')}    To: {query.get('end')}")
    lines.append(f"Mode: {query.get('mode')}")
    lines.append("-" * 60)

    lines.append("Route segments:")
    for segment in route.segments:
        lines.append(
            f"  [{segment.line_name}] {segment.start_station} -> {segment.end_station} "
            f"({format_distance(segment.distance)})"
        )

    lines.append("Station sequence:")
    for index, name in enumerate(route.station_sequence, start=1):
        marker = "  (transfer station)" if name in transfer_stations else ""
        lines.append(f"  {index:>3}. {name}{marker}")

    lines.append("Transfers:")
    if route.transfers:
        for station, from_line, to_line in route.transfers:
            lines.append(f"  - {station}: {from_line} -> {to_line}")
    else:
        lines.append("  none")

    lines.append("-" * 60)
    lines.append(f"Total distance: {format_distance(route.total_distance_m)}")
    lines.append(f"Transfers required: {route.transfer_count}")
    lines.append(f"Estimated time: {route.estimated_time} minutes")
    lines.append(f"Lines involved: {', '.join(route.lines)}")
    lines.append(f"Fare: {fare} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(route: Route, fare: int, query: Dict[str, object]) -> str:
    """Render the structured JSON report."""
    return json.dumps(build_summary(route, fare, query), ensure_ascii=False, indent=2)


def write_report(content: str, output_file: str) -> Report:
    """Append rendered report content to ``output_file`` (UTF-8).

    Returns:
        A ``Report`` describing what was written.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n")
    return Report(format="file", content=content, output_file=output_file)
