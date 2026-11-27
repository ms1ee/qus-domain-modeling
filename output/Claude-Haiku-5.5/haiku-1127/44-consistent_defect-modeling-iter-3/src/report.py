"""Path summary generation and report rendering (text and JSON)."""

import json
from dataclasses import dataclass

from fare_calculator import Sum_money, calculate_estimated_time
from models import Route


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_meters: int
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A rendered report.

    Attributes:
        format: 'text' or 'json'.
        content: Rendered content.
        output_file_path: Path the content was written to, or None.
    """

    format: str
    content: str
    output_file_path: object = None


def build_summary(route: Route) -> PathSummary:
    """Create the path summary (distance, fare, transfers, estimated time)."""
    return PathSummary(
        total_distance_meters=route.total_distance_m,
        total_fare=Sum_money(route.total_distance_m),
        transfer_count=route.transfer_count,
        estimated_time_minutes=round(
            calculate_estimated_time(route.total_distance_m, route.transfer_count), 1),
    )


def format_distance(meters) -> str:
    """Show meters for short distances and kilometers (plus meters) for long ones."""
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters} m)"


def _segments(route):
    """Group consecutive edges on the same line into segments.

    Returns:
        List of (line, first_station, last_station, station_count).
    """
    if not route.edges:
        return []
    segments = []
    start_index = 0
    for i in range(1, len(route.edges)):
        if route.edges[i].line != route.edges[i - 1].line:
            segments.append((route.edges[i - 1].line, route.stations[start_index],
                             route.stations[i], i - start_index + 1))
            start_index = i
    last = len(route.edges)
    segments.append((route.edges[-1].line, route.stations[start_index],
                     route.stations[last], last - start_index + 1))
    return segments


def _query_fields(query):
    """Return query information as plain values."""
    return {
        "start_station": query.start_name,
        "end_station": query.end_name,
        "mode": query.mode,
        "max_transfers": query.max_transfers,
        "line_preference": query.line_preference,
        "timestamp": query.timestamp.isoformat(timespec="seconds"),
    }


def render_text(query, route: Route, summary: PathSummary) -> str:
    """Render a human-readable console report."""
    sep = "=" * 60
    thin = "-" * 60
    max_text = "unlimited" if query.max_transfers is None else str(query.max_transfers)
    preference = query.line_preference or "none"

    lines = [
        sep,
        "Beijing Subway Fare Query",
        sep,
        f"Start station   : {query.start_name}",
        f"End station     : {query.end_name}",
        f"Mode            : {query.mode}",
        f"Max transfers   : {max_text}",
        f"Line preference : {preference}",
        thin,
        "Station sequence (end to start):",
        "  " + " -> ".join(reversed(route.stations)),
        thin,
        "Route details (start to end):",
    ]
    for index, (line, first, last, count) in enumerate(_segments(route), start=1):
        lines.append(f"  {index}. {line}: {first} -> {last} ({count} stations)")
    for transfer in route.transfers:
        lines.append(f"  Transfer at {transfer.station_name}: {transfer.from_line} -> {transfer.to_line}")
    if not route.transfers:
        lines.append("  No transfers required")
    lines.extend([
        thin,
        f"Total distance  : {format_distance(summary.total_distance_meters)}",
        f"Transfers       : {summary.transfer_count}",
        f"Involved lines  : {', '.join(route.involved_lines)}",
        f"Estimated time  : {summary.estimated_time_minutes:.1f} min",
        f"Fare: {summary.total_fare} yuan",
        sep,
    ])
    return "\n".join(lines)


def render_json(query, route: Route, summary: PathSummary) -> str:
    """Render the report as structured JSON."""
    payload = {
        "query": _query_fields(query),
        "path": list(reversed(route.stations)),
        "path_start_to_end": list(route.stations),
        "distance_meters": summary.total_distance_meters,
        "distance_kilometers": round(summary.total_distance_meters / 1000, 3),
        "fare_yuan": summary.total_fare,
        "estimated_time_minutes": summary.estimated_time_minutes,
        "transfer_count": summary.transfer_count,
        "involved_lines": list(route.involved_lines),
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "segments": [
            {"line": line, "from": first, "to": last, "station_count": count}
            for line, first, last, count in _segments(route)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report(query, route: Route, summary: PathSummary, fmt="text", output_file_path=None) -> Report:
    """Render a report in the requested format.

    Raises:
        ValueError: If the format is not 'text' or 'json'.
    """
    if fmt == "text":
        content = render_text(query, route, summary)
    elif fmt == "json":
        content = render_json(query, route, summary)
    else:
        raise ValueError(f"unsupported format '{fmt}'")
    return Report(format=fmt, content=content, output_file_path=output_file_path)
