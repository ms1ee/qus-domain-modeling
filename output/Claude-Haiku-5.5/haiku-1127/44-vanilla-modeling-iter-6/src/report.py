"""Path visualization and report export (console text, JSON, file output)."""

import json
import os
from datetime import datetime


def format_distance(meters):
    """Format a distance: meters for short trips, kilometers for long trips."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_segments(route):
    """Group consecutive edges on the same line into line segments."""
    segments = []
    names = route.station_names
    for i, edge in enumerate(route.edges):
        if i == 0 or edge.line != route.edges[i - 1].line:
            segments.append({"line": edge.line, "start": names[i],
                             "end": names[i + 1], "stops": 0})
        segments[-1]["end"] = names[i + 1]
        segments[-1]["stops"] += 1
    return segments


def build_summary(route):
    """Extract the key summary figures of a route as a dictionary."""
    return {
        "total_distance_km": round(route.total_distance_meters / 1000.0, 3),
        "total_distance_meters": round(route.total_distance_meters, 1),
        "fare_yuan": route.fare_yuan,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": round(route.estimated_time_minutes, 2),
    }


def _timestamp(timestamp):
    return timestamp or datetime.now().isoformat(timespec="seconds")


def format_text(route, timestamp=None):
    """Render a human-readable console report for a route."""
    ts = _timestamp(timestamp)
    bar = "=" * 60
    out = [
        bar,
        "Beijing Subway Fare Query Result",
        bar,
        f"Query time : {ts}",
        f"Start      : {route.start_station}",
        f"End        : {route.end_station}",
        f"Mode       : {route.mode}",
        "",
        f"Station sequence ({len(route.station_names)} stations):",
    ]
    for index, name in enumerate(route.station_names, 1):
        out.append(f"  {index:>3}. {name}")

    out.append("")
    out.append("Line segments:")
    segments = build_segments(route)
    if not segments:
        out.append("  (none)")
    for seg in segments:
        out.append(f"  [{seg['line']}] {seg['start']} -> {seg['end']} "
                   f"({seg['stops']} stops)")

    out.append("")
    out.append("Transfers:")
    if route.transfers:
        for transfer in route.transfers:
            out.append(f"  At {transfer.station_name}: "
                       f"{transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("  No transfers")
    out.append(f"Lines involved: {', '.join(route.lines) if route.lines else 'none'}")

    out.append("")
    out.append(f"Total distance : {format_distance(route.total_distance_meters)}")
    out.append(f"Transfers      : {route.transfer_count}")
    out.append(f"Estimated time : {route.estimated_time_minutes:.1f} minutes")
    out.append(f"Fare: {route.fare_yuan} yuan")
    out.append(bar)
    return "\n".join(out)


def format_json(route, timestamp=None, indent=2):
    """Render a structured JSON report for programmatic integration."""
    data = {
        "query": {
            "start_station": route.start_station,
            "end_station": route.end_station,
            "mode": route.mode,
            "timestamp": _timestamp(timestamp),
        },
        "path": list(route.station_names),
        "distance": {
            "meters": round(route.total_distance_meters, 1),
            "kilometers": round(route.total_distance_meters / 1000.0, 3),
        },
        "fare_yuan": route.fare_yuan,
        "estimated_time_minutes": round(route.estimated_time_minutes, 2),
        "transfer_count": route.transfer_count,
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line,
             "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines": list(route.lines),
        "segments": build_segments(route),
        "summary": build_summary(route),
    }
    return json.dumps(data, ensure_ascii=False, indent=indent)


def write_report(content, path, append=True):
    """Write report text to a file (UTF-8), creating parent directories.

    Raises:
        OSError: if the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as handle:
        handle.write(content)
