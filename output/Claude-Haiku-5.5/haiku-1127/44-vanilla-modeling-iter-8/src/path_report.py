"""Rendering and exporting of route reports (console text and JSON)."""

import json
import os
from dataclasses import dataclass
from typing import Optional

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)


@dataclass
class PathReport:
    """A rendered report.

    Attributes:
        format: "text" or "json".
        content: The rendered content.
        outputFilePath: Path the report was written to, if any.
    """

    format: str
    content: str
    outputFilePath: Optional[str] = None


def format_distance(meters):
    """Format a distance: meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return "%.0f m (%.2f km)" % (meters, meters / 1000.0)
    return "%.2f km (%.0f m)" % (meters / 1000.0, meters)


def render_text(route):
    """Render a console-friendly text report of a route."""
    transfer_names = set(t.station for t in route.transfers)
    out = []
    out.append("Beijing Subway Fare Query")
    out.append("=" * 50)
    out.append("Start station  : %s" % route.start)
    out.append("End station    : %s" % route.end)
    out.append("Query mode     : %s" % route.mode)
    out.append("Max transfers  : %s" % ("unlimited" if route.max_transfers is None else route.max_transfers))
    out.append("Line preference: %s" % (", ".join(route.line_preference) or "none"))
    out.append("")
    out.append("Stations on route (%d):" % len(route.station_names))
    for index, name in enumerate(route.station_names, start=1):
        mark = "  [transfer]" if name in transfer_names else ""
        out.append("  %3d. %s%s" % (index, name, mark))
    out.append("")
    out.append("Line segments:")
    if not route.segments:
        out.append("  (no travel required)")
    for index, (line, stations) in enumerate(route.segments, start=1):
        out.append("  %d. %s: %s -> %s (%d stops)"
                   % (index, line, stations[0], stations[-1], len(stations) - 1))
    out.append("")
    if route.transfers:
        out.append("Transfers:")
        for transfer in route.transfers:
            out.append("  - %s: %s -> %s" % (transfer.station, transfer.from_line, transfer.to_line))
    else:
        out.append("Transfers: none")
    out.append("Lines involved : %s" % (", ".join(route.lines) or "none"))
    out.append("Total distance : %s" % format_distance(route.total_distance_m))
    out.append("Transfer count : %d" % route.transfer_count)
    out.append("Estimated time : %.1f minutes" % route.estimated_time_min)
    out.append("Fare: %d yuan" % route.fare_yuan)
    return "\n".join(out)


def render_json(route, indent=2):
    """Render a structured JSON report of a route."""
    data = {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.line_preference,
        },
        "path": route.station_names,
        "distance": {
            "meters": round(route.total_distance_m, 1),
            "kilometers": round(route.total_distance_km, 3),
        },
        "fare_yuan": route.fare_yuan,
        "estimated_time_minutes": round(route.estimated_time_min, 1),
        "transfer_count": route.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines": route.lines,
        "composite_score": round(route.composite_score, 3),
    }
    return json.dumps(data, ensure_ascii=False, indent=indent)


def render_report(route, fmt, compact=False):
    """Render a route in the given format ("text" or "json")."""
    if fmt == FORMAT_TEXT:
        return render_text(route)
    if fmt == FORMAT_JSON:
        return render_json(route, indent=None if compact else 2)
    raise ValueError("Unsupported format %r" % (fmt,))


def build_report(route, fmt):
    """Build a ``PathReport`` for a route."""
    return PathReport(format=fmt, content=render_report(route, fmt))


def write_report(report, path, append=False):
    """Write a report to a file, creating parent directories if needed.

    Returns:
        str: the path written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as handle:
        handle.write(report.content)
        handle.write("\n")
        if report.format == FORMAT_TEXT:
            handle.write("-" * 50 + "\n")
    report.outputFilePath = path
    return path
