"""Visualisation and export of route reports (console text, JSON, summary)."""

import json

from fare_calculator import calculate_estimated_time  # noqa: F401  (re-exported for convenience)


def format_distance(distance_m: int) -> str:
    """Format a distance: meters for short trips, kilometers for long trips."""
    if distance_m < 1000:
        return f"{distance_m} m"
    return f"{distance_m / 1000:.2f} km ({distance_m} m)"


def build_summary(report) -> dict:
    """Extract the key figures of a route report.

    Returns:
        Dictionary with ``distance_m`` (meters only), ``fare``, ``transfers``
        and ``estimated_time_min``.
    """
    return {
        "distance_m": report.distance_m,
        "fare": report.fare,
        "transfers": report.transfer_count,
        "estimated_time_min": report.estimated_time,
    }


def format_text(report) -> str:
    """Render a route report as human readable console text."""
    summary = build_summary(report)
    lines = []
    lines.append("=" * 50)
    lines.append("Beijing Subway Fare Query")
    lines.append("=" * 50)
    for note in report.notes:
        lines.append(f"Note: {note}")
    lines.append(f"Start: {report.start}")
    lines.append(f"End: {report.end}")
    lines.append(f"Mode: {report.mode}")
    if report.max_transfers is not None:
        lines.append(f"Max transfers: {report.max_transfers}")
    if report.preferred_lines:
        lines.append(f"Line preference: {', '.join(report.preferred_lines)}")
    lines.append("")

    lines.append("Station sequence (end -> start):")
    lines.append("  " + " -> ".join(report.stations))
    lines.append("")

    lines.append("Line segments (travel order):")
    if not report.segments:
        lines.append("  (no travel required)")
    for segment in report.segments:
        lines.append(f"  [{segment.line}] " + " -> ".join(segment.stations))
    lines.append("")

    lines.append("Transfers:")
    if report.transfers:
        for transfer in report.transfers:
            lines.append(f"  {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        lines.append("  none")
    lines.append(f"Transfer count: {summary['transfers']}")
    lines.append(f"Lines involved: {', '.join(report.lines) if report.lines else 'none'}")
    lines.append("")

    lines.append(f"Total distance: {format_distance(summary['distance_m'])}")
    lines.append(f"Estimated time: {summary['estimated_time_min']} min")
    lines.append(f"Fare: {summary['fare']} yuan")
    lines.append("=" * 50)
    return "\n".join(lines)


def format_json(report) -> str:
    """Render a route report as a JSON document."""
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
