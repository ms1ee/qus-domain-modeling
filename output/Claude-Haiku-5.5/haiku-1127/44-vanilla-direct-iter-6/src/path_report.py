"""Path visualization and report export.

A route is turned into a report dictionary which is rendered either as
console text or as JSON, and can optionally be appended to a file.
"""

import json
import os

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Format a distance: meters for short trips, kilometers for long trips."""
    if meters < 1000:
        return f"{round(meters)} m"
    return f"{meters / 1000:.2f} km ({round(meters)} m)"


def build_summary(route):
    """Extract the key figures of a route.

    Returns:
        dict with total distance (m and km), fare, transfer count and
        estimated time in minutes.
    """
    fare = Sum_money(route.distance)
    estimated = calculate_estimated_time(route.distance, route.transfer_count)
    return {
        "total_distance_m": route.distance,
        "total_distance_km": round(route.distance / 1000.0, 3),
        "fare": fare,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": round(estimated, 1),
    }


def build_report_data(route, query_info):
    """Build the structured report used by both text and JSON renderers.

    Args:
        route: ``pathfinding.Route`` instance.
        query_info: dict with ``mode``, ``max_transfers`` and ``line_preference``.

    Returns:
        dict: Report content.
    """
    summary = build_summary(route)
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": query_info.get("mode", route.mode),
            "max_transfers": query_info.get("max_transfers"),
            "line_preference": query_info.get("line_preference"),
        },
        "path": list(route.stations),
        "distance": {
            "meters": route.distance,
            "kilometers": summary["total_distance_km"],
            "display": format_distance(route.distance),
        },
        "fare": summary["fare"],
        "estimated_time_minutes": summary["estimated_time_minutes"],
        "transfer_count": route.transfer_count,
        "lines": list(route.lines),
        "segments": [{"line": seg["line"], "stations": list(seg["stations"])}
                     for seg in route.segments],
        "transfers": [dict(item) for item in route.transfer_stations],
    }


def render_text(report):
    """Render the report as console-formatted text."""
    query = report["query"]
    out = []
    out.append("=" * 56)
    out.append("Beijing Subway Fare Query Result")
    out.append("=" * 56)
    out.append(f"Starting station : {query['start']}")
    out.append(f"Ending station   : {query['end']}")
    out.append(f"Query mode       : {query['mode']}")
    if query.get("max_transfers") is not None:
        out.append(f"Max transfers    : {query['max_transfers']}")
    if query.get("line_preference"):
        out.append(f"Line preference  : {query['line_preference']}")
    out.append("")
    out.append(f"Route ({len(report['path'])} stations):")
    out.append("  " + " -> ".join(report["path"]))
    out.append("")
    out.append("Line segments:")
    for number, segment in enumerate(report["segments"], start=1):
        stations = segment["stations"]
        out.append(f"  {number}. [{segment['line']}] {stations[0]} -> {stations[-1]} "
                   f"({len(stations)} stations)")
    out.append("")
    if report["transfers"]:
        out.append("Transfer stations:")
        for item in report["transfers"]:
            out.append(f"  - {item['station']}: {item['from_line']} -> {item['to_line']}")
    else:
        out.append("Transfer stations: none")
    out.append(f"Lines involved  : {', '.join(report['lines'])}")
    out.append(f"Transfers       : {report['transfer_count']}")
    out.append(f"Total distance  : {report['distance']['display']}")
    out.append(f"Fare: {report['fare']} yuan")
    out.append(f"Estimated time  : {report['estimated_time_minutes']:.1f} minutes")
    return "\n".join(out)


def render_json(report):
    """Render the report as a JSON document."""
    return json.dumps(report, ensure_ascii=False, indent=2)


def export_report(content, output_file):
    """Append rendered report content to a file.

    Args:
        content: The rendered report string.
        output_file: Destination file path. Parent directories are created.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n\n")
