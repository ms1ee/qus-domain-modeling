"""Route report generation: text and JSON formats plus path summaries."""

import json


def format_distance(distance_m):
    """Format a distance: meters for short distances, kilometers for long ones."""
    km = distance_m / 1000.0
    if distance_m < 1000:
        return f"{distance_m:.0f} m ({km:.2f} km)"
    return f"{km:.2f} km ({distance_m:.0f} m)"


class Summary:
    """Key figures extracted from a route.

    Attributes:
        total_distance_km: Travel distance in kilometers.
        total_fare: Fare in yuan.
        transfer_count: Number of transfers.
        estimated_time_minutes: Estimated travel time in minutes.
    """

    def __init__(self, route):
        self.total_distance_km = round(route.distance_m / 1000.0, 3)
        self.total_fare = route.fare
        self.transfer_count = route.transfer_count
        self.estimated_time_minutes = round(route.estimated_time_minutes, 2)

    def to_dict(self):
        """Return the summary as a dictionary."""
        return {
            "total_distance_km": self.total_distance_km,
            "total_fare": self.total_fare,
            "transfer_count": self.transfer_count,
            "estimated_time_minutes": self.estimated_time_minutes,
        }


def build_summary(route):
    """Create a ``Summary`` for a route."""
    return Summary(route)


def _mode_description(route):
    config = route.config
    max_text = "unlimited" if config.max_transfers is None else str(config.max_transfers)
    pref_text = ", ".join(config.preferred_lines) if config.preferred_lines else "none"
    return f"Mode: {config.mode} | Max transfers: {max_text} | Line preference: {pref_text}"


def format_text(route):
    """Render a route as console-friendly text."""
    summary = build_summary(route)
    lines = []
    lines.append("=" * 60)
    lines.append("Beijing Subway Route")
    lines.append("=" * 60)
    lines.append(f"Query: {route.start_station} -> {route.end_station}")
    lines.append(_mode_description(route))
    lines.append("")
    lines.append(f"Station sequence ({len(route.stations)} stations):")
    for index, name in enumerate(route.stations, start=1):
        lines.append(f"  {index:>3}. {name}")
    lines.append("")
    lines.append("Line segments:")
    for segment in route.segments:
        stations = segment["stations"]
        lines.append(
            f"  [{segment['line']}] {stations[0]} -> {stations[-1]} "
            f"({len(stations)} stations)"
        )
    lines.append("")
    if route.transfer_details:
        lines.append(f"Transfer stations ({len(route.transfer_details)}):")
        for item in route.transfer_details:
            lines.append(f"  - {item['station']}: {item['from_line']} -> {item['to_line']}")
    else:
        lines.append("Transfer stations: none (direct route)")
    lines.append(f"Lines involved: {', '.join(route.lines)}")
    lines.append("")
    lines.append(f"Total distance: {format_distance(route.distance_m)}")
    lines.append(f"Transfers: {summary.transfer_count}")
    lines.append(f"Estimated time: {summary.estimated_time_minutes:.1f} min")
    lines.append(f"Fare: {route.fare} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(route):
    """Render a route as a JSON string for programmatic use."""
    summary = build_summary(route)
    payload = {
        "query": {
            "start_station": route.start_station,
            "end_station": route.end_station,
            "mode": route.config.mode,
            "max_transfers": route.config.max_transfers,
            "line_preference": route.config.preferred_lines,
        },
        "path": route.stations,
        "distance_m": route.distance_m,
        "distance_km": summary.total_distance_km,
        "fare": route.fare,
        "estimated_time_minutes": summary.estimated_time_minutes,
        "transfer_count": route.transfer_count,
        "transfer_stations": route.transfer_stations,
        "transfer_details": route.transfer_details,
        "lines": route.lines,
        "segments": route.segments,
        "summary": summary.to_dict(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_report(route, fmt="text"):
    """Render a route in the requested format ('text' or 'json').

    Raises:
        ValueError: If the format is unsupported.
    """
    if fmt == "text":
        return format_text(route)
    if fmt == "json":
        return format_json(route)
    raise ValueError(f"Unsupported output format '{fmt}'")
