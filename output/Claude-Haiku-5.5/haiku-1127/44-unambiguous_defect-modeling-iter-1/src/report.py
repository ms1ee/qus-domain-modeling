"""Rendering of route results as console text or JSON, and writing to files."""

from __future__ import annotations

import json
import os

from route_planner import RouteResult

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
VALID_FORMATS = (FORMAT_TEXT, FORMAT_JSON)
RECORD_SEPARATOR = "=" * 60


def _number(value: float):
    """Return an int when the float is integral, otherwise a float rounded to 1 decimal."""
    if float(value).is_integer():
        return int(value)
    return round(value, 1)


def build_summary(result: RouteResult) -> dict:
    """Extract the key figures of a route: distance, fare, transfers and time."""
    return {
        "total_distance_km": round(result.total_distance_km, 3),
        "fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_minutes": result.estimated_time_min,
    }


def to_dict(result: RouteResult) -> dict:
    """Convert a route result into a JSON-serialisable dictionary."""
    return {
        "query": {
            "origin": result.origin,
            "destination": result.destination,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": list(result.preferred_lines),
        },
        "path": list(result.stations),
        "segments": [
            {"line": line, "stations": list(stations)} for line, stations in result.segments
        ],
        "distance": {
            "meters": _number(result.total_distance_m),
            "kilometers": round(result.total_distance_km, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": result.estimated_time_min,
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "involved_lines": list(result.involved_lines),
        "summary": build_summary(result),
    }


def format_text(result: RouteResult) -> str:
    """Render a route result as human-readable console text."""
    max_text = "unlimited" if result.max_transfers is None else str(result.max_transfers)
    lines = [
        "Beijing Subway Fare Query",
        f"From: {result.origin}",
        f"To:   {result.destination}",
        f"Mode: {result.mode}    Max transfers: {max_text}",
    ]
    if result.preferred_lines:
        lines.append(f"Line preference: {', '.join(result.preferred_lines)}")

    lines.append("")
    lines.append(f"Route ({len(result.stations)} stations):")
    for index, name in enumerate(result.stations, start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("")
    lines.append("Line segments:")
    for index, (line, stations) in enumerate(result.segments, start=1):
        lines.append(f"  [{index}] {line}: {' -> '.join(stations)}")

    lines.append("")
    lines.append("Transfers:")
    if result.transfers:
        for transfer in result.transfers:
            lines.append(f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        lines.append("  None (no transfer required)")

    lines.append("")
    lines.append(
        f"Total distance: {_number(result.total_distance_m)} m "
        f"({result.total_distance_km:.3f} km)"
    )
    lines.append(f"Transfer count: {result.transfer_count}")
    lines.append(f"Involved lines: {', '.join(result.involved_lines)}")
    lines.append(f"Estimated time: {result.estimated_time_min:.1f} minutes")
    lines.append(f"Fare: {result.fare} yuan")
    return "\n".join(lines)


def format_json(result: RouteResult) -> str:
    """Render a route result as an indented JSON document."""
    return json.dumps(to_dict(result), ensure_ascii=False, indent=2)


def render(result: RouteResult, output_format: str = FORMAT_TEXT) -> str:
    """Render a single route result in the requested format.

    Raises:
        ValueError: If the format is not supported.
    """
    if output_format == FORMAT_TEXT:
        return format_text(result)
    if output_format == FORMAT_JSON:
        return format_json(result)
    raise ValueError(f"unsupported output format '{output_format}'")


def render_many(results: list[RouteResult], output_format: str = FORMAT_TEXT) -> str:
    """Render several route results (one session's queries) as a single document."""
    if output_format == FORMAT_TEXT:
        return f"\n{RECORD_SEPARATOR}\n".join(format_text(r) for r in results)
    if output_format == FORMAT_JSON:
        return json.dumps([to_dict(r) for r in results], ensure_ascii=False, indent=2)
    raise ValueError(f"unsupported output format '{output_format}'")


def write_report(content: str, path: str) -> None:
    """Write report content to a UTF-8 file, creating parent directories as needed.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")
