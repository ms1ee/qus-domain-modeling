"""Path visualization, summary generation and report export.

Two output formats are provided:

* ``text``: console-friendly report with station sequence, line segments,
  transfer details, distance, time and fare.
* ``json``: structured report for programmatic integration.
"""

import json

from route_query import RouteResult


def format_distance(meters):
    """Format a distance, showing meters for short and kilometers for long distances."""
    if meters < 1000:
        return f"{meters} m ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters} m)"


def build_summary(result):
    """Extract the key figures of a query result.

    Returns:
        dict: Total distance (m and km), fare, transfer count and estimated time (min).
    """
    return {
        "total_distance_m": result.distance_m,
        "total_distance_km": round(result.distance_m / 1000.0, 3),
        "fare": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": round(result.estimated_time_min, 1),
    }


def format_text(result):
    """Render a query result as console-formatted text."""
    summary = build_summary(result)
    preference = ", ".join(result.line_preference) if result.line_preference else "none"
    max_transfers = result.max_transfers if result.max_transfers is not None else "unlimited"

    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 60)
    out.append(f"From: {result.start}")
    out.append(f"To: {result.end}")
    out.append(f"Mode: {result.mode}")
    out.append(f"Max transfers: {max_transfers}")
    out.append(f"Line preference: {preference}")
    out.append("")
    out.append(f"Route ({len(result.stations)} stations):")
    out.append("  " + " -> ".join(result.stations))
    out.append("")
    out.append("Line segments:")
    for index, segment in enumerate(result.segments, 1):
        out.append(
            f"  {index}. [{segment['line']}] {segment['from']} -> {segment['to']} "
            f"({segment['station_count']} stations, {format_distance(segment['distance_m'])})"
        )
    out.append("")
    out.append("Transfers:")
    if result.transfers:
        for transfer in result.transfers:
            out.append(
                f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )
    else:
        out.append("  None (direct ride)")
    out.append(f"Lines involved: {', '.join(result.lines)}")
    out.append("")
    out.append(f"Total distance: {format_distance(summary['total_distance_m'])}")
    out.append(f"Transfer count: {summary['transfer_count']}")
    out.append(f"Estimated time: {summary['estimated_time_min']:.1f} minutes")
    out.append(f"Fare: {result.fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def to_dict(result):
    """Convert a query result to a JSON-serializable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.line_preference,
        },
        "path": result.stations,
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_m / 1000.0, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": round(result.estimated_time_min, 1),
        "transfer_count": result.transfer_count,
        "transfers": result.transfers,
        "lines": result.lines,
        "segments": result.segments,
        "summary": build_summary(result),
    }


def format_json(result):
    """Render a query result as an indented JSON document."""
    return json.dumps(to_dict(result), ensure_ascii=False, indent=2)


def format_result(result, fmt):
    """Render a result in the requested format ('text' or 'json').

    Raises:
        ValueError: If the format is not supported.
    """
    if not isinstance(result, RouteResult):
        raise TypeError("result must be a RouteResult")
    if fmt == "text":
        return format_text(result)
    if fmt == "json":
        return format_json(result)
    raise ValueError(f"Unsupported output format: {fmt}")
