"""Path visualization and report export (console text and JSON)."""

import json
import os

from route_planner import summarize


def format_distance(meters):
    """Format a distance: meters only for short trips, meters plus kilometers for long trips."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters:.0f} m ({meters / 1000:.2f} km)"


def format_text(route):
    """Render a Route as a human-readable console report."""
    rule = "=" * 60
    lines = [
        rule,
        "Beijing Subway Fare Report",
        rule,
        f"Start: {route.start}",
        f"End: {route.end}",
        f"Mode: {route.mode}",
        f"Max transfers: {route.max_transfers if route.max_transfers is not None else 'unlimited'}",
        f"Line preference: {', '.join(route.preferred_lines) if route.preferred_lines else 'none'}",
        "",
        "Station sequence (end to start):",
    ]
    for index, name in enumerate(reversed(route.station_path), start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("")
    lines.append("Route by line:")
    for segment in route.segments:
        stops = len(segment.stations) - 1
        lines.append(
            f"  [{segment.line}] {segment.stations[0]} -> {segment.stations[-1]} "
            f"({stops} stops, {format_distance(segment.distance)})"
        )

    lines.append("")
    lines.append("Transfers:")
    if not route.transfers:
        lines.append("  None")
    for transfer in route.transfers:
        lines.append(
            f"  {transfer.station}: {transfer.from_line} -> {transfer.to_line} "
            f"(lines involved: {', '.join(transfer.involved_lines)})"
        )

    summary = summarize(route)
    lines.append("")
    lines.append(f"Total distance: {format_distance(summary.total_distance_m)}")
    lines.append(f"Transfers required: {summary.transfer_count}")
    lines.append(f"Estimated time: {summary.estimated_time_minutes:.1f} minutes")
    lines.append(f"Lines involved: {', '.join(route.involved_lines)}")
    lines.append(f"Fare: {summary.total_fare} yuan")
    lines.append(rule)
    return "\n".join(lines)


def route_to_dict(route):
    """Convert a Route to a JSON-serializable dict."""
    summary = summarize(route)
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.preferred_lines,
        },
        "path": route.station_path,
        "distance": {
            "meters": round(route.total_distance, 2),
            "kilometers": round(route.total_distance / 1000.0, 3),
        },
        "fare": route.fare,
        "estimated_time_minutes": round(route.estimated_time, 2),
        "transfer_count": route.transfer_count,
        "involved_lines": route.involved_lines,
        "transfers": [
            {
                "station": t.station,
                "from_line": t.from_line,
                "to_line": t.to_line,
                "involved_lines": t.involved_lines,
            }
            for t in route.transfers
        ],
        "segments": [
            {
                "line": s.line,
                "start": s.stations[0],
                "end": s.stations[-1],
                "stations": s.stations,
                "distance_m": round(s.distance, 2),
            }
            for s in route.segments
        ],
        "summary": {
            "total_distance_m": round(summary.total_distance_m, 2),
            "total_fare": summary.total_fare,
            "transfer_count": summary.transfer_count,
            "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        },
    }


def format_json(route):
    """Render a Route as an indented JSON string."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=2)


def write_report(content, output_file):
    """Write report text to a file (UTF-8), creating parent directories as needed.

    Returns:
        str: absolute path of the written file.
    """
    absolute = os.path.abspath(output_file)
    directory = os.path.dirname(absolute)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(absolute, "w", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")
    return absolute
