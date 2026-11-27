"""Path summary generation, report formatting and export."""

import json
import os

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Format a distance in meters, adding kilometers for long distances."""
    value = int(round(meters))
    if value >= 1000:
        return f"{value} m ({value / 1000:.2f} km)"
    return f"{value} m"


def build_summary(route):
    """Extract key information from a RouteResult.

    Returns:
        dict with keys: distance_meters, fare, transfer_count,
        estimated_time_minutes, lines.
    """
    return {
        "distance_meters": route.distance,
        "fare": Sum_money(route.distance),
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": round(
            calculate_estimated_time(route.distance, route.transfer_count), 2
        ),
        "lines": list(route.lines),
    }


def format_text_report(route, summary):
    """Render a human-readable console report."""
    separator = "=" * 60
    out = [
        separator,
        "Beijing Subway Fare Query",
        separator,
        f"From: {route.source}",
        f"To: {route.target}",
        f"Query mode: {route.mode}",
        "",
        "Station sequence (end -> start):",
        "  " + " -> ".join(reversed(route.stations)),
        "",
        "Route segments:",
    ]
    for index, segment in enumerate(route.segments, start=1):
        out.append(f"  {index}. [{segment['line']}] " + " -> ".join(segment["stations"]))

    out.append("")
    out.append("Transfers:")
    if not route.transfers:
        out.append("  None (direct ride)")
    else:
        for transfer in route.transfers:
            out.append(
                f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )

    out.append("")
    out.append(f"Total distance: {format_distance(summary['distance_meters'])}")
    out.append(f"Transfers: {summary['transfer_count']}")
    out.append(f"Estimated time: {summary['estimated_time_minutes']:.1f} minutes")
    out.append(f"Lines involved: {', '.join(summary['lines']) if summary['lines'] else 'None'}")
    out.append(f"Fare: {summary['fare']} yuan")
    out.append(separator)
    return "\n".join(out)


def format_json_report(route, summary, query_info=None, indent=2):
    """Render a structured JSON report for programmatic use."""
    payload = {
        "query": {
            "start": route.source,
            "end": route.target,
            "mode": route.mode,
            **(query_info or {}),
        },
        "path": route.stations,
        "distance_meters": summary["distance_meters"],
        "fare": summary["fare"],
        "estimated_time_minutes": summary["estimated_time_minutes"],
        "transfer_count": summary["transfer_count"],
        "transfers": route.transfers,
        "lines": summary["lines"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def export_report(content, path):
    """Append a rendered report to a file, creating parent directories if needed.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content + "\n")
