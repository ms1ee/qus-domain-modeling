"""
Path visualization and export.

Builds a structured summary of a computed route and renders it either as
console-formatted text or as JSON.
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(distance_m):
    """Format a distance: meters for short distances (<1 km), kilometers otherwise."""
    if distance_m < 1000:
        return f"{distance_m:.0f} m"
    return f"{distance_m / 1000:.2f} km"


def _build_segments(station_names, edges):
    """Group consecutive edges of the same line into travel segments."""
    segments = []
    for index, edge in enumerate(edges):
        start = station_names[index]
        end = station_names[index + 1]
        if segments and segments[-1]["line"] == edge.line:
            segments[-1]["end"] = end
            segments[-1]["distance_m"] += edge.distance
        else:
            segments.append({
                "line": edge.line,
                "start": start,
                "end": end,
                "distance_m": edge.distance,
            })
    return segments


def _build_transfers(station_names, edges):
    """Identify transfer stations and the lines joined at each of them."""
    transfers = []
    for index in range(1, len(edges)):
        previous_edge = edges[index - 1]
        current_edge = edges[index]
        if previous_edge.line != current_edge.line:
            transfers.append({
                "station": station_names[index],
                "from_line": previous_edge.line,
                "to_line": current_edge.line,
            })
    return transfers


def _involved_lines(edges):
    """Return the unique line names used by the route, in travel order."""
    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)
    return lines


def build_path_summary(start, end, mode, station_names, edges, transfer_count):
    """
    Build a structured summary of a route.

    Args:
        start: Official name of the starting station.
        end: Official name of the ending station.
        mode: Query mode used.
        station_names: Ordered list of station names along the route.
        edges: Ordered list of Edge objects along the route.
        transfer_count: Number of transfers on the route.

    Returns:
        dict: Summary with query, path, distance, fare, time, transfers and lines.
    """
    distance_m = sum(edge.distance for edge in edges)
    fare = Sum_money(distance_m)
    estimated_time = calculate_estimated_time(distance_m, transfer_count)
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": list(station_names),
        "station_count": len(station_names),
        "distance": {
            "meters": distance_m,
            "kilometers": round(distance_m / 1000.0, 2),
        },
        "fare": fare,
        "estimated_time_minutes": estimated_time,
        "transfer_count": transfer_count,
        "lines": _involved_lines(edges),
        "segments": _build_segments(station_names, edges),
        "transfers": _build_transfers(station_names, edges),
    }


def format_text_report(summary):
    """Render a route summary as console-formatted text."""
    query = summary["query"]
    lines = []
    lines.append("=== Beijing Subway Route ===")
    lines.append(f"From: {query['start']}  To: {query['end']}  (mode: {query['mode']})")
    lines.append(f"Total distance: {format_distance(summary['distance']['meters'])}"
                 f" ({summary['distance']['meters']} m)")
    lines.append(f"Fare: {summary['fare']} yuan")
    lines.append(f"Estimated time: {summary['estimated_time_minutes']:.2f} min")
    lines.append(f"Transfers: {summary['transfer_count']}")
    lines.append(f"Lines involved: {', '.join(summary['lines']) if summary['lines'] else 'None'}")

    lines.append("")
    lines.append("Route details:")
    segments = summary["segments"]
    if not segments:
        lines.append("  (start and end are the same station)")
    for index, segment in enumerate(segments):
        if index > 0:
            lines.append(f"  Transfer at {segment['start']}: {segments[index - 1]['line']}"
                         f" -> {segment['line']}")
        lines.append(f"  [{segment['line']}] {segment['start']} -> {segment['end']}"
                     f" ({format_distance(segment['distance_m'])})")

    lines.append("")
    lines.append(f"Station sequence ({summary['station_count']} stations):")
    for number, name in enumerate(summary["path"], start=1):
        lines.append(f"  {number}. {name}")

    return "\n".join(lines)


def format_json_report(summary, indent=2):
    """Render a route summary as a JSON string."""
    return json.dumps(summary, ensure_ascii=False, indent=indent)
