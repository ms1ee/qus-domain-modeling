"""Path visualization and report export (console text and JSON)."""

import json
import os

from route_service import RouteResult  # noqa: F401  (documents the expected type)


def format_distance(meters):
    """Format a distance: meters for short distances, kilometers for long ones."""
    meters = float(meters)
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km ({meters:.0f} m)"


def build_summary(result):
    """Extract the key figures of a route result."""
    return {
        "total_distance_km": round(result.total_distance_m / 1000.0, 2),
        "total_distance_m": round(result.total_distance_m, 1),
        "fare": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": round(result.estimated_time_min, 1),
    }


def format_text(result):
    """Render a route result as console-friendly text."""
    separator = "=" * 60
    divider = "-" * 60
    max_text = "unlimited" if result.max_transfers is None else str(result.max_transfers)
    preference_text = ", ".join(result.line_preference) if result.line_preference else "none"

    out = [
        separator,
        f"Route: {result.start} -> {result.end}",
        f"Mode: {result.mode} | Max transfers: {max_text} | Line preference: {preference_text}",
        divider,
        f"Station sequence ({len(result.stations)} stations):",
        "  " + " -> ".join(result.stations),
        "Line segments:",
    ]
    for segment in result.segments:
        out.append(f"  [{segment.line}] {' -> '.join(segment.stations)} ({format_distance(segment.distance_m)})")

    out.append("Transfers:")
    if result.transfers:
        for transfer in result.transfers:
            out.append(f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("  none")

    out.append(f"Lines involved: {', '.join(result.involved_lines)}")
    out.append(f"Total distance: {format_distance(result.total_distance_m)}")
    out.append(f"Number of transfers: {result.transfer_count}")
    out.append(f"Estimated travel time: {result.estimated_time_min:.1f} min")
    out.append(f"Fare: {result.fare} yuan")
    out.append(separator)
    return "\n".join(out)


def to_json_dict(result):
    """Convert a route result into a JSON-serialisable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": list(result.line_preference),
        },
        "path": list(result.stations),
        "distance": {
            "meters": round(result.total_distance_m, 1),
            "kilometers": round(result.total_distance_m / 1000.0, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": round(result.estimated_time_min, 1),
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "involved_lines": list(result.involved_lines),
        "segments": [
            {"line": s.line, "stations": list(s.stations), "distance_m": round(s.distance_m, 1)}
            for s in result.segments
        ],
        "summary": build_summary(result),
    }


def format_json(result):
    """Render a route result as an indented JSON string."""
    return json.dumps(to_json_dict(result), ensure_ascii=False, indent=2)


def export_report(result, fmt="text"):
    """Render a route result in the requested format ('text' or 'json')."""
    if fmt == "json":
        return format_json(result)
    return format_text(result)


def write_report(path, content, append=False):
    """Write report content to a file, creating parent directories if needed.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")
