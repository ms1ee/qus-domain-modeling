"""Path visualisation and report generation (console text and JSON)."""

import json

from pathfinding import MODE_LABELS


def build_summary(result):
    """Build a JSON-serialisable summary dictionary for a route result."""
    total = result.total_distance_m
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": list(result.stations),
        "distance": {
            "meters": total,
            "kilometers": round(total / 1000.0, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": result.estimated_time_min,
        "transfer_count": result.transfer_count,
        "lines": result.lines,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "segments": [
            {
                "line": s.line,
                "from": s.stations[0],
                "to": s.stations[-1],
                "stops": len(s.stations) - 1,
                "distance_m": s.distance_m,
            }
            for s in result.segments
        ],
    }


def format_json(result):
    """Return the route result as an indented JSON string."""
    return json.dumps(build_summary(result), ensure_ascii=False, indent=2)


def format_text(result):
    """Return a human-readable console report of the route."""
    out = []
    out.append(f"Route: {result.start} -> {result.end}")
    out.append(f"Mode: {MODE_LABELS.get(result.mode, result.mode)}")
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
        stops = len(segment.stations) - 1
        out.append(
            f"  [{segment.line}] {segment.stations[0]} -> {segment.stations[-1]} "
            f"({stops} stops, {segment.distance_m:.0f} m)"
        )
    out.append("")

    out.append("Transfers:")
    if not result.transfers:
        out.append("  None (direct journey)")
    else:
        for transfer in result.transfers:
            out.append(
                f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}"
            )
    out.append(f"Lines involved: {', '.join(result.lines)}")
    out.append("")

    kilometers = result.total_distance_m / 1000.0
    out.append(f"Total distance: {result.total_distance_m:.0f} m ({kilometers:.2f} km)")
    out.append(f"Transfer count: {result.transfer_count}")
    out.append(f"Estimated time: {result.estimated_time_min:.1f} min")
    out.append(f"Fare: {result.fare} yuan")
    return "\n".join(out)
