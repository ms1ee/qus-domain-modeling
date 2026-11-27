"""Path visualisation and export: console text report, JSON report and path summary."""

import json
from dataclasses import dataclass


@dataclass
class PathSummary:
    """Key information extracted from a route result."""
    total_distance_m: int
    fare_yuan: int
    transfer_count: int
    estimated_time_min: float


def summarize(result):
    """Build a PathSummary from a RouteResult."""
    return PathSummary(
        total_distance_m=result.total_distance_m,
        fare_yuan=result.fare_yuan,
        transfer_count=result.transfer_count,
        estimated_time_min=result.estimated_time_min,
    )


def format_distance(meters):
    """Format a distance: meters for short distances, kilometres (plus meters) for long ones."""
    meters = int(meters)
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters} m)"


def format_text(result):
    """Render a RouteResult as a console-friendly text report."""
    summary = summarize(result)
    max_t = "unlimited" if result.max_transfers is None else str(result.max_transfers)
    pref = result.line_preference or "none"
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query Result")
    out.append("=" * 60)
    out.append(f"From: {result.start}")
    out.append(f"To:   {result.end}")
    out.append(f"Mode: {result.mode} | Max transfers: {max_t} | Line preference: {pref}")
    for note in result.notices:
        out.append(f"Note: {note}")
    out.append("")

    reversed_stations = list(reversed(result.station_sequence))
    out.append(f"Station sequence (ordered from end to start, {len(reversed_stations)} stations):")
    for i, name in enumerate(reversed_stations, 1):
        out.append(f"  {i:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for seg in result.segments:
        stops = len(seg.stations) - 1
        out.append(f"  [{seg.line}] {seg.start_station} -> {seg.end_station} "
                   f"({stops} stops, {format_distance(seg.distance_m)})")
    out.append("")

    out.append("Transfer stations:")
    if result.transfers:
        for t in result.transfers:
            out.append(f"  {t.station_name} (lines: {', '.join(t.involved_lines)})")
    else:
        out.append("  None")
    out.append("")

    out.append(f"Total distance: {format_distance(summary.total_distance_m)}")
    out.append(f"Transfers: {summary.transfer_count}")
    out.append(f"Estimated time: {summary.estimated_time_min:.1f} min")
    out.append(f"Fare: {summary.fare_yuan} yuan")
    return "\n".join(out)


def format_json(result):
    """Render a RouteResult as an indented JSON document for programmatic use."""
    summary = summarize(result)
    payload = {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.line_preference,
        },
        "path": result.station_sequence,
        "distance_m": summary.total_distance_m,
        "distance_km": round(summary.total_distance_m / 1000.0, 3),
        "fare_yuan": summary.fare_yuan,
        "estimated_time_min": round(summary.estimated_time_min, 2),
        "transfer_count": summary.transfer_count,
        "transfers": [
            {"station": t.station_name, "lines": t.involved_lines} for t in result.transfers
        ],
        "lines": result.involved_lines,
        "segments": [
            {
                "line": s.line,
                "start": s.start_station,
                "end": s.end_station,
                "stops": len(s.stations) - 1,
                "distance_m": s.distance_m,
            }
            for s in result.segments
        ],
        "notices": result.notices,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
