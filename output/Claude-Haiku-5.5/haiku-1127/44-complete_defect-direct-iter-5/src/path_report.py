"""Path visualisation and export helpers.

Builds a structured summary of a route (stations, segments, transfers, distance,
fare, estimated time) and renders it as console text or JSON.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge


def format_distance(distance_m: float) -> str:
    """Format a distance using meters for short and kilometers for long distances."""
    if distance_m < 1000:
        return f"{distance_m:.0f} m"
    return f"{distance_m / 1000.0:.2f} km"


def format_distance_both(distance_m: float) -> str:
    """Format a distance showing both the primary unit and its conversion."""
    if distance_m < 1000:
        return f"{distance_m:.0f} m ({distance_m / 1000.0:.2f} km)"
    return f"{distance_m / 1000.0:.2f} km ({distance_m:.0f} m)"


def find_transfers(stations: Sequence[str], edges: Sequence[Edge]) -> List[Dict[str, str]]:
    """Identify transfer stations, where the travelling line changes."""
    transfers: List[Dict[str, str]] = []
    for i in range(1, len(edges)):
        prev_line = edges[i - 1].line
        next_line = edges[i].line
        if prev_line != next_line:
            transfers.append(
                {"station": stations[i], "from_line": prev_line, "to_line": next_line}
            )
    return transfers


def build_segments(stations: Sequence[str], edges: Sequence[Edge]) -> List[Dict[str, Any]]:
    """Group consecutive edges operated by the same line into segments."""
    segments: List[Dict[str, Any]] = []
    if not edges:
        return segments
    start = 0
    for i in range(1, len(edges) + 1):
        if i == len(edges) or edges[i].line != edges[start].line:
            segments.append(
                {
                    "line": edges[start].line,
                    "from": stations[start],
                    "to": stations[i],
                    "station_count": i - start + 1,
                    "distance_m": sum(e.distance for e in edges[start:i]),
                }
            )
            start = i
    return segments


def build_summary(query: Dict[str, Any], stations: Sequence[str], edges: Sequence[Edge]) -> Dict[str, Any]:
    """Create the structured path summary.

    Args:
        query: Query information (start, end, mode, max_transfers, line_preference).
        stations: Station names from start to end.
        edges: Edges traversed between consecutive stations.

    Returns:
        A JSON-serialisable dictionary describing the route.

    Raises:
        ValueError: If the station and edge lists are inconsistent.
    """
    if len(stations) != len(edges) + 1:
        raise ValueError("Inconsistent route: stations and edges do not match")

    distance = sum(e.distance for e in edges)
    transfers = find_transfers(stations, edges)
    lines: List[str] = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)

    fare = Sum_money(distance)
    estimated = calculate_estimated_time(distance, len(transfers))

    return {
        "query": dict(query),
        "path": list(stations),
        "distance_m": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(estimated, 2),
        "transfer_count": len(transfers),
        "transfers": transfers,
        "lines": lines,
        "segments": build_segments(stations, edges),
    }


def format_text(summary: Dict[str, Any]) -> str:
    """Render a summary as console-friendly text."""
    query = summary["query"]
    out: List[str] = []
    out.append(f"Route: {query['start']} -> {query['end']}")
    out.append(f"Query mode: {query['mode']}")
    out.append("")

    out.append(f"Station sequence ({len(summary['path'])} stations):")
    for index, name in enumerate(summary["path"], start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for seg in summary["segments"]:
        out.append(
            f"  - {seg['line']}: {seg['from']} -> {seg['to']} "
            f"({seg['station_count']} stations, {format_distance(seg['distance_m'])})"
        )
    out.append("")

    out.append(f"Total distance: {format_distance_both(summary['distance_m'])}")
    out.append(f"Transfers: {summary['transfer_count']}")
    if summary["transfers"]:
        out.append("Transfer stations:")
        for t in summary["transfers"]:
            out.append(f"  - {t['station']}: {t['from_line']} -> {t['to_line']}")
    out.append("Lines involved: " + ", ".join(summary["lines"]))
    out.append(f"Estimated travel time: {summary['estimated_time_min']:.1f} min")
    out.append(f"Fare: {summary['fare']} yuan")
    return "\n".join(out)


def format_json(summary: Dict[str, Any]) -> str:
    """Render a summary as indented JSON."""
    return json.dumps(summary, ensure_ascii=False, indent=2)
