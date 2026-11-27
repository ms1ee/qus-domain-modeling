"""Path visualization and report export.

Builds console text reports and structured JSON reports from a ``RouteResult``.
"""

import os
from typing import Any, Dict, List, Sequence

from fare_calculator import calculate_estimated_time
from models import Edge
from pathfinding import RouteResult


def format_distance(meters: float) -> str:
    """Format a distance showing meters for short and kilometers for long trips.

    Examples: ``850 m (0.85 km)`` and ``12.35 km (12350 m)``.
    """
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_segments(station_names: Sequence[str], edges: Sequence[Edge]) -> List[Dict[str, Any]]:
    """Group consecutive stations travelled on the same line into segments."""
    if not edges:
        return []
    segments: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {"line": edges[0].line, "stations": [station_names[0]]}
    for index, edge in enumerate(edges):
        if edge.line != current["line"]:
            segments.append(current)
            current = {"line": edge.line, "stations": [station_names[index]]}
        current["stations"].append(station_names[index + 1])
    segments.append(current)
    for segment in segments:
        segment["start"] = segment["stations"][0]
        segment["end"] = segment["stations"][-1]
        segment["stops"] = len(segment["stations"]) - 1
    return segments


def find_transfers(station_names: Sequence[str], edges: Sequence[Edge]) -> List[Dict[str, str]]:
    """Identify transfer stations where the travelled line changes."""
    transfers: List[Dict[str, str]] = []
    for index in range(1, len(edges)):
        if edges[index - 1].line != edges[index].line:
            transfers.append(
                {
                    "station": station_names[index],
                    "from_line": edges[index - 1].line,
                    "to_line": edges[index].line,
                }
            )
    return transfers


def summarize_route(route: RouteResult, fare: int) -> Dict[str, Any]:
    """Extract key route information (distance, fare, transfers, time)."""
    distance = route.total_distance
    return {
        "distance_meters": distance,
        "distance_kilometers": round(distance / 1000.0, 2),
        "fare": fare,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": round(
            calculate_estimated_time(distance, route.transfer_count), 1
        ),
        "station_count": len(route.station_numbers),
        "lines": list(route.lines),
    }


def render_text_report(query: Dict[str, Any], route: RouteResult,
                       station_names: Sequence[str], fare: int) -> str:
    """Render a human-readable console report."""
    summary = summarize_route(route, fare)
    max_transfers = query.get("max_transfers")
    preference = query.get("line_preference")
    lines: List[str] = [
        "=" * 56,
        "Beijing Subway Fare Query Result",
        "=" * 56,
        f"Starting station : {query.get('start')}",
        f"Ending station   : {query.get('end')}",
        f"Query mode       : {query.get('mode')}",
        f"Max transfers    : {max_transfers if max_transfers is not None else 'unlimited'}",
        f"Line preference  : {preference if preference else 'none'}",
        "",
        f"Station sequence ({len(station_names)} stations):",
    ]
    for index, name in enumerate(station_names, start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("")
    lines.append("Line segments:")
    segments = build_segments(station_names, route.edges)
    if segments:
        for segment in segments:
            lines.append(
                f"  [{segment['line']}] {segment['start']} -> {segment['end']} "
                f"({segment['stops']} stops)"
            )
    else:
        lines.append("  (no travel required)")

    lines.append("")
    lines.append("Transfers:")
    transfers = find_transfers(station_names, route.edges)
    if transfers:
        for transfer in transfers:
            lines.append(
                f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )
    else:
        lines.append("  No transfer required")

    lines.append("")
    lines.append(f"Lines involved   : {', '.join(route.lines) if route.lines else 'none'}")
    lines.append(f"Total distance   : {format_distance(route.total_distance)}")
    lines.append(f"Transfer count   : {route.transfer_count}")
    lines.append(f"Estimated time   : {summary['estimated_time_minutes']} minutes")
    lines.append(f"Fare: {fare} yuan")
    return "\n".join(lines)


def build_json_report(query: Dict[str, Any], route: RouteResult,
                      station_names: Sequence[str], fare: int) -> Dict[str, Any]:
    """Build a structured report suitable for programmatic integration."""
    summary = summarize_route(route, fare)
    return {
        "query": query,
        "path": list(station_names),
        "distance": {
            "meters": summary["distance_meters"],
            "kilometers": summary["distance_kilometers"],
        },
        "fare": fare,
        "estimated_time_minutes": summary["estimated_time_minutes"],
        "transfer_count": route.transfer_count,
        "transfers": find_transfers(station_names, route.edges),
        "lines": list(route.lines),
        "segments": build_segments(station_names, route.edges),
    }


def export_report(content: str, path: str) -> None:
    """Write report content to a file (UTF-8), creating parent folders if needed.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n")
