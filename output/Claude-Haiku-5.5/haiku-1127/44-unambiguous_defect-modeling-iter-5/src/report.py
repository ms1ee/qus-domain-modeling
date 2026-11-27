"""Path visualization and export: console text, JSON, and file output."""

import json
import os


def build_summary(result):
    """Return the key figures of a route as a dictionary (PathSummary)."""
    return {
        "total_distance_km": round(result.distance_m / 1000.0, 3),
        "total_fare_yuan": result.fare_yuan,
        "transfer_count": result.transfer_count,
        "estimated_time_minutes": result.estimated_time_minutes,
    }


def format_text(result):
    """Render a RouteResult as human-readable console text."""
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Route Query")
    out.append("=" * 60)
    out.append(f"From:            {result.start_station}")
    out.append(f"To:              {result.end_station}")
    out.append(f"Mode:            {result.mode}")
    out.append(f"Max transfers:   {result.max_transfers if result.max_transfers is not None else 'unlimited'}")
    out.append(f"Line preference: {result.line_preference or 'none'}")
    out.append("")
    out.append(f"Route ({len(result.station_names)} stations):")
    for idx, name in enumerate(result.station_names, start=1):
        out.append(f"  {idx:>3}. {name}")
    out.append("")
    out.append("Line segments:")
    for idx, seg in enumerate(result.segments, start=1):
        out.append(
            f"  {idx}. [{seg.line}] {seg.start_station} -> {seg.end_station} "
            f"({seg.station_count} stations, {seg.distance_m:.0f} m)"
        )
    out.append("")
    out.append("Transfers:")
    if not result.transfers:
        out.append("  None (direct ride)")
    else:
        for t in result.transfers:
            out.append(f"  - {t.station}: {t.from_line} -> {t.to_line}")
    out.append("")
    km = result.distance_m / 1000.0
    out.append(f"Total distance:  {result.distance_m:.0f} m ({km:.2f} km)")
    out.append(f"Transfer count:  {result.transfer_count}")
    out.append(f"Lines involved:  {', '.join(result.lines)}")
    out.append(f"Estimated time:  {result.estimated_time_minutes:.1f} min")
    out.append(f"Fare: {result.fare_yuan} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(result):
    """Render a RouteResult as a JSON document for programmatic use."""
    data = {
        "query": {
            "start": result.start_station,
            "end": result.end_station,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.line_preference,
        },
        "path": list(result.station_names),
        "distance_meters": round(result.distance_m, 2),
        "distance_km": round(result.distance_m / 1000.0, 3),
        "fare": result.fare_yuan,
        "estimated_time_minutes": result.estimated_time_minutes,
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "lines": list(result.lines),
        "segments": [
            {
                "line": s.line,
                "start_station": s.start_station,
                "end_station": s.end_station,
                "station_count": s.station_count,
                "distance_meters": s.distance_m,
            }
            for s in result.segments
        ],
        "summary": build_summary(result),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def write_report(content, path, append=False):
    """Write report content to a file, creating parent directories as needed.

    Returns:
        Absolute path of the written file.
    """
    absolute = os.path.abspath(path)
    directory = os.path.dirname(absolute)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(absolute, "a" if append else "w", encoding="utf-8") as fh:
        fh.write(content)
    return absolute
