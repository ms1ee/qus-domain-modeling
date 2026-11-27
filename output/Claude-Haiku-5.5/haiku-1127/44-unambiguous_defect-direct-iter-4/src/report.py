"""Path visualization and export: console text and structured JSON reports."""

import json

MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Minimum transfers",
    "comprehensive": "Comprehensive optimal",
}


def result_to_dict(result) -> dict:
    """Convert a RouteResult into a JSON-serializable dictionary."""
    return {
        "query": {
            "start": result.start,
            "destination": result.destination,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": list(result.preferred_lines),
        },
        "path": list(result.stations),
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_km, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": result.estimated_minutes,
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "lines": list(result.lines),
        "segments": [
            {
                "line": s.line,
                "start": s.start,
                "end": s.end,
                "stop_count": s.stop_count,
                "distance_m": s.distance_m,
            }
            for s in result.segments
        ],
        "summary": result.to_summary(),
    }


def format_text(result) -> str:
    """Return a console-formatted report for one route result."""
    rule = "=" * 64
    out = [rule]
    out.append(f"Route: {result.start} -> {result.destination}")
    out.append(f"Mode: {MODE_LABELS.get(result.mode, result.mode)}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Line preference: {', '.join(result.preferred_lines)}")
    out.append("-" * 64)

    out.append("Route details:")
    for index, segment in enumerate(result.segments, 1):
        out.append(
            f"  [{index}] {segment.line}: {segment.start} -> {segment.end} "
            f"({segment.stop_count} stations, {segment.distance_m} m)"
        )
        if index < len(result.segments):
            transfer = result.transfers[index - 1]
            out.append(f"      >> Transfer at {transfer.station}: "
                       f"{transfer.from_line} -> {transfer.to_line}")
    if not result.segments:
        out.append("  (no travel required)")
    out.append("")

    out.append(f"Station sequence ({len(result.stations)} stations):")
    for position, name in enumerate(result.stations, 1):
        out.append(f"  {position:>3}. {name}")
    out.append("")

    out.append("Summary:")
    out.append(f"  Total distance: {result.distance_m} m ({result.distance_km:.2f} km)")
    out.append(f"  Transfers: {result.transfer_count}")
    if result.transfers:
        for transfer in result.transfers:
            out.append(f"    - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    out.append(f"  Lines involved: {', '.join(result.lines) if result.lines else 'None'}")
    out.append(f"  Estimated time: {result.estimated_minutes:.1f} min")
    out.append(f"  Fare: {result.fare} yuan")
    out.append(rule)
    return "\n".join(out)


def format_json(result) -> str:
    """Return the JSON report for one route result."""
    return json.dumps(result_to_dict(result), ensure_ascii=False, indent=2)


def format_text_session(results) -> str:
    """Return text reports for several results separated by blank lines."""
    return "\n\n".join(format_text(result) for result in results)


def format_json_session(results) -> str:
    """Return a JSON array containing the reports of several results."""
    return json.dumps([result_to_dict(result) for result in results],
                      ensure_ascii=False, indent=2)
