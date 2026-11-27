"""Path visualization and export: console text and structured JSON reports."""

import json
from dataclasses import dataclass

REPORT_FORMATS = ("text", "json")
BAR = "=" * 60


@dataclass
class PathReport:
    """A rendered report.

    Attributes:
        format: "text" or "json".
        content: the rendered string.
    """

    format: str
    content: str


def format_distance(meters):
    """Format a distance: meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def route_to_dict(route):
    """Convert a Route into a JSON-serializable dict."""
    return {
        "query": {
            "start_station": route.start_station,
            "end_station": route.end_station,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.line_preference,
        },
        "path": list(route.station_sequence),
        "distance": {
            "meters": round(route.total_distance_m, 1),
            "kilometers": round(route.total_distance_m / 1000.0, 3),
        },
        "fare_yuan": route.fare_yuan,
        "estimated_time_minutes": round(route.summary.estimated_time_minutes, 1),
        "transfer_count": route.transfer_count,
        "lines_involved": list(route.lines_involved),
        "segments": [
            {
                "line": seg.line_name,
                "start_station": seg.start_station,
                "end_station": seg.end_station,
                "distance_meters": round(seg.distance_m, 1),
                "stations": list(seg.station_sequence),
            }
            for seg in route.segments
        ],
        "transfers": [
            {
                "station": tr.station,
                "from_line": tr.from_line,
                "to_line": tr.to_line,
            }
            for tr in route.transfers
        ],
    }


def render_text(route):
    """Render a Route as human-readable console text."""
    lines = [BAR, "Beijing Subway Fare Report", BAR]
    lines.append(f"Query: {route.start_station} -> {route.end_station}")
    lines.append(f"Mode: {route.mode}")
    lines.append("Max transfers: " + ("unlimited" if route.max_transfers is None else str(route.max_transfers)))
    lines.append("Line preference: " + (route.line_preference or "none"))
    lines.append("")

    lines.append(f"Station sequence ({len(route.station_sequence)} stations):")
    for index, name in enumerate(route.station_sequence, start=1):
        lines.append(f"  {index:>3}. {name}")
    lines.append("")

    lines.append("Line segments:")
    for seg in route.segments:
        stops = len(seg.station_sequence) - 1
        lines.append(
            f"  [{seg.line_name}] {seg.start_station} -> {seg.end_station} "
            f"({format_distance(seg.distance_m)}, {stops} stop(s))"
        )
    lines.append("")

    if route.transfers:
        lines.append(f"Transfers ({len(route.transfers)}):")
        for tr in route.transfers:
            lines.append(f"  - {tr.station}: {tr.from_line} -> {tr.to_line}")
    else:
        lines.append("Transfers: none")
    lines.append("Lines involved: " + ", ".join(route.lines_involved))
    lines.append("")

    lines.append(f"Total distance: {format_distance(route.total_distance_m)}")
    lines.append(f"Transfer count: {route.transfer_count}")
    lines.append(f"Estimated time: {route.summary.estimated_time_minutes:.1f} minutes")
    lines.append(f"Fare: {route.fare_yuan} yuan")
    lines.append(BAR)
    return "\n".join(lines)


def render_json(route):
    """Render a Route as an indented JSON string."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=2)


def build_report(route, fmt="text"):
    """Build a PathReport in the requested format.

    Raises:
        ValueError: If the format is unsupported.
    """
    if fmt == "text":
        return PathReport(format="text", content=render_text(route))
    if fmt == "json":
        return PathReport(format="json", content=render_json(route))
    raise ValueError(f"unsupported output format '{fmt}'")
