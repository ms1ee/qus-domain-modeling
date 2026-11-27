"""Report rendering (console text and JSON) and file export."""

import json
import os
from typing import Any, Dict, Iterable, List

from route import Route

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)


def _format_distance(meters: float) -> str:
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km"


def format_route_text(route: Route) -> str:
    """Render a route as human-readable console text."""
    query = route.query
    summary = route.summary()
    rule = "-" * 60
    lines: List[str] = [
        "=" * 60,
        "Beijing Subway Fare Query",
        "=" * 60,
        f"Start station   : {query.start_station}",
        f"End station     : {query.end_station}",
        f"Query mode      : {query.mode}",
        "Max transfers   : "
        + (str(query.max_transfers) if query.max_transfers is not None else "unlimited"),
        f"Line preference : {query.line_preference or 'none'}",
        rule,
        f"Route ({len(route.stations)} stations):",
    ]
    for index, name in enumerate(route.stations, 1):
        lines.append(f"  {index:>3}. {name}")
    lines.append(rule)
    lines.append("Line segments:")
    if route.segments:
        for segment in route.segments:
            lines.append(
                f"  [{segment.line}] {segment.start_station} -> {segment.end_station} "
                f"({segment.station_count} stations, {_format_distance(segment.distance_meters)})"
            )
    else:
        lines.append("  (none - start and end are the same station)")
    lines.append("Transfers:")
    if route.transfers:
        for transfer in route.transfers:
            lines.append(f"  {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        lines.append("  None (direct ride)")
    lines.append(rule)
    lines.append(
        f"Total distance  : {route.total_distance_meters:.0f} m "
        f"({summary.total_distance_km:.2f} km)"
    )
    lines.append(f"Transfer count  : {summary.transfer_count}")
    lines.append(f"Involved lines  : {', '.join(route.involved_lines) or 'none'}")
    lines.append(f"Estimated time  : {summary.estimated_time_minutes:.1f} min")
    lines.append(f"Fare: {route.fare_yuan} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def route_to_dict(route: Route) -> Dict[str, Any]:
    """Convert a route into a JSON-serialisable dictionary."""
    query = route.query
    summary = route.summary()
    return {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(route.stations),
        "distance_meters": round(route.total_distance_meters, 1),
        "distance_km": summary.total_distance_km,
        "fare_yuan": route.fare_yuan,
        "estimated_time_minutes": route.estimated_time_minutes,
        "transfer_count": route.transfer_count,
        "involved_lines": list(route.involved_lines),
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "segments": [
            {
                "line": s.line,
                "start_station": s.start_station,
                "end_station": s.end_station,
                "distance_meters": round(s.distance_meters, 1),
                "station_count": s.station_count,
            }
            for s in route.segments
        ],
    }


def render_reports(routes: Iterable[Route], fmt: str) -> str:
    """Render several routes into one document of the requested format."""
    if fmt == FORMAT_TEXT:
        return "\n\n".join(format_route_text(route) for route in routes) + "\n"
    if fmt == FORMAT_JSON:
        return json.dumps([route_to_dict(route) for route in routes], ensure_ascii=False, indent=2) + "\n"
    raise ValueError(f"Unsupported format '{fmt}'")


def write_report_file(path: str, content: str) -> None:
    """Write report content to a UTF-8 file, creating parent directories."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
