"""Path visualization, summary generation and report export (text and JSON)."""

import json

from models import PathSummary, Report
from fare_calculator import Sum_money, calculate_estimated_time


def build_summary(path, fare=None):
    """Extract key information (distance, fare, transfers, time) from a path."""
    total_fare = Sum_money(path.total_distance_m) if fare is None else fare
    minutes = calculate_estimated_time(path.total_distance_m, path.transfer_count)
    return PathSummary(
        total_distance_km=round(path.total_distance_m / 1000.0, 3),
        total_fare=total_fare,
        transfer_count=path.transfer_count,
        estimated_time_minutes=minutes,
    )


def format_distance(meters):
    """Format a distance in both meters and kilometers."""
    return f"{meters:.0f} m ({meters / 1000.0:.2f} km)"


def render_text(query, path, summary):
    """Render a human-readable console report."""
    transfer_stations = {t.station for t in path.transfers}
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 60)
    out.append(f"From: {query.start_station}")
    out.append(f"To:   {query.end_station}")
    out.append(f"Mode: {query.mode}")
    if query.max_transfers is not None:
        out.append(f"Max transfers: {query.max_transfers}")
    if query.line_preference:
        out.append(f"Line preference: {query.line_preference}")
    out.append("")

    out.append(f"Route ({len(path.station_sequence)} stations):")
    for idx, name in enumerate(path.station_sequence, start=1):
        marker = "  [transfer]" if name in transfer_stations else ""
        out.append(f"  {idx:>3}. {name}{marker}")
    out.append("")

    out.append("Line segments:")
    if path.segments:
        for seg in path.segments:
            stops = len(seg.stations) - 1
            out.append(f"  {seg.line}: {seg.start} -> {seg.end} "
                       f"({stops} stop(s), {format_distance(seg.distance_m)})")
    else:
        out.append("  None (start and end are the same station)")
    out.append("")

    out.append("Transfer stations:")
    if path.transfers:
        for t in path.transfers:
            out.append(f"  {t.station}: {t.from_line} -> {t.to_line}")
    else:
        out.append("  None (direct journey)")
    out.append("")

    out.append("Summary:")
    out.append(f"  Total distance: {format_distance(path.total_distance_m)}")
    out.append(f"  Transfers: {summary.transfer_count}")
    out.append(f"  Lines involved: {', '.join(path.involved_lines) if path.involved_lines else 'None'}")
    out.append(f"  Estimated time: {summary.estimated_time_minutes} min")
    out.append(f"  Fare: {summary.total_fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def to_json_dict(query, path, summary):
    """Build a JSON-serializable dictionary describing the query result."""
    return {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(path.station_sequence),
        "distance_meters": round(path.total_distance_m, 2),
        "distance_km": summary.total_distance_km,
        "fare_yuan": summary.total_fare,
        "estimated_time_minutes": summary.estimated_time_minutes,
        "transfer_count": summary.transfer_count,
        "involved_lines": list(path.involved_lines),
        "segments": [
            {
                "line": seg.line,
                "start": seg.start,
                "end": seg.end,
                "stations": list(seg.stations),
                "distance_meters": round(seg.distance_m, 2),
            }
            for seg in path.segments
        ],
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in path.transfers
        ],
    }


def make_report(query, path, summary, fmt="text"):
    """Render the query result in the requested format ('text' or 'json')."""
    fmt_lower = str(fmt).lower()
    if fmt_lower == "text":
        content = render_text(query, path, summary)
    elif fmt_lower == "json":
        content = json.dumps(to_json_dict(query, path, summary), ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"Unsupported report format: {fmt}")
    return Report(format=fmt_lower, content=content)
