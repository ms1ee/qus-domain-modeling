"""Path visualization and multi-format report export (text and JSON)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Union

from models import Query, Route

SUPPORTED_FORMATS = ("text", "json")


def format_distance(meters: float) -> str:
    """Format a distance: meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_summary(route: Route) -> Dict[str, Any]:
    """Extract the key figures of a route."""
    return {
        "total_distance_km": round(route.total_distance_meters / 1000.0, 2),
        "total_distance_meters": round(route.total_distance_meters, 2),
        "fare_yuan": route.fare_yuan,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": route.estimated_time_minutes,
    }


def render_text(route: Route, query: Query) -> str:
    """Render a route as human-readable console text."""
    rule = "=" * 60
    lines: List[str] = [
        rule,
        "Beijing Subway Fare Report",
        rule,
        f"Query:    {query.start_station} -> {query.end_station}",
        f"Mode:     {query.mode}",
        f"Time:     {query.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Station sequence ({len(route.stations)} stations):",
    ]
    for index, station in enumerate(route.stations, start=1):
        lines.append(f"  {index:>3}. {station}")

    lines.append("")
    lines.append("Line segments:")
    if route.segments:
        for segment in route.segments:
            lines.append(
                f"  [{segment.sequence_number}] {segment.line_name}: "
                f"{segment.start_station} -> {segment.end_station} "
                f"({format_distance(segment.distance_meters)})"
            )
    else:
        lines.append("  (no travel required)")

    lines.append("")
    lines.append("Transfers:")
    if route.transfers:
        for transfer in route.transfers:
            lines.append(f"  - {transfer.station_name}: {transfer.from_line} -> {transfer.to_line}")
    else:
        lines.append("  None")

    summary = build_summary(route)
    lines.append("")
    lines.append(f"Lines involved:   {', '.join(route.lines_involved) if route.lines_involved else 'None'}")
    lines.append(f"Total distance:   {format_distance(route.total_distance_meters)}")
    lines.append(f"Transfer count:   {summary['transfer_count']}")
    lines.append(f"Estimated time:   {summary['estimated_time_minutes']:.1f} minutes")
    lines.append(f"Fare: {summary['fare_yuan']} yuan")
    if route.notes:
        lines.append(f"Note: {route.notes}")
    lines.append(rule)
    return "\n".join(lines)


def build_json_record(route: Route, query: Query) -> Dict[str, Any]:
    """Build the structured (JSON-serializable) representation of a route."""
    return {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "timestamp": query.timestamp.isoformat(timespec="seconds"),
        },
        "path": list(route.stations),
        "distance_meters": round(route.total_distance_meters, 2),
        "distance_kilometers": round(route.total_distance_meters / 1000.0, 2),
        "fare_yuan": route.fare_yuan,
        "estimated_time_minutes": route.estimated_time_minutes,
        "transfer_count": route.transfer_count,
        "lines": list(route.lines_involved),
        "segments": [
            {
                "sequence_number": seg.sequence_number,
                "line": seg.line_name,
                "start_station": seg.start_station,
                "end_station": seg.end_station,
                "distance_meters": round(seg.distance_meters, 2),
            }
            for seg in route.segments
        ],
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "summary": build_summary(route),
    }


class ReportExporter:
    """Renders route reports in the chosen format and optionally writes them to a file.

    Records of all rendered queries are kept, so the output file always contains
    every result of the session (a valid JSON array in json mode).
    """

    def __init__(self, format_name: str = "text", output_file: Optional[str] = None) -> None:
        if format_name not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported format '{format_name}', expected 'text' or 'json'")
        self.format = format_name
        self.output_file = output_file
        self._records: List[Union[str, Dict[str, Any]]] = []

    @property
    def records(self) -> List[Union[str, Dict[str, Any]]]:
        return list(self._records)

    def render(self, route: Route, query: Query) -> str:
        """Render one query result as a string and remember it for export."""
        if self.format == "json":
            record = build_json_record(route, query)
            self._records.append(record)
            return json.dumps(record, ensure_ascii=False, indent=2)
        text = render_text(route, query)
        self._records.append(text)
        return text

    def write(self) -> Optional[str]:
        """Write all recorded results to the output file. Returns the path or None."""
        if not self.output_file:
            return None
        if self.format == "json":
            content = json.dumps(self._records, ensure_ascii=False, indent=2) + "\n"
        else:
            content = "\n\n".join(str(item) for item in self._records) + "\n"
        directory = os.path.dirname(os.path.abspath(self.output_file))
        os.makedirs(directory, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as handle:
            handle.write(content)
        return self.output_file

    def export(self, route: Route, query: Query) -> str:
        """Render a query result and write it to the output file (if configured)."""
        rendered = self.render(route, query)
        self.write()
        return rendered
