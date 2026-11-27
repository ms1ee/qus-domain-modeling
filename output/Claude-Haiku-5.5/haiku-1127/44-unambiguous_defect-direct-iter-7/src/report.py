"""Rendering of route results as console text or structured JSON."""

from __future__ import annotations

import json

from route_service import RouteResult

SEPARATOR = "=" * 60
RULE = "-" * 60


def format_text_report(result: RouteResult) -> str:
    """Render a route result as a human-readable console report."""
    max_text = "unlimited" if result.max_transfers is None else str(result.max_transfers)
    preference = ", ".join(result.preferred_lines) if result.preferred_lines else "none"
    lines = [
        SEPARATOR,
        f"Route: {result.start} -> {result.end}",
        f"Mode: {result.mode} | Max transfers: {max_text} | Line preference: {preference}",
        RULE,
        f"Station sequence ({len(result.stations)} stations):",
    ]
    for index, name in enumerate(result.stations, start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("")
    lines.append("Line segments:")
    for segment in result.segments:
        lines.append(
            f"  [{segment.line}] {segment.start} -> {segment.end} "
            f"({segment.stop_count} stops, {segment.distance_m} m)"
        )

    lines.append("")
    lines.append("Transfer details:")
    if result.transfer_count == 0:
        lines.append("  No transfer required")
    else:
        for index, station in enumerate(result.transfer_stations):
            before = result.segments[index].line
            after = result.segments[index + 1].line
            lines.append(f"  Transfer at {station}: {before} -> {after}")
    lines.append(f"Lines involved: {', '.join(result.lines)}")

    lines.append(RULE)
    lines.append(
        f"Total distance: {result.distance_m} m ({result.distance_km:.2f} km)"
    )
    lines.append(f"Transfers: {result.transfer_count}")
    lines.append(f"Estimated time: {result.estimated_time_min:.1f} min")
    lines.append(f"Fare: {result.fare} yuan")
    lines.append(SEPARATOR)
    return "\n".join(lines)


def route_to_dict(result: RouteResult) -> dict:
    """Convert a route result into a JSON-serialisable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": result.stations,
        "distance_m": result.distance_m,
        "distance_km": round(result.distance_km, 2),
        "fare": result.fare,
        "estimated_time_min": result.estimated_time_min,
        "transfer_count": result.transfer_count,
        "transfer_stations": result.transfer_stations,
        "lines": result.lines,
        "segments": [
            {
                "line": segment.line,
                "start": segment.start,
                "end": segment.end,
                "stations": segment.stations,
                "distance_m": segment.distance_m,
            }
            for segment in result.segments
        ],
    }


def render_json(results) -> str:
    """Render a list of route results as a JSON array string."""
    return json.dumps([route_to_dict(result) for result in results],
                      ensure_ascii=False, indent=2)


def render_results(results, output_format: str) -> str:
    """Render results in the requested format ('text' or 'json')."""
    if output_format == "json":
        return render_json(results)
    return "\n\n".join(format_text_report(result) for result in results) + "\n"
