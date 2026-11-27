"""Path visualization and report export.

Renders a ``Route`` as console text or structured JSON and writes reports to
an optional output file.
"""

import json
import os
from typing import Optional

from models import Query, Route

SUPPORTED_FORMATS = ("text", "json")
SEPARATOR = "-" * 60


def format_distance(meters: float) -> str:
    """Format a distance using meters for short and kilometers for long distances."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km"


def format_distance_both(meters: float) -> str:
    """Format a distance in both meters and kilometers, primary unit first."""
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000.0:.2f} km)"
    return f"{meters / 1000.0:.2f} km ({meters:.0f} m)"


def build_summary(route: Route) -> dict:
    """Extract the key summary information of a route."""
    return {
        "total_distance_meters": round(route.total_distance_meters, 1),
        "total_distance_km": round(route.total_distance_km, 2),
        "fare_yuan": route.fare_yuan,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": round(route.estimated_time_minutes, 1),
    }


def format_text(route: Route, query: Query) -> str:
    """Render the route as human-readable console text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"Route: {query.start_station} -> {query.end_station}")
    lines.append(f"Query mode: {query.mode}")
    if query.max_transfers is not None:
        lines.append(f"Maximum transfers: {query.max_transfers}")
    if query.line_preference:
        lines.append(f"Line preference: {query.line_preference}")
    lines.append(SEPARATOR)

    lines.append(f"Station sequence ({len(route.stations)} stations):")
    for index, name in enumerate(route.stations, start=1):
        lines.append(f"  {index:>3}. {name}")
    lines.append(SEPARATOR)

    lines.append("Line segments:")
    for segment in route.segments:
        lines.append(
            f"  [{segment.line_name}] {segment.start_station} -> {segment.end_station} "
            f"({segment.hop_count} hop(s), {format_distance(segment.distance_meters)})"
        )

    lines.append("Transfer details:")
    if route.transfers:
        for transfer in route.transfers:
            lines.append(
                f"  Transfer at {transfer.station_name}: "
                f"{transfer.from_line} -> {transfer.to_line}"
            )
    else:
        lines.append("  No transfer required")
    lines.append(f"Lines involved: {', '.join(route.lines_involved)}")
    lines.append(f"Transfer count: {route.transfer_count}")
    lines.append(SEPARATOR)

    lines.append(f"Total distance: {format_distance_both(route.total_distance_meters)}")
    lines.append(f"Estimated time: {route.estimated_time_minutes:.1f} minutes")
    lines.append(f"Fare: {route.fare_yuan} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(route: Route, query: Query) -> str:
    """Render the route as a JSON document for programmatic integration."""
    summary = build_summary(route)
    payload = {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": list(route.stations),
        "distance": {
            "meters": summary["total_distance_meters"],
            "kilometers": summary["total_distance_km"],
        },
        "fare": {"yuan": route.fare_yuan},
        "estimated_time_minutes": summary["estimated_time_minutes"],
        "transfer_count": route.transfer_count,
        "transfers": [
            {
                "station": transfer.station_name,
                "from_line": transfer.from_line,
                "to_line": transfer.to_line,
            }
            for transfer in route.transfers
        ],
        "lines": list(route.lines_involved),
        "segments": [
            {
                "line": segment.line_name,
                "start_station": segment.start_station,
                "end_station": segment.end_station,
                "distance_meters": round(segment.distance_meters, 1),
                "hop_count": segment.hop_count,
            }
            for segment in route.segments
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_report(route: Route, query: Query, format_name: str) -> str:
    """Render a route in the requested format ('text' or 'json')."""
    if format_name == "text":
        return format_text(route, query)
    if format_name == "json":
        return format_json(route, query)
    raise ValueError(f"Unsupported output format '{format_name}'")


class Report:
    """A rendered path report that can be exported to a file.

    Attributes:
        format: Output format, 'text' or 'json'.
        output_file: Optional destination file path.
        content: The rendered report text.
    """

    def __init__(self, format_name: str, output_file: Optional[str] = None, content: str = "") -> None:
        if format_name not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported output format '{format_name}'")
        self.format = format_name
        self.output_file = output_file
        self.content = content

    @classmethod
    def from_route(
        cls,
        route: Route,
        query: Query,
        format_name: str,
        output_file: Optional[str] = None,
    ) -> "Report":
        """Render a route and wrap it in a ``Report``."""
        return cls(format_name, output_file, render_report(route, query, format_name))

    def write(self) -> Optional[str]:
        """Write the content to the output file, if one is configured.

        Returns:
            The path written to, or None when no output file is configured.

        Raises:
            OSError: If the file cannot be written.
        """
        if not self.output_file:
            return None
        directory = os.path.dirname(os.path.abspath(self.output_file))
        os.makedirs(directory, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as handle:
            handle.write(self.content)
            if not self.content.endswith("\n"):
                handle.write("\n")
        return self.output_file
