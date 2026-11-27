"""Route result model and construction from a computed path."""

from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time


@dataclass
class Route:
    """Summary of a computed subway route.

    Attributes:
        station_sequence: Station names from start to end.
        total_distance_meters: Total travel distance in meters.
        transfer_count: Number of line changes.
        estimated_time_minutes: Estimated travel time in minutes.
        involved_lines: Unique line names used, in order of first use.
        fare_yuan: Fare in yuan.
        transfers: List of dicts {station, from_line, to_line}.
        segments: List of dicts {line, start, end, distance_meters}.
    """

    station_sequence: list = field(default_factory=list)
    total_distance_meters: float = 0.0
    transfer_count: int = 0
    estimated_time_minutes: float = 0.0
    involved_lines: list = field(default_factory=list)
    fare_yuan: int = 0
    transfers: list = field(default_factory=list)
    segments: list = field(default_factory=list)

    @property
    def total_distance_km(self):
        """Total travel distance in kilometers."""
        return self.total_distance_meters / 1000.0


def build_route(path_numbers, edges, number_to_name):
    """Build a Route from station numbers and the edges between them.

    Args:
        path_numbers: Station numbers from source to target.
        edges: Edges between consecutive stations (len(path_numbers) - 1 items).
        number_to_name: Mapping station number -> station name.

    Returns:
        Route instance with fare and time computed.

    Raises:
        ValueError: If the path is empty or inconsistent.
    """
    if not path_numbers:
        raise ValueError("Cannot build a route from an empty path")
    if len(edges) != len(path_numbers) - 1:
        raise ValueError("Path and edge lists are inconsistent")

    stations = [number_to_name[number] for number in path_numbers]
    total_distance = sum(edge.distance for edge in edges)

    segments = []
    transfers = []
    involved_lines = []
    for index, edge in enumerate(edges):
        from_station = stations[index]
        to_station = stations[index + 1]
        if not segments or segments[-1]["line"] != edge.line:
            segments.append({
                "line": edge.line,
                "start": from_station,
                "end": to_station,
                "distance_meters": edge.distance,
            })
        else:
            segments[-1]["end"] = to_station
            segments[-1]["distance_meters"] += edge.distance

        if edge.line not in involved_lines:
            involved_lines.append(edge.line)

        if index > 0 and edges[index - 1].line != edge.line:
            transfers.append({
                "station": from_station,
                "from_line": edges[index - 1].line,
                "to_line": edge.line,
            })

    transfer_count = len(transfers)
    fare = Sum_money(total_distance)
    estimated_time = calculate_estimated_time(total_distance, transfer_count)

    return Route(
        station_sequence=stations,
        total_distance_meters=total_distance,
        transfer_count=transfer_count,
        estimated_time_minutes=estimated_time,
        involved_lines=involved_lines,
        fare_yuan=fare,
        transfers=transfers,
        segments=segments,
    )
