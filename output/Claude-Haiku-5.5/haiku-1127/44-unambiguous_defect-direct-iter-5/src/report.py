"""Path visualization and export: console text, JSON and file output."""

import json
import os

from fare_calculator import EXTENDED_STEP_M  # noqa: F401  (re-exported for reference)

_RULE = "=" * 60


def _format_distance(meters):
    """Show a distance in meters with its kilometer equivalent."""
    return f"{meters} m ({meters / 1000:.2f} km)"


def build_summary(result):
    """Build the path summary (distance, fare, transfers, time)."""
    return {
        "total_distance_m": result.distance_m,
        "total_distance_km": round(result.distance_m / 1000.0, 3),
        "total_fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": result.estimated_time_min,
    }


def format_text_report(result):
    """Render the human-readable console report of a route result."""
    out = [
        _RULE,
        "Beijing Subway Route Report",
        _RULE,
        f"Starting station : {result.start}",
        f"Ending station   : {result.end}",
        f"Query mode       : {result.mode}",
        "Max transfers    : "
        + ("unlimited" if result.max_transfers is None else str(result.max_transfers)),
        "Line preference  : " + (", ".join(result.preferred_lines) or "none"),
        "",
        f"Route ({len(result.station_names)} stations):",
        "  " + " -> ".join(result.station_names),
        "",
        "Line segments:",
    ]
    for index, segment in enumerate(result.segments, start=1):
        stations = segment["stations"]
        out.append(
            f"  {index}. {segment['line']}: {' -> '.join(stations)} ({len(stations)} stations)"
        )

    out.append("")
    out.append("Transfer details:")
    if result.transfers:
        for transfer in result.transfers:
            out.append(
                f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )
    else:
        out.append("  No transfer required")

    out.extend(
        [
            "",
            f"Lines involved      : {', '.join(result.lines)}",
            f"Total distance      : {_format_distance(result.distance_m)}",
            f"Transfers           : {result.transfer_count}",
            f"Estimated time      : {result.estimated_time_min:.1f} minutes",
            f"Fare: {result.fare} yuan",
            _RULE,
        ]
    )
    return "\n".join(out)


def to_json_dict(result):
    """Convert a route result to a JSON-serializable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": list(result.preferred_lines),
        },
        "path": list(result.station_names),
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_m / 1000.0, 3),
        },
        "fare_yuan": result.fare,
        "estimated_time_min": result.estimated_time_min,
        "transfer_count": result.transfer_count,
        "transfers": list(result.transfers),
        "lines": list(result.lines),
        "segments": list(result.segments),
        "summary": build_summary(result),
    }


def format_json_report(result, compact=False):
    """Serialize a route result to a JSON string.

    Args:
        result: RouteResult to serialize.
        compact: If True, produce a single line (JSON Lines style).
    """
    if compact:
        return json.dumps(to_json_dict(result), ensure_ascii=False)
    return json.dumps(to_json_dict(result), ensure_ascii=False, indent=2)


def write_report(content, path, append=True):
    """Write report content to a file, creating parent directories as needed.

    Args:
        content: Text to write; a trailing newline is ensured.
        path: Destination file path.
        append: If True, append to the file; otherwise overwrite it.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(content.rstrip("\n") + "\n")
