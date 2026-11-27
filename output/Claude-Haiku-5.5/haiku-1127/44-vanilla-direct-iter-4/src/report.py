"""Path visualisation and report export (console text and JSON)."""

import json

from fare_calculator import format_fare


def format_distance(meters):
    """Format a distance in meters and kilometers.

    Short distances (< 1 km) are shown in meters first; longer ones in kilometers first.
    """
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000:.3f} km)"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def _short_distance(meters):
    """Format a segment distance compactly."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km"


def summarize(result):
    """Extract key summary values from a query result."""
    return {
        "total_distance_km": result["distance_km"],
        "total_fare_yuan": result["fare"],
        "transfer_count": result["transfer_count"],
        "estimated_time_min": result["estimated_time_min"],
    }


def format_text(result):
    """Render a query result as console-formatted text."""
    query = result["query"]
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Route")
    out.append("=" * 60)
    out.append(f"From: {query['start']}")
    out.append(f"To:   {query['end']}")
    out.append(f"Mode: {query['mode']}")
    if query["max_transfers"] is not None:
        out.append(f"Max transfers: {query['max_transfers']}")
    if query["preferred_lines"]:
        out.append(f"Preferred lines: {', '.join(query['preferred_lines'])}")
    out.append("-" * 60)

    out.append(f"Station sequence ({result['station_count']} stations):")
    for index, name in enumerate(result["path"], start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("-" * 60)

    out.append("Line segments:")
    for seg in result["segments"]:
        out.append(f"  [{seg['line']}] {seg['from']} -> {seg['to']} ({_short_distance(seg['distance_m'])})")

    out.append("Transfer stations:")
    if not result["transfer_stations"]:
        out.append("  None (direct trip)")
    else:
        for transfer in result["transfer_stations"]:
            out.append(f"  {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}")
    out.append(f"Lines involved: {', '.join(result['lines'])}")
    out.append("-" * 60)

    out.append(f"Total distance: {format_distance(result['distance_m'])}")
    out.append(f"Transfers: {result['transfer_count']}")
    out.append(f"Estimated time: {result['estimated_time_min']:.1f} minutes")
    out.append(format_fare(result["fare"]))
    out.append("=" * 60)
    return "\n".join(out)


def to_json_dict(result):
    """Convert a query result into the structured JSON layout."""
    return {
        "query": result["query"],
        "path": result["path"],
        "distance": {
            "meters": result["distance_m"],
            "kilometers": result["distance_km"],
        },
        "fare": result["fare"],
        "estimated_time_minutes": result["estimated_time_min"],
        "transfer_count": result["transfer_count"],
        "lines": result["lines"],
        "segments": result["segments"],
        "transfer_stations": result["transfer_stations"],
    }


def format_json(result, indent=2):
    """Render a query result as a JSON string.

    Args:
        result: Query result dict.
        indent: Indentation width; use None for a single compact line.
    """
    return json.dumps(to_json_dict(result), ensure_ascii=False, indent=indent)
