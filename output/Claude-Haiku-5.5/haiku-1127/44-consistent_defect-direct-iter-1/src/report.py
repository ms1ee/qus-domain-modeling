"""Path visualization and report export (console text and JSON)."""

import json

from fare_calculator import calculate_estimated_time


def format_distance(meters):
    """Format a distance: meters for short trips, kilometers for long ones."""
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters} m)"


def build_segments(route):
    """Group the travel path into line segments (travel order).

    Returns:
        list[dict]: Each dict has keys ``line`` (str), ``stations`` (list of
        station names in travel order) and ``distance`` (meters).
    """
    chron_stations = list(reversed(route.stations))
    chron_edges = list(reversed(route.edges))
    if not chron_edges:
        return []

    segments = []
    current = {
        "line": chron_edges[0].line,
        "stations": [chron_stations[0], chron_stations[1]],
        "distance": chron_edges[0].distance,
    }
    for i in range(1, len(chron_edges)):
        edge = chron_edges[i]
        if edge.line == current["line"]:
            current["stations"].append(chron_stations[i + 1])
            current["distance"] += edge.distance
        else:
            segments.append(current)
            current = {
                "line": edge.line,
                "stations": [chron_stations[i], chron_stations[i + 1]],
                "distance": edge.distance,
            }
    segments.append(current)
    return segments


def build_summary(route, fare):
    """Extract key figures of a route.

    Returns:
        dict: ``total_distance_m``, ``fare_yuan``, ``transfer_count`` and
        ``estimated_time_min``.
    """
    return {
        "total_distance_m": route.distance,
        "fare_yuan": fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": round(
            calculate_estimated_time(route.distance, route.transfer_count), 1),
    }


def format_text(query, route, fare):
    """Render a console-formatted text report."""
    summary = build_summary(route, fare)
    segments = build_segments(route)
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Report")
    out.append("=" * 60)
    out.append(f"Starting station : {query['start']}")
    out.append(f"Ending station   : {query['end']}")
    out.append(f"Query mode       : {query['mode']}")
    out.append("")
    out.append(f"Station sequence (end -> start, {len(route.stations)} stations):")
    for index, name in enumerate(route.stations, 1):
        out.append(f"  {index:>3}. {name}")
    out.append("")
    out.append("Line segments (travel order):")
    if segments:
        for segment in segments:
            out.append(f"  [{segment['line']}] {' -> '.join(segment['stations'])} "
                       f"({format_distance(segment['distance'])})")
    else:
        out.append("  (no travel required)")
    out.append("")
    out.append(f"Transfers: {route.transfer_count}")
    if route.transfers:
        for transfer in route.transfers:
            out.append(f"  - {transfer['station']}: "
                       f"{transfer['from_line']} -> {transfer['to_line']}")
    else:
        out.append("  No transfers required")
    out.append(f"Lines involved: {', '.join(route.lines) if route.lines else 'none'}")
    out.append("")
    out.append(f"Total distance : {format_distance(summary['total_distance_m'])}")
    out.append(f"Estimated time : {summary['estimated_time_min']:.1f} minutes")
    out.append(f"Fare: {fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(query, route, fare, indent=2):
    """Render a structured JSON report for programmatic integration."""
    summary = build_summary(route, fare)
    payload = {
        "query": query,
        "path": route.stations,
        "distance_m": summary["total_distance_m"],
        "fare": fare,
        "estimated_time_min": summary["estimated_time_min"],
        "transfer_count": summary["transfer_count"],
        "lines": route.lines,
        "transfers": route.transfers,
        "segments": [
            {"line": seg["line"], "stations": seg["stations"],
             "distance_m": seg["distance"]}
            for seg in build_segments(route)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)
