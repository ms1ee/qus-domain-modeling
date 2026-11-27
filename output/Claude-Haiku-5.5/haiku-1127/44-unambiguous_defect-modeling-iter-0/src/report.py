"""
Path visualization and report export.

Supports console-formatted text and structured JSON output, and can write
reports to a file.
"""

import json

FORMAT_TEXT = "text"
FORMAT_JSON = "json"
SUPPORTED_FORMATS = (FORMAT_TEXT, FORMAT_JSON)


def _format_preferences(query):
    """Return a human-readable description of the query constraints."""
    parts = []
    if query.max_transfers is not None:
        parts.append(f"max transfers: {query.max_transfers}")
    if query.preferred_lines:
        parts.append(f"preferred lines: {', '.join(query.preferred_lines)}")
    return "; ".join(parts) if parts else "none"


def format_text(query, route):
    """Render a route as console-formatted text."""
    lines = []
    lines.append("=" * 64)
    lines.append("Beijing Subway Fare Query")
    lines.append("=" * 64)
    lines.append(f"From: {query.start}")
    lines.append(f"To:   {query.end}")
    lines.append(f"Mode: {query.mode}")
    lines.append(f"Constraints: {_format_preferences(query)}")
    lines.append("-" * 64)

    lines.append(f"Station sequence ({len(route.station_names)} stations):")
    for index, name in enumerate(route.station_names, start=1):
        lines.append(f"  {index:>3}. {name}")

    lines.append("-" * 64)
    lines.append("Line segments:")
    for seg in route.segments:
        lines.append(f"  [{seg['line']}] {seg['from_station']} -> {seg['to_station']} "
                     f"({seg['stops']} stops, {seg['distance_meters']:.0f} m)")

    lines.append("Transfers:")
    if not route.transfers:
        lines.append("  None (direct ride)")
    else:
        for transfer in route.transfers:
            lines.append(f"  - {transfer['station']}: "
                         f"{transfer['from_line']} -> {transfer['to_line']}")
    lines.append(f"Lines involved: {', '.join(route.lines)}")

    lines.append("-" * 64)
    lines.append(f"Total distance: {route.total_distance_meters:.0f} m "
                 f"({route.total_distance_km:.2f} km)")
    lines.append(f"Transfer count: {route.transfer_count}")
    lines.append(f"Estimated time: {route.estimated_time_minutes:.1f} minutes")
    lines.append(f"Fare: {route.fare} yuan")
    lines.append("=" * 64)
    return "\n".join(lines)


def format_json(query, route):
    """Render a route as a JSON document string."""
    payload = {
        "query": query.to_dict(),
        "path": route.station_names,
        "distance_meters": route.total_distance_meters,
        "distance_km": round(route.total_distance_km, 2),
        "fare": route.fare,
        "fare_text": f"Fare: {route.fare} yuan",
        "estimated_time_minutes": route.estimated_time_minutes,
        "transfer_count": route.transfer_count,
        "transfers": route.transfers,
        "lines": route.lines,
        "segments": route.segments,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


class ReportExporter:
    """
    Renders route reports in a chosen format and optionally writes them to a file.

    Attributes:
        format (str): "text" or "json".
        output_file_path (str | None): Destination file, or None for console only.
    """

    def __init__(self, format=FORMAT_TEXT, output_file_path=None):
        if format not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format '{format}'")
        self.format = format
        self.output_file_path = output_file_path

    def prepare_output_file(self):
        """Create or truncate the output file so that results can be appended."""
        if self.output_file_path:
            with open(self.output_file_path, "w", encoding="utf-8"):
                pass

    def render(self, query, route):
        """Return the report as a string in the configured format."""
        if self.format == FORMAT_JSON:
            return format_json(query, route)
        return format_text(query, route)

    def export(self, query, route):
        """
        Render the report and append it to the output file if one is configured.

        Returns:
            str: The rendered report.
        """
        text = self.render(query, route)
        if self.output_file_path:
            with open(self.output_file_path, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")
        return text
