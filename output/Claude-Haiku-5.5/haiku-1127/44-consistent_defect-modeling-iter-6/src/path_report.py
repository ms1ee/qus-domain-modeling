"""
Path visualisation, summary generation and report export.

Builds a PathSummary from a RouteResult and renders it as console text or
as structured JSON, and writes reports to files.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass
from typing import Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import RouteResult


@dataclass
class QueryInfo:
    """Information about a user query, included in reports."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: Optional[str]
    timestamp: datetime.datetime


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_m: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_min: float


@dataclass
class Report:
    """A rendered report."""

    format: str
    content: str
    output_file: Optional[str] = None


def build_summary(route: RouteResult) -> PathSummary:
    """Compute the path summary (distance, fare, transfers, estimated time)."""
    distance = route.total_distance_m
    return PathSummary(
        total_distance_m=distance,
        total_fare_yuan=Sum_money(distance),
        transfer_count=route.transfer_count,
        estimated_time_min=calculate_estimated_time(distance, route.transfer_count),
    )


def format_distance(distance_m: float) -> str:
    """Format a distance: meters for short distances, meters plus kilometers for long ones."""
    if distance_m < 1000:
        return f"{distance_m:.0f} m"
    return f"{distance_m:.0f} m ({distance_m / 1000:.2f} km)"


def format_minutes(minutes: float) -> str:
    """Format a duration in minutes."""
    return f"{minutes:.1f} min"


def build_text_report(query: QueryInfo, route: RouteResult, summary: PathSummary) -> str:
    """Render a console-formatted report."""
    out = []
    out.append("Beijing Subway Fare Query")
    out.append("=" * 40)
    out.append(f"Start station : {query.start_station}")
    out.append(f"End station   : {query.end_station}")
    out.append(f"Query mode    : {query.mode}")
    out.append(f"Max transfers : {query.max_transfers if query.max_transfers is not None else 'unlimited'}")
    out.append(f"Line preference: {query.line_preference or 'none'}")
    out.append("")
    out.append("Station sequence (end -> start):")
    for index, name in enumerate(reversed(route.station_names), start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("")
    out.append("Line segments:")
    if route.segments:
        for seg in route.segments:
            out.append(
                f"  - {seg.line_name}: {seg.station_count} stations, {format_distance(seg.distance_m)}"
            )
    else:
        out.append("  (none)")
    out.append("")
    out.append("Transfers:")
    if route.transfers:
        for t in route.transfers:
            out.append(f"  - {t.station_name}: {t.from_line} -> {t.to_line}")
    else:
        out.append("  None (no transfer required)")
    out.append("")
    out.append(f"Lines involved : {', '.join(route.lines) if route.lines else 'none'}")
    out.append(f"Total distance : {format_distance(summary.total_distance_m)}")
    out.append(f"Transfer count : {summary.transfer_count}")
    out.append(f"Estimated time : {format_minutes(summary.estimated_time_min)}")
    out.append(f"Fare: {summary.total_fare_yuan} yuan")
    return "\n".join(out)


def build_json_report(query: QueryInfo, route: RouteResult, summary: PathSummary) -> str:
    """Render a structured JSON report for programmatic use."""
    data = {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
            "timestamp": query.timestamp.isoformat(timespec="seconds"),
        },
        "path": {
            "stations": route.station_names,
            "station_count": len(route.station_names),
            "segments": [
                {
                    "line": seg.line_name,
                    "station_count": seg.station_count,
                    "distance_m": seg.distance_m,
                }
                for seg in route.segments
            ],
        },
        "distance_m": round(summary.total_distance_m, 1),
        "distance_km": round(summary.total_distance_m / 1000.0, 3),
        "fare_yuan": summary.total_fare_yuan,
        "estimated_time_min": round(summary.estimated_time_min, 2),
        "transfer_count": summary.transfer_count,
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines": route.lines,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_report(query: QueryInfo, route: RouteResult, summary: PathSummary, fmt: str = "text") -> Report:
    """Render a report in the requested format ('text' or 'json')."""
    if fmt == "json":
        content = build_json_report(query, route, summary)
    elif fmt == "text":
        content = build_text_report(query, route, summary)
    else:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return Report(format=fmt, content=content)


def export_report(report: Report, path: str) -> str:
    """Write a report to a file, creating parent directories if needed.

    Returns:
        The absolute path of the written file.
    """
    target = os.path.abspath(os.fspath(path))
    directory = os.path.dirname(target)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(report.content)
        if not report.content.endswith("\n"):
            fh.write("\n")
    report.output_file = target
    return target
