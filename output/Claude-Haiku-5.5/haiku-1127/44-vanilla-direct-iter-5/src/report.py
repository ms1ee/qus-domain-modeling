"""Path visualization and export: console text, JSON and summaries."""
from __future__ import annotations

import json
from typing import Any

from pathfinding import RouteResult


def format_distance(meters: float) -> str:
    """Format a distance: meters for short trips, kilometers for long trips."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_summary(route: RouteResult, fare: int, estimated_time: float) -> dict[str, Any]:
    """Extract the key figures of a route."""
    return {
        "total_distance_km": round(route.distance_m / 1000.0, 3),
        "total_fare": fare,
        "transfer_count": route.transfers,
        "estimated_time_min": estimated_time,
    }


def format_text_report(route: RouteResult, fare: int, estimated_time: float) -> str:
    """Render a console-friendly text report."""
    out: list[str] = []
    out.append("=" * 60)
    out.append(f"Route: {route.start} -> {route.end}")
    out.append(f"Mode: {route.mode}")
    out.append("-" * 60)
    out.append(f"Stations ({len(route.station_names)}):")
    for i, name in enumerate(route.station_names, 1):
        out.append(f"  {i:>3}. {name}")
    out.append("Line segments:")
    segments = route.segments()
    if segments:
        for line, stations in segments:
            out.append(f"  [{line}] {' -> '.join(stations)}")
    else:
        out.append("  (none)")
    out.append("Transfer stations:")
    if route.transfer_stations:
        for station, from_line, to_line in route.transfer_stations:
            out.append(f"  - {station}: {from_line} -> {to_line}")
    else:
        out.append("  (none)")
    out.append(f"Lines involved: {', '.join(route.lines) if route.lines else 'none'}")
    out.append("-" * 60)
    out.append(f"Total distance: {format_distance(route.distance_m)}")
    out.append(f"Transfers: {route.transfers}")
    out.append(f"Estimated time: {estimated_time:.1f} min")
    out.append(f"Fare: {fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def build_report_dict(route: RouteResult, fare: int, estimated_time: float) -> dict[str, Any]:
    """Build the structured (JSON-serialisable) report."""
    return {
        "query": {"start": route.start, "end": route.end, "mode": route.mode},
        "path": route.station_names,
        "distance": {
            "meters": round(route.distance_m, 1),
            "kilometers": round(route.distance_m / 1000.0, 3),
        },
        "fare": fare,
        "estimated_time_min": estimated_time,
        "transfer_count": route.transfers,
        "lines": route.lines,
        "transfer_stations": [
            {"station": station, "from_line": f_line, "to_line": t_line}
            for station, f_line, t_line in route.transfer_stations
        ],
        "segments": [
            {"line": line, "stations": stations} for line, stations in route.segments()
        ],
        "summary": build_summary(route, fare, estimated_time),
    }


def format_json_report(route: RouteResult, fare: int, estimated_time: float) -> str:
    """Render the structured report as an indented JSON string."""
    return json.dumps(build_report_dict(route, fare, estimated_time),
                      ensure_ascii=False, indent=2)


def write_report(content: str, path: str, append: bool = True) -> None:
    """Write a rendered report to a file (UTF-8).

    Raises:
        OSError: if the file cannot be written.
    """
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(content)
        fh.write("\n")
