"""Path visualization, summary generation and report export."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

from models import Query, Route


def format_distance(meters: float) -> str:
    """Format a distance showing meters and kilometers, emphasizing the unit suited to its length."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters:.0f} m ({km:.2f} km)"
    return f"{km:.2f} km ({meters:.0f} m)"


def route_summary(route: Route) -> Dict[str, object]:
    """Extract key summary information from a route."""
    return {
        "total_distance_km": round(route.total_distance / 1000.0, 2),
        "total_distance_m": round(route.total_distance, 1),
        "fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": round(route.estimated_time, 1),
    }


def transfer_points(segments: List[Tuple[str, List[str]]]) -> List[Tuple[str, str, str]]:
    """Return (station, from_line, to_line) for each transfer between consecutive segments."""
    points = []
    for i in range(len(segments) - 1):
        station = segments[i][1][-1]
        points.append((station, segments[i][0], segments[i + 1][0]))
    return points


def format_text(route: Route, query: Query) -> str:
    """Render a console-friendly text report."""
    out: List[str] = []
    out.append("=" * 60)
    out.append(f"Query: {query.origin_station} -> {query.destination_station}")
    out.append(f"Mode: {query.mode}")
    if query.max_transfers is not None:
        out.append(f"Max transfers: {query.max_transfers}")
    if query.line_preference:
        out.append(f"Line preference: {query.line_preference}")
    out.append("-" * 60)

    out.append(f"Station sequence ({len(route.station_sequence)} stations):")
    for idx, name in enumerate(route.station_sequence, start=1):
        out.append(f"  {idx:>3}. {name}")

    out.append("")
    out.append("Line segments:")
    for line, stations in route.segments:
        out.append(f"  [{line}] " + " -> ".join(stations))

    transfers = transfer_points(route.segments)
    out.append("")
    out.append(f"Transfers ({len(transfers)}):")
    if transfers:
        for station, from_line, to_line in transfers:
            out.append(f"  At {station}: {from_line} -> {to_line}")
    else:
        out.append("  none")

    out.append("")
    out.append(f"Involved lines: {', '.join(route.involved_lines) if route.involved_lines else 'none'}")
    out.append(f"Total distance: {format_distance(route.total_distance)}")
    out.append(f"Transfer count: {route.transfer_count}")
    out.append(f"Estimated time: {route.estimated_time:.1f} minutes")
    out.append(f"Fare: {route.fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(route: Route, query: Query) -> str:
    """Render a structured JSON report for programmatic integration."""
    payload = {
        "query": {
            "raw_input": query.raw_input,
            "origin_station": query.origin_station,
            "destination_station": query.destination_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(route.station_sequence),
        "distance": {
            "meters": round(route.total_distance, 1),
            "kilometers": round(route.total_distance / 1000.0, 3),
        },
        "fare": route.fare,
        "estimated_time_minutes": round(route.estimated_time, 1),
        "transfer_count": route.transfer_count,
        "involved_lines": list(route.involved_lines),
        "segments": [{"line": line, "stations": stations} for line, stations in route.segments],
        "summary": route_summary(route),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render(route: Route, query: Query, fmt: str) -> str:
    """Render a route in the requested format ('text' or 'json')."""
    if fmt == "json":
        return format_json(route, query)
    if fmt == "text":
        return format_text(route, query)
    raise ValueError(f"unsupported output format '{fmt}'")


def write_report(content: str, output_file: str) -> None:
    """Append a rendered report to a file, creating parent directories if needed."""
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as fh:
        fh.write(content + "\n\n")
