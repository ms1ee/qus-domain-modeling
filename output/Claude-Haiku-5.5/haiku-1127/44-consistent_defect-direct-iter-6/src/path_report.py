"""Path visualization, summary generation, and report export."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Format a distance: meters for short trips, kilometers for long trips."""
    meters = int(round(meters))
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters} m)"


def count_transfers(edges):
    """Count line changes between consecutive edges."""
    return sum(1 for index in range(1, len(edges))
               if edges[index].line != edges[index - 1].line)


def find_transfers(station_names, edges):
    """Return transfer details: station and the lines before and after it."""
    transfers = []
    for index in range(1, len(edges)):
        previous_line = edges[index - 1].line
        current_line = edges[index].line
        if previous_line != current_line:
            transfers.append({
                "station": station_names[index],
                "from_line": previous_line,
                "to_line": current_line,
            })
    return transfers


def involved_lines(edges):
    """Return the unique line names used on the path, in order of first use."""
    lines = []
    for edge in edges:
        if edge.line not in lines:
            lines.append(edge.line)
    return lines


def build_segments(station_names, edges):
    """Group consecutive edges on the same line into travel segments."""
    segments = []
    if not edges:
        return segments
    start = 0
    for index in range(1, len(edges) + 1):
        if index == len(edges) or edges[index].line != edges[start].line:
            segment_edges = edges[start:index]
            segments.append({
                "line": edges[start].line,
                "start": station_names[start],
                "end": station_names[index],
                "stations": index - start + 1,
                "distance_m": sum(edge.distance for edge in segment_edges),
            })
            start = index
    return segments


def build_summary(edges):
    """Extract key summary figures: distance, fare, transfers, and time."""
    distance = sum(edge.distance for edge in edges)
    transfers = count_transfers(edges)
    return {
        "distance_m": distance,
        "fare": Sum_money(distance),
        "transfer_count": transfers,
        "estimated_time_min": round(calculate_estimated_time(distance, transfers), 1),
    }


def build_report(query, station_names, edges):
    """Build a structured report dictionary for a computed path.

    Args:
        query: Dictionary describing the query (start, end, mode, ...).
        station_names: Station names from start to end.
        edges: Edges traversed from start to end.
    """
    summary = build_summary(edges)
    return {
        "query": dict(query),
        "path": list(station_names),
        "segments": build_segments(station_names, edges),
        "distance_m": summary["distance_m"],
        "distance_km": round(summary["distance_m"] / 1000.0, 3),
        "fare": summary["fare"],
        "estimated_time_min": summary["estimated_time_min"],
        "transfer_count": summary["transfer_count"],
        "transfers": find_transfers(station_names, edges),
        "lines": involved_lines(edges),
    }


def render_text(report):
    """Render a report as console-formatted text."""
    query = report["query"]
    lines = [
        "=" * 60,
        "Beijing Subway Route Report",
        "=" * 60,
        f"From: {query['start']}",
        f"To:   {query['end']}",
        f"Mode: {query['mode']}",
    ]
    if query.get("max_transfers") is not None:
        lines.append(f"Max transfers: {query['max_transfers']}")
    if query.get("line_preference"):
        lines.append(f"Line preference: {', '.join(query['line_preference'])}")

    lines.append("")
    lines.append("Station sequence (end to start):")
    for index, name in enumerate(reversed(report["path"]), start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("")
    lines.append("Route segments (start to end):")
    if not report["segments"]:
        lines.append("  (start and end are the same station)")
    for segment in report["segments"]:
        lines.append(
            f"  [{segment['line']}] {segment['start']} -> {segment['end']} "
            f"({segment['stations']} stations, {format_distance(segment['distance_m'])})"
        )

    lines.append("")
    lines.append("Transfers:")
    if not report["transfers"]:
        lines.append("  None (no line change)")
    for transfer in report["transfers"]:
        lines.append(f"  - {transfer['station']}: "
                     f"{transfer['from_line']} -> {transfer['to_line']}")

    lines.append(f"Lines involved: {', '.join(report['lines'])}")
    lines.append("")
    lines.append(f"Total distance: {format_distance(report['distance_m'])}")
    lines.append(f"Transfers: {report['transfer_count']}")
    lines.append(f"Estimated time: {report['estimated_time_min']:.1f} minutes")
    lines.append(f"Fare: {report['fare']} yuan")
    return "\n".join(lines)


def render_json(report):
    """Render a report as a JSON document string."""
    return json.dumps(report, ensure_ascii=False, indent=2)
