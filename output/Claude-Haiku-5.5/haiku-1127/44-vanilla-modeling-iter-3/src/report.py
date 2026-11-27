"""Rendering of query results as console text or JSON, plus summaries."""

from __future__ import annotations

import json
from typing import Any, Dict

from query_service import QueryResult

MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Minimum transfers",
    "comprehensive": "Comprehensive optimal",
}


def format_distance(meters: float) -> str:
    """Format a distance: meters for short trips, kilometers for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_summary(result: QueryResult) -> Dict[str, Any]:
    """Extract the key figures of a query result."""
    return {
        "total_distance_km": round(result.total_distance_m / 1000.0, 3),
        "total_fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_minutes": round(result.estimated_time_min, 1),
    }


def build_report_dict(result: QueryResult) -> Dict[str, Any]:
    """Build the structured (JSON-serialisable) report."""
    return {
        "query": {
            "start_station": result.start_station,
            "end_station": result.end_station,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.line_preference,
        },
        "path": {
            "stations": result.stations,
            "segments": [
                {
                    "start_station": seg.start_station,
                    "end_station": seg.end_station,
                    "line": seg.line,
                    "distance_m": round(seg.distance_m, 1),
                }
                for seg in result.segments
            ],
            "transfers": [
                {
                    "station": t.station_name,
                    "from_line": t.from_line,
                    "to_line": t.to_line,
                }
                for t in result.transfers
            ],
        },
        "distance_m": round(result.total_distance_m, 1),
        "distance_km": round(result.total_distance_m / 1000.0, 3),
        "fare_yuan": result.fare,
        "estimated_time_minutes": round(result.estimated_time_min, 1),
        "transfer_count": result.transfer_count,
        "involved_lines": result.involved_lines,
        "summary": build_summary(result),
    }


def format_json(result: QueryResult) -> str:
    """Render the result as an indented JSON document."""
    return json.dumps(build_report_dict(result), ensure_ascii=False, indent=2)


def format_text(result: QueryResult) -> str:
    """Render the result as a human-readable console report."""
    out = []
    rule = "=" * 60
    out.append(rule)
    out.append("Beijing Subway Fare Query Result")
    out.append(rule)
    out.append(f"From: {result.start_station}")
    out.append(f"To:   {result.end_station}")
    out.append(f"Mode: {MODE_LABELS.get(result.mode, result.mode)}")
    max_text = "unlimited" if result.max_transfers is None else str(result.max_transfers)
    out.append(f"Max transfers: {max_text}")
    preference = ", ".join(result.line_preference) if result.line_preference else "none"
    out.append(f"Line preference: {preference}")
    out.append("")

    out.append(f"Station sequence ({len(result.stations)} stations):")
    transfer_by_station = {t.station_name: t for t in result.transfers}
    for index, name in enumerate(result.stations, start=1):
        note = ""
        if name in transfer_by_station:
            t = transfer_by_station[name]
            note = f"   [transfer: {t.from_line} -> {t.to_line}]"
        out.append(f"  {index:>3}. {name}{note}")
    out.append("")

    out.append("Line segments:")
    if result.segments:
        for seg in result.segments:
            out.append(
                f"  [{seg.line}] {seg.start_station} -> {seg.end_station}: "
                f"{format_distance(seg.distance_m)}"
            )
    else:
        out.append("  (none)")
    out.append("")

    out.append(f"Transfers ({result.transfer_count}):")
    if result.transfers:
        for t in result.transfers:
            out.append(f"  - At {t.station_name}: {t.from_line} -> {t.to_line}")
    else:
        out.append("  None")
    out.append("")

    out.append(f"Involved lines: {', '.join(result.involved_lines)}")
    out.append(f"Total distance: {format_distance(result.total_distance_m)}")
    out.append(f"Estimated time: ~{result.estimated_time_min:.1f} min")
    out.append(f"Fare: {result.fare} yuan")
    out.append(rule)
    return "\n".join(out)
