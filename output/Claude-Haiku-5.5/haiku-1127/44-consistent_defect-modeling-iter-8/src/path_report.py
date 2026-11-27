"""Path visualization, summary extraction and report export.

Renders a Route as console text or as structured JSON. Station sequences in
the text report are listed from end to start, as required by the PRD.
"""

import json
from dataclasses import dataclass

from fare_calculator import calculate_estimated_time


@dataclass
class PathSummary:
    """Key figures of a computed path.

    Attributes:
        total_distance_m: Total travel distance in meters.
        total_fare: Fare in yuan.
        transfer_count: Number of transfers.
        estimated_time_min: Estimated travel time in minutes.
    """

    total_distance_m: int
    total_fare: int
    transfer_count: int
    estimated_time_min: float


def build_summary(route, fare) -> PathSummary:
    """Extract the path summary from a route and its fare."""
    return PathSummary(
        total_distance_m=int(route.total_distance),
        total_fare=int(fare),
        transfer_count=int(route.transfer_count),
        estimated_time_min=round(
            calculate_estimated_time(route.total_distance, route.transfer_count), 1
        ),
    )


def format_distance(meters) -> str:
    """Format a distance: meters for short trips, kilometers (plus meters) for long trips."""
    if meters < 1000:
        return f"{int(meters)} m"
    return f"{meters / 1000:.2f} km ({int(meters)} m)"


def build_segments(route, name_of) -> list:
    """Group consecutive edges of the same line into segments.

    Returns a list of dicts with keys: line, from, to, stops, distance_m.
    """
    segments = []
    edges = route.edges
    stations = route.stations
    index = 0
    while index < len(edges):
        end = index
        while end + 1 < len(edges) and edges[end + 1].line == edges[index].line:
            end += 1
        distance = sum(edges[k].distance for k in range(index, end + 1))
        segments.append(
            {
                "line": edges[index].line,
                "from": name_of(stations[index]),
                "to": name_of(stations[end + 1]),
                "stops": end - index + 1,
                "distance_m": distance,
            }
        )
        index = end + 1
    return segments


def build_transfers(route, name_of) -> list:
    """Return the transfer stations of a route with the lines before and after."""
    transfers = []
    edges = route.edges
    for index in range(len(edges) - 1):
        if edges[index].line != edges[index + 1].line:
            transfers.append(
                {
                    "station": name_of(route.stations[index + 1]),
                    "from_line": edges[index].line,
                    "to_line": edges[index + 1].line,
                }
            )
    return transfers


def _optional(value) -> str:
    return "not limited" if value is None else str(value)


def render_text(query_info, route, summary, name_of) -> str:
    """Render a console-formatted report including line segments and transfers."""
    rule = "=" * 60
    lines = [
        rule,
        "Beijing Subway Fare Query Result",
        rule,
        f"Starting station : {query_info['start']}",
        f"Ending station   : {query_info['end']}",
        f"Query mode       : {query_info['mode']}",
        f"Max transfers    : {_optional(query_info.get('max_transfers'))}",
        f"Line preference  : {_optional(query_info.get('line_preference'))}",
        "",
        "Station sequence (end to start):",
        "  " + " -> ".join(reversed([name_of(n) for n in route.stations])),
        "",
        "Line segments:",
    ]
    for number, segment in enumerate(build_segments(route, name_of), 1):
        lines.append(
            f"  {number}. [{segment['line']}] {segment['from']} -> {segment['to']} "
            f"({segment['stops']} stops, {format_distance(segment['distance_m'])})"
        )
    lines.append("Transfer stations:")
    transfers = build_transfers(route, name_of)
    if not transfers:
        lines.append("  None")
    for transfer in transfers:
        lines.append(
            f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
        )
    lines.extend(
        [
            "",
            f"Lines involved    : {', '.join(route.involved_lines)}",
            f"Total distance    : {format_distance(summary.total_distance_m)}",
            f"Transfer count    : {summary.transfer_count}",
            f"Estimated time    : {summary.estimated_time_min:.1f} minutes",
            f"Fare: {summary.total_fare} yuan",
            rule,
        ]
    )
    return "\n".join(lines)


def render_json(query_info, route, summary, name_of) -> str:
    """Render the structured JSON report for programmatic integration."""
    payload = {
        "query": {
            "start": query_info["start"],
            "end": query_info["end"],
            "mode": query_info["mode"],
            "max_transfers": query_info.get("max_transfers"),
            "line_preference": query_info.get("line_preference"),
        },
        "path": [name_of(n) for n in route.stations],
        "distance_meters": summary.total_distance_m,
        "distance_kilometers": round(summary.total_distance_m / 1000.0, 2),
        "fare_yuan": summary.total_fare,
        "estimated_time_minutes": summary.estimated_time_min,
        "transfer_count": summary.transfer_count,
        "transfers": build_transfers(route, name_of),
        "lines": route.involved_lines,
        "segments": build_segments(route, name_of),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
