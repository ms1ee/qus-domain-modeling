"""Path visualization and export: console text, JSON and summaries."""

import json


def format_distance(distance_m):
    """Format a distance: meters for short distances, kilometers (plus meters) for long ones."""
    if distance_m < 1000:
        return f"{distance_m:.0f} m"
    return f"{distance_m / 1000:.2f} km ({distance_m:.0f} m)"


def build_summary(result):
    """Extract the key figures of a path result.

    Returns:
        dict: total distance (km and m), total fare, transfer count and
        estimated time in minutes.
    """
    return {
        "total_distance_km": round(result.distance_m / 1000.0, 2),
        "total_distance_m": result.distance_m,
        "total_fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": round(result.estimated_time_min, 1),
    }


def format_text(result):
    """Render a path result as human-readable console text."""
    summary = build_summary(result)
    out = []
    out.append("=" * 50)
    out.append("Beijing Subway Route")
    out.append("=" * 50)
    out.append(f"From: {result.start}")
    out.append(f"To:   {result.end}")
    out.append(f"Mode: {result.mode}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Preferred lines: {', '.join(result.preferred_lines)}")
    out.append("")
    out.append(f"Station sequence ({len(result.stations)} stations):")
    for index, name in enumerate(result.stations, start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("")
    out.append("Line segments:")
    for segment in result.segments:
        out.append(f"  [{segment.line}] {' -> '.join(segment.stations)}")
    out.append("")
    if result.transfers:
        out.append(f"Transfers ({len(result.transfers)}):")
        for transfer in result.transfers:
            out.append(f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("Transfers: none required")
    out.append(f"Lines involved: {', '.join(result.lines)}")
    out.append("")
    out.append(f"Total distance: {format_distance(result.distance_m)}")
    out.append(f"Transfer count: {summary['transfer_count']}")
    out.append(f"Estimated time: {summary['estimated_time_min']:.1f} minutes")
    out.append(f"Fare: {result.fare} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def to_dict(result):
    """Convert a path result to a JSON-serialisable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": list(result.stations),
        "distance_m": result.distance_m,
        "distance_km": round(result.distance_m / 1000.0, 3),
        "fare": result.fare,
        "estimated_time_min": round(result.estimated_time_min, 2),
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "lines": list(result.lines),
        "segments": [
            {"line": s.line, "stations": list(s.stations)} for s in result.segments
        ],
    }


def format_json(result, indent=2):
    """Render a path result as a JSON string.

    Args:
        result: PathResult to render.
        indent: Indentation level, or None for compact single-line output.
    """
    return json.dumps(to_dict(result), ensure_ascii=False, indent=indent)
