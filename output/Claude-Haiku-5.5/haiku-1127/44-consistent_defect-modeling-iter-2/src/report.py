"""Path visualization and export: summaries, console text and JSON reports."""

import json
import os
from typing import Optional

from .fare_calculator import Sum_money, calculate_estimated_time
from .models import PathSummary, Query, Route


def build_summary(route: Route) -> PathSummary:
    """Extract the key figures of a route into a PathSummary."""
    fare = Sum_money(route.total_distance_meters)
    minutes = calculate_estimated_time(route.total_distance_meters, route.transfer_count)
    return PathSummary(
        total_distance_meters=route.total_distance_meters,
        total_fare=fare,
        transfer_count=route.transfer_count,
        estimated_time_minutes=minutes,
    )


def format_distance(meters: float) -> str:
    """Format a distance: meters for short trips, meters plus kilometers otherwise."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters:,.0f} m ({meters / 1000:.2f} km)"


def render_text(query: Query, route: Route, summary: PathSummary) -> str:
    """Render a console-formatted report of the route and fare."""
    out = []
    out.append("=== Beijing Subway Fare Query ===")
    out.append(f"From: {query.start_station}")
    out.append(f"To:   {query.end_station}")
    out.append(f"Mode: {query.mode}")
    if query.max_transfers is not None:
        out.append(f"Max transfers: {query.max_transfers}")
    if query.line_preference:
        out.append(f"Line preference: {query.line_preference}")
    out.append("")
    out.append(f"Station sequence ({len(route.station_sequence)} stations):")
    out.append("  " + " -> ".join(route.station_sequence))
    out.append("")
    out.append("Route segments:")
    for line, stations in route.segments:
        out.append(f"  [{line}] " + " -> ".join(stations))
    out.append("")
    if route.transfers:
        out.append("Transfers:")
        for station, from_line, to_line in route.transfers:
            out.append(f"  At {station}: {from_line} -> {to_line}")
    else:
        out.append("Transfers: none")
    out.append(f"Transfer count: {summary.transfer_count}")
    out.append(f"Lines involved: {', '.join(route.involved_lines)}")
    out.append("")
    out.append(f"Total distance: {format_distance(summary.total_distance_meters)}")
    out.append(f"Estimated time: {summary.estimated_time_minutes:.1f} min")
    out.append(f"Fare: {summary.total_fare} yuan")
    return "\n".join(out)


def render_json(query: Query, route: Route, summary: PathSummary) -> str:
    """Render the route and fare as a JSON document for programmatic use."""
    payload = {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(route.station_sequence),
        "distance_meters": round(summary.total_distance_meters, 2),
        "distance_km": round(summary.total_distance_meters / 1000.0, 3),
        "fare": summary.total_fare,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        "transfer_count": summary.transfer_count,
        "involved_lines": list(route.involved_lines),
        "segments": [
            {"line": line, "stations": list(stations)}
            for line, stations in route.segments
        ],
        "transfers": [
            {"station": station, "from_line": from_line, "to_line": to_line}
            for station, from_line, to_line in route.transfers
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_report(fmt: str, query: Query, route: Route, summary: PathSummary) -> str:
    """Render a report in the requested format ('text' or 'json')."""
    if fmt == "json":
        return render_json(query, route, summary)
    if fmt == "text":
        return render_text(query, route, summary)
    raise ValueError(f"unsupported output format '{fmt}'")


def write_report(content: str, output_file: str, append: bool = True) -> None:
    """Write report content to a file, creating parent directories if needed.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(output_file))
    if directory:
        os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(output_file, mode, encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")
