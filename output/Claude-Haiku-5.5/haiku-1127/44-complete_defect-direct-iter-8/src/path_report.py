"""Path visualization, summary generation, and report export."""

import json
import os
from dataclasses import dataclass

from errors import FareCalculationError
from fare_calculator import Sum_money, calculate_estimated_time


@dataclass
class RouteSummary:
    """Key information extracted from a route for presentation and export.

    Attributes:
        origin: Origin station name.
        destination: Destination station name.
        mode: Query mode used.
        stations: Ordered station names from origin to destination.
        segments: List of {"line": str, "stations": [str, ...]} line segments.
        transfers: List of {"station", "from_line", "to_line"} transfer records.
        lines: Unique line names involved, in travel order.
        distance_m: Total distance in meters.
        fare: Fare in yuan.
        transfer_count: Number of transfers.
        estimated_time_min: Estimated travel time in minutes.
    """

    origin: str
    destination: str
    mode: str
    stations: list
    segments: list
    transfers: list
    lines: list
    distance_m: float
    fare: int
    transfer_count: int
    estimated_time_min: float

    @property
    def distance_km(self):
        """Total distance in kilometers, rounded to two decimals."""
        return round(self.distance_m / 1000.0, 2)


def format_distance(meters):
    """Format a distance using meters for short trips and kilometers for long trips."""
    if meters < 1000:
        return f"{int(round(meters))} m ({meters / 1000.0:.2f} km)"
    return f"{meters / 1000.0:.2f} km ({int(round(meters))} m)"


def _build_segments(numbers, edges, name_of):
    """Group consecutive edges on the same line into named segments."""
    if not edges:
        return []
    segments = []
    current_line = edges[0].line
    current = [name_of(numbers[0])]
    for index, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append({"line": current_line, "stations": current})
            current_line = edge.line
            current = [name_of(numbers[index])]  # the interchange station starts the new segment
        current.append(name_of(numbers[index + 1]))
    segments.append({"line": current_line, "stations": current})
    return segments


def build_summary(route, network, origin_name=None, destination_name=None):
    """Create a RouteSummary from a RouteResult.

    Args:
        route: RouteResult from pathfinding.find_route.
        network: SubwayNetwork used for station-number-to-name lookup.
        origin_name, destination_name: Optional names; derived from the route if omitted.

    Raises:
        FareCalculationError: If the fare cannot be calculated.
    """
    stations = [network.name_of(number) for number in route.stations]
    segments = _build_segments(route.stations, route.edges, network.name_of)

    transfers = []
    for previous, following in zip(segments, segments[1:]):
        transfers.append({
            "station": previous["stations"][-1],
            "from_line": previous["line"],
            "to_line": following["line"],
        })

    lines = []
    for segment in segments:
        if segment["line"] not in lines:
            lines.append(segment["line"])

    try:
        fare = Sum_money(route.distance)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    estimated = calculate_estimated_time(route.distance, route.transfer_count)

    return RouteSummary(
        origin=origin_name if origin_name is not None else stations[0],
        destination=destination_name if destination_name is not None else stations[-1],
        mode=route.mode,
        stations=stations,
        segments=segments,
        transfers=transfers,
        lines=lines,
        distance_m=route.distance,
        fare=fare,
        transfer_count=route.transfer_count,
        estimated_time_min=estimated,
    )


def format_text(summary):
    """Render a RouteSummary as console-formatted text."""
    rows = []
    rows.append("=" * 60)
    rows.append(f"Route: {summary.origin} -> {summary.destination}")
    rows.append(f"Query mode: {summary.mode}")
    rows.append(f"Stations passed ({len(summary.stations)}): " + " -> ".join(summary.stations))
    rows.append("Line segments:")
    for index, segment in enumerate(summary.segments, 1):
        rows.append(f"  {index}. [{segment['line']}] " + " -> ".join(segment["stations"]))
    if summary.transfers:
        rows.append("Transfer stations:")
        for transfer in summary.transfers:
            rows.append(f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}")
    else:
        rows.append("Transfer stations: none")
    rows.append(f"Total distance: {format_distance(summary.distance_m)}")
    rows.append(f"Transfers: {summary.transfer_count}")
    rows.append("Lines involved: " + ", ".join(summary.lines))
    rows.append(f"Estimated travel time: {summary.estimated_time_min:.1f} min")
    rows.append(f"Fare: {summary.fare} yuan")
    rows.append("=" * 60)
    return "\n".join(rows)


def to_json_dict(summary):
    """Convert a RouteSummary into a JSON-serializable dictionary."""
    return {
        "query": {
            "origin": summary.origin,
            "destination": summary.destination,
            "mode": summary.mode,
        },
        "path": summary.stations,
        "segments": summary.segments,
        "distance_m": summary.distance_m,
        "distance_km": summary.distance_km,
        "fare": summary.fare,
        "estimated_time_min": summary.estimated_time_min,
        "transfer_count": summary.transfer_count,
        "transfers": summary.transfers,
        "lines": summary.lines,
    }


def format_json(summary):
    """Render a RouteSummary as a JSON document string."""
    return json.dumps(to_json_dict(summary), ensure_ascii=False, indent=2)


def export_report(content, file_path, append=True):
    """Write report content to a file, creating parent directories if needed.

    Args:
        content: Text to write.
        file_path: Destination file path.
        append: If True, append to existing content; otherwise overwrite.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(file_path, mode, encoding="utf-8") as handle:
        handle.write(content)
        handle.write("\n")
