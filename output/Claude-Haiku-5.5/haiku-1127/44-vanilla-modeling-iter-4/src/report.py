"""Path visualization and export: summaries, console text and JSON reports."""

import json
import os
from dataclasses import dataclass
from typing import Optional

from fare_calculator import Sum_money, calculate_estimated_time
from models import PathSummary


@dataclass
class Report:
    """A rendered report.

    Attributes:
        format: 'text' or 'json'.
        content: The rendered text.
        output_file: File the report was written to, or None.
    """

    format: str
    content: str
    output_file: Optional[str] = None


def summarize_path(path):
    """Extract distance, fare, transfer count and estimated time from a path."""
    return PathSummary(
        total_distance_km=path.total_distance / 1000.0,
        total_fare=Sum_money(path.total_distance),
        transfer_count=path.transfer_count,
        estimated_time_minutes=calculate_estimated_time(path.total_distance, path.transfer_count),
    )


def format_distance(meters):
    """Show short distances in meters and long ones in kilometers (both given)."""
    kilometers = meters / 1000.0
    if meters < 1000:
        return f"{meters:.0f} m ({kilometers:.2f} km)"
    return f"{kilometers:.2f} km ({meters:.0f} m)"


def build_segments(path):
    """Group consecutive edges on the same line into segments.

    Returns:
        list of (line name, [station names]) tuples.
    """
    names = path.station_sequence
    edges = path.edges
    if not edges:
        return []
    segments = []
    current_line = edges[0].line
    stations = [names[0], names[1]]
    for index in range(1, len(edges)):
        edge = edges[index]
        if edge.line == current_line:
            stations.append(names[index + 1])
        else:
            segments.append((current_line, stations))
            current_line = edge.line
            stations = [names[index], names[index + 1]]
    segments.append((current_line, stations))
    return segments


def format_text(query, path, summary):
    """Render the human-readable console report."""
    max_text = "unlimited" if query.max_transfers is None else str(query.max_transfers)
    lines = [
        "=" * 60,
        "Beijing Subway Fare Query Result",
        "=" * 60,
        f"Starting station : {query.start_station}",
        f"Ending station   : {query.end_station}",
        f"Query mode       : {query.mode}",
        f"Max transfers    : {max_text}",
        f"Line preference  : {query.line_preference or 'none'}",
        "",
        "Route (line segments):",
    ]
    for index, (line, stations) in enumerate(build_segments(path), 1):
        lines.append(f"  {index}. [{line}] " + " -> ".join(stations))
    lines.append("")
    lines.append(f"Station sequence ({len(path.station_sequence)} stations):")
    lines.append("  " + " -> ".join(path.station_sequence))
    lines.append("")
    lines.append("Transfers:")
    if path.transfers:
        for transfer in path.transfers:
            lines.append(f"  - {transfer.station_name}: {' / '.join(transfer.lines)}")
    else:
        lines.append("  None")
    lines.append("")
    lines.append(f"Transfer count   : {summary.transfer_count}")
    lines.append(f"Involved lines   : {', '.join(path.involved_lines)}")
    lines.append(f"Total distance   : {format_distance(path.total_distance)}")
    lines.append(f"Estimated time   : {summary.estimated_time_minutes:.0f} minutes")
    lines.append("")
    lines.append(f"Fare: {summary.total_fare} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(query, path, summary):
    """Render the structured JSON report for programmatic use."""
    payload = {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": {
            "stations": path.station_sequence,
            "transfers": [
                {"station": transfer.station_name, "lines": transfer.lines}
                for transfer in path.transfers
            ],
        },
        "distance": {
            "meters": round(path.total_distance, 2),
            "kilometers": round(path.total_distance / 1000.0, 3),
        },
        "fare": summary.total_fare,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        "transfer_count": summary.transfer_count,
        "involved_lines": path.involved_lines,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report(query, path, fmt="text"):
    """Create a Report of the requested format ('text' or 'json').

    Raises:
        ValueError: If the format is unsupported.
    """
    summary = summarize_path(path)
    if fmt == "text":
        content = format_text(query, path, summary)
    elif fmt == "json":
        content = format_json(query, path, summary)
    else:
        raise ValueError(f"Unsupported format '{fmt}'")
    return Report(format=fmt, content=content)


def write_report(report, output_file):
    """Write a report to ``output_file`` (overwriting it) and return the path."""
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    content = report.content if report.content.endswith("\n") else report.content + "\n"
    with open(output_file, "w", encoding="utf-8") as handle:
        handle.write(content)
    report.output_file = output_file
    return output_file
