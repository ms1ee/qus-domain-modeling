"""Path summary generation and report formatting (console text and JSON)."""

import json
import os
from dataclasses import dataclass

from fare_calculator import calculate_estimated_time


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_m: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A formatted path report."""

    format: str
    content: str
    output_file: str = None

    def write(self, path):
        """Write the report content to ``path`` and remember the location."""
        write_text_file(path, self.content)
        self.output_file = path
        return path


def build_summary(route):
    """Build a ``PathSummary`` from a ``Route`` (distance kept in meters)."""
    return PathSummary(
        total_distance_m=route.total_distance_m,
        total_fare_yuan=route.fare_yuan,
        transfer_count=route.transfer_count,
        estimated_time_minutes=calculate_estimated_time(route.total_distance_m,
                                                        route.transfer_count),
    )


def format_distance(meters):
    """Format a distance: meters for short distances, kilometres (and meters) for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km ({meters:.0f} m)"


def build_text_report(route):
    """Build the console-formatted text report of a route."""
    summary = build_summary(route)
    preference = ", ".join(route.line_preference) if route.line_preference else "none"
    output = [
        "=" * 60,
        "Beijing Subway Fare Report",
        "=" * 60,
        f"Starting station : {route.origin}",
        f"Ending station   : {route.destination}",
        f"Query mode       : {route.mode}",
        f"Max transfers    : {route.max_transfers}",
        f"Line preference  : {preference}",
        "",
        "Station sequence (end -> start):",
    ]
    for index, name in enumerate(reversed(route.station_names), start=1):
        output.append(f"  {index:>3}. {name}")

    output.extend([
        "",
        f"Total distance   : {format_distance(summary.total_distance_m)}",
        f"Transfers        : {summary.transfer_count}",
        f"Estimated time   : {summary.estimated_time_minutes:.1f} min",
        f"Lines involved   : {', '.join(route.lines)}",
        "",
        "Line segments (start -> end):",
    ])
    for segment in route.segments:
        output.append(f"  [{segment.line}] {segment.start} -> {segment.end} "
                      f"({segment.intervals} section(s))")

    output.append("")
    output.append("Transfer stations:")
    if route.transfers:
        for transfer in route.transfers:
            output.append(f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        output.append("  (none)")

    output.append("")
    output.append(f"Fare: {summary.total_fare_yuan} yuan")
    return "\n".join(output)


def build_json_report(route):
    """Build the structured (JSON-serializable) representation of a route."""
    summary = build_summary(route)
    return {
        "query": {
            "origin": route.origin,
            "destination": route.destination,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": list(route.line_preference) or None,
        },
        "path": list(reversed(route.station_names)),
        "path_start_to_end": list(route.station_names),
        "distance": {
            "meters": round(summary.total_distance_m, 2),
            "kilometers": round(summary.total_distance_m / 1000.0, 3),
        },
        "fare_yuan": summary.total_fare_yuan,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        "transfer_count": summary.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines": list(route.lines),
        "segments": [
            {"line": s.line, "from": s.start, "to": s.end, "intervals": s.intervals}
            for s in route.segments
        ],
    }


def build_report(route, fmt="text"):
    """Build a ``Report`` in the requested format (``text`` or ``json``)."""
    if fmt == "text":
        return Report(format="text", content=build_text_report(route))
    if fmt == "json":
        return Report(format="json",
                      content=json.dumps(build_json_report(route), ensure_ascii=False, indent=2))
    raise ValueError(f"Unsupported report format '{fmt}'")


def write_text_file(path, content):
    """Write text content to a file, creating parent directories if needed."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
