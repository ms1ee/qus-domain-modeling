"""
Path visualization, summary generation and report export.

Renders a RouteResult as console text or as a JSON document and writes
reports to files.
"""

import json

FORMAT_TEXT = "text"
FORMAT_JSON = "json"


def format_distance(meters):
    """Show short distances in meters and long distances in kilometers (with meters)."""
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters:,} m)"


def build_summary(result):
    """
    Extract the key summary information of a route.

    Returns:
        dict with total distance (meters), fare, transfer count and
        estimated travel time (minutes).
    """
    return {
        "total_distance_m": result.distance_m,
        "fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_minutes": round(result.estimated_minutes, 1),
    }


def format_text(result):
    """Render a RouteResult as human-readable console text."""
    summary = build_summary(result)
    out = []
    out.append("=" * 56)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 56)
    out.append(f"Starting station : {result.origin}")
    out.append(f"Ending station   : {result.destination}")
    out.append(f"Query mode       : {result.mode}")
    if result.max_transfers is not None:
        out.append(f"Max transfers    : {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Preferred lines  : {', '.join(result.preferred_lines)}")
    out.append("")
    out.append("Station sequence (end -> start):")
    out.append("  " + " -> ".join(result.stations))
    out.append("")
    out.append("Line segments (travel order):")
    for index, seg in enumerate(result.segments, 1):
        out.append(f"  {index}. {seg.line}: {seg.start} -> {seg.end} ({seg.stops} section(s))")
    out.append("")
    if result.transfers:
        out.append("Transfer stations:")
        for t in result.transfers:
            out.append(f"  * {t.station}: {t.from_line} -> {t.to_line}")
    else:
        out.append("Transfer stations: none")
    out.append("")
    out.append(f"Lines involved   : {', '.join(result.lines)}")
    out.append(f"Total distance   : {format_distance(summary['total_distance_m'])}")
    out.append(f"Transfer count   : {summary['transfer_count']}")
    out.append(f"Estimated time   : {summary['estimated_time_minutes']} minutes")
    out.append(f"Fare: {result.fare} yuan")
    return "\n".join(out)


def to_dict(result):
    """Convert a RouteResult into a JSON-serializable dictionary."""
    return {
        "query": {
            "origin": result.origin,
            "destination": result.destination,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "preferred_lines": result.preferred_lines,
        },
        "path": result.stations,
        "segments": [
            {"line": s.line, "start": s.start, "end": s.end, "stops": s.stops}
            for s in result.segments
        ],
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_m / 1000.0, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": round(result.estimated_minutes, 1),
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "lines": result.lines,
    }


def format_json(result):
    """Render a RouteResult as an indented JSON string."""
    return json.dumps(to_dict(result), ensure_ascii=False, indent=2)


def render(result, fmt=FORMAT_TEXT):
    """Render a RouteResult in the requested format ('text' or 'json')."""
    if fmt == FORMAT_JSON:
        return format_json(result)
    if fmt == FORMAT_TEXT:
        return format_text(result)
    raise ValueError(f"Unsupported output format '{fmt}'")


def write_output(content, path):
    """Append a rendered report to a file, creating it if necessary."""
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(content)
        fh.write("\n\n")
