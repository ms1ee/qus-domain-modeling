"""Path summary generation and report rendering (console text and JSON)."""

import json
from dataclasses import dataclass


class ReportError(Exception):
    """Raised when a report cannot be rendered or written."""


@dataclass
class PathSummary:
    """Key information extracted from a path result."""

    totalDistanceKm: float
    totalFare: int
    transferCount: int
    estimatedTimeMinutes: float


def build_path_summary(result):
    """Extract the summary fields of a ``PathResult``."""
    return PathSummary(
        totalDistanceKm=result.total_distance_km,
        totalFare=result.fare,
        transferCount=result.transfer_count,
        estimatedTimeMinutes=result.estimated_time_minutes,
    )


def build_line_segments(result):
    """Group consecutive edges on the same line into line segments."""
    segments = []
    edges = result.edges
    stations = result.stations
    if not edges:
        return segments
    start = 0
    for index in range(1, len(edges) + 1):
        if index == len(edges) or edges[index].line != edges[start].line:
            segments.append({
                "line": edges[start].line,
                "from_station": stations[start],
                "to_station": stations[index],
                "hops": index - start,
            })
            start = index
    return segments


def format_text(result):
    """Render a human readable console report."""
    summary = build_path_summary(result)
    segments = build_line_segments(result)
    out = []
    out.append("=" * 56)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 56)
    out.append(f"From: {result.start_station}")
    out.append(f"To:   {result.end_station}")
    out.append(f"Mode: {result.mode}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Line preference: {', '.join(result.preferred_lines)}")
    out.append("-" * 56)
    out.append(f"Route ({len(result.stations)} stations):")
    for index, name in enumerate(result.stations, start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("")
    out.append("Line segments:")
    for segment in segments:
        out.append(
            f"  {segment['line']}: {segment['from_station']} -> {segment['to_station']}"
            f" ({segment['hops']} hop(s))"
        )
    out.append("")
    out.append("Transfers:")
    if not result.transfers:
        out.append("  None (direct journey)")
    for transfer in result.transfers:
        out.append(f"  {transfer.station_name}: {transfer.from_line} -> {transfer.to_line}")
    out.append("")
    out.append("-" * 56)
    out.append(f"Total distance: {result.total_distance_m:.0f} m ({summary.totalDistanceKm:.2f} km)")
    out.append(f"Transfers: {summary.transferCount}")
    out.append(f"Lines involved: {', '.join(result.lines)}")
    out.append(f"Estimated time: {summary.estimatedTimeMinutes:.1f} minutes")
    out.append(f"Fare: {summary.totalFare} yuan")
    out.append("=" * 56)
    return "\n".join(out)


def format_json(result):
    """Render a structured JSON report for programmatic integration."""
    summary = build_path_summary(result)
    payload = {
        "query": {
            "start_station": result.start_station,
            "end_station": result.end_station,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
            "timestamp": result.timestamp.isoformat(timespec="seconds"),
        },
        "path": {
            "stations": result.stations,
            "station_count": len(result.stations),
            "segments": build_line_segments(result),
        },
        "distance": {
            "meters": round(result.total_distance_m, 1),
            "kilometers": summary.totalDistanceKm,
        },
        "fare": {
            "amount": summary.totalFare,
            "currency": "CNY",
            "unit": "yuan",
        },
        "estimated_time_minutes": summary.estimatedTimeMinutes,
        "transfer_count": summary.transferCount,
        "transfers": [
            {
                "station": transfer.station_name,
                "from_line": transfer.from_line,
                "to_line": transfer.to_line,
            }
            for transfer in result.transfers
        ],
        "lines": result.lines,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_report(result, fmt="text"):
    """Render a path result in the requested format (``text`` or ``json``)."""
    if fmt == "text":
        return format_text(result)
    if fmt == "json":
        return format_json(result)
    raise ReportError(f"Unsupported output format '{fmt}'")


def write_report(content, output_file, append=False):
    """Write rendered report content to a file.

    Args:
        content: Rendered text.
        output_file: Destination path.
        append: If True, append to the file instead of overwriting it.

    Raises:
        ReportError: If the file cannot be written.
    """
    try:
        with open(output_file, "a" if append else "w", encoding="utf-8") as handle:
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
    except OSError as exc:
        raise ReportError(f"Cannot write output file '{output_file}': {exc}") from exc
