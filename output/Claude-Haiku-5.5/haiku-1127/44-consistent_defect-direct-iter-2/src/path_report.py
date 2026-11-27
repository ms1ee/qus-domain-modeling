"""Path visualisation and report export.

Renders a RouteResult as console text or as JSON and writes reports to files.
"""

import json


def format_distance(meters):
    """Format a distance: meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_summary(result):
    """Extract the key figures of a route into a dict."""
    return {
        "total_distance_m": round(result.distance_m, 1),
        "fare": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": round(result.estimated_minutes, 1),
    }


def render_text(result):
    """Render a route as console-formatted text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"Query: {result.start} -> {result.end}")
    lines.append(f"Mode: {result.mode}")
    if result.max_transfers is not None:
        lines.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        lines.append("Line preference: " + ", ".join(result.preferred_lines))
    lines.append("-" * 60)

    lines.append("Station sequence (end -> start):")
    lines.append("  " + " -> ".join(reversed(result.stations)))
    lines.append("")

    lines.append("Route segments (start -> end):")
    for segment in result.segments:
        lines.append(
            f"  [{segment['line']}] " + " -> ".join(segment["stations"])
            + f" ({len(segment['stations']) - 1} stop(s))"
        )
    if result.transfers:
        lines.append("")
        lines.append("Transfers:")
        for transfer in result.transfers:
            lines.append(
                f"  Transfer at {transfer['station']}: "
                f"{transfer['from_line']} -> {transfer['to_line']} "
                f"(station lines: {', '.join(transfer['station_lines'])})"
            )
    else:
        lines.append("")
        lines.append("Transfers: none")

    lines.append("-" * 60)
    lines.append(f"Total distance: {format_distance(result.distance_m)}")
    lines.append(f"Transfers: {result.transfer_count}")
    lines.append(f"Estimated time: {result.estimated_minutes:.1f} min")
    lines.append("Involved lines: " + ", ".join(result.involved_lines))
    lines.append(f"Fare: {result.fare} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_json(result):
    """Render a route as a JSON document for programmatic use."""
    payload = {
        "query": {
            "start": result.start,
            "end": result.end,
            "input_start": result.start_query,
            "input_end": result.end_query,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": list(reversed(result.stations)),
        "path_order": "end_to_start",
        "distance_m": round(result.distance_m, 1),
        "distance_km": round(result.distance_m / 1000.0, 3),
        "fare": result.fare,
        "estimated_time_min": round(result.estimated_minutes, 1),
        "transfer_count": result.transfer_count,
        "involved_lines": list(result.involved_lines),
        "segments": result.segments,
        "transfers": result.transfers,
        "summary": build_summary(result),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_report(content, output_file, append=True):
    """Write a rendered report to a file (appending by default).

    Raises:
        OSError: if the file cannot be written.
    """
    mode = "a" if append else "w"
    with open(output_file, mode, encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n")
