"""Path visualization, summary generation and report export."""

import json
import os

from pathfinding import (
    MODE_COMPREHENSIVE,
    MODE_LEAST_TRANSFER,
    MODE_SHORTEST,
)

MODE_LABELS = {
    MODE_SHORTEST: "Shortest-Distance Path",
    MODE_LEAST_TRANSFER: "Minimum-Transfer Path",
    MODE_COMPREHENSIVE: "Comprehensive Optimal Path",
}


def format_distance(meters):
    """Format a distance in meters and, when large enough, in kilometers."""
    if meters >= 1000:
        return f"{meters} m ({meters / 1000.0:.2f} km)"
    return f"{meters} m"


def build_segments(route):
    """Group the path into consecutive single-line segments.

    Returns:
        list[dict]: Each item has "line" and "stations" (ordered station names).
    """
    if not route.edges:
        return []
    names = route.station_names
    current = {"line": route.edges[0].line, "stations": [names[0]]}
    segments = []
    for idx, edge in enumerate(route.edges):
        if edge.line != current["line"]:
            segments.append(current)
            current = {"line": edge.line, "stations": [names[idx]]}
        current["stations"].append(names[idx + 1])
    segments.append(current)
    return segments


def build_summary(route):
    """Extract the key figures of a route into a dictionary."""
    return {
        "total_distance_m": route.distance_m,
        "total_distance_km": route.distance_km,
        "total_fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": route.estimated_minutes,
        "lines": list(route.lines),
    }


def format_text(route):
    """Render a human-readable console report for a route."""
    segments = build_segments(route)
    out = []
    out.append("=== Beijing Subway Fare Query ===")
    out.append(f"From: {route.start}")
    out.append(f"To: {route.end}")
    out.append(f"Mode: {MODE_LABELS.get(route.mode, route.mode)}")
    if route.max_transfers is not None:
        out.append(f"Max transfers: {route.max_transfers}")
    if route.preferred_lines:
        out.append(f"Line preference: {', '.join(route.preferred_lines)}")
    out.append("")
    out.append("-- Line segments --")
    for idx, segment in enumerate(segments):
        stations = segment["stations"]
        out.append(f"[{segment['line']}] {' -> '.join(stations)} ({len(stations)} stations)")
        if idx < len(segments) - 1:
            transfer_station = stations[-1]
            next_line = segments[idx + 1]["line"]
            out.append(f"  Transfer at {transfer_station}: {segment['line']} -> {next_line}")
    out.append("")
    out.append(f"-- Complete station sequence ({len(route.station_names)} stations) --")
    for idx, name in enumerate(route.station_names, start=1):
        marker = ""
        if idx == 1:
            marker = " (start)"
        elif idx == len(route.station_names):
            marker = " (end)"
        elif any(point["station"] == name for point in route.transfer_points):
            marker = " (transfer)"
        out.append(f"{idx:>3}. {name}{marker}")
    out.append("")
    out.append("-- Summary --")
    out.append(f"Total distance: {format_distance(route.distance_m)}")
    out.append(f"Transfers: {route.transfer_count}")
    if route.transfer_points:
        details = ", ".join(
            f"{p['station']} ({p['from_line']} -> {p['to_line']})" for p in route.transfer_points
        )
        out.append(f"Transfer stations: {details}")
    out.append(f"Lines involved: {', '.join(route.lines)}")
    out.append(f"Estimated travel time: {route.estimated_minutes} minutes")
    out.append(f"Fare: {route.fare} yuan")
    return "\n".join(out)


def route_to_dict(route):
    """Convert a route into a JSON-serializable dictionary."""
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.preferred_lines,
        },
        "path": list(route.station_names),
        "distance": route.distance_m,
        "distance_m": route.distance_m,
        "distance_km": route.distance_km,
        "fare": route.fare,
        "estimated_time": route.estimated_minutes,
        "estimated_time_min": route.estimated_minutes,
        "transfer_count": route.transfer_count,
        "transfers": [dict(point) for point in route.transfer_points],
        "lines": list(route.lines),
        "segments": build_segments(route),
        "summary": build_summary(route),
    }


def format_json(route):
    """Render a route as an indented JSON string."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=2)


def export_report(content, file_path):
    """Write report content to a file (UTF-8), creating parent directories.

    Returns:
        str: Absolute path of the written file.

    Raises:
        OSError: If the file cannot be written.
    """
    abs_path = os.path.abspath(file_path)
    directory = os.path.dirname(abs_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    text = content if content.endswith("\n") else content + "\n"
    with open(abs_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return abs_path
