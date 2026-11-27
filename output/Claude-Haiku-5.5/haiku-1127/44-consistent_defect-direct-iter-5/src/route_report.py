"""Route query results, path summaries and report formatting."""

import json
from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, PathNotFoundError, ShortestPath


@dataclass
class RouteResult:
    """Outcome of a path query.

    ``stations`` and ``edges`` are ordered from the end station back to the
    start station, as produced by backtracking the search tree.
    """

    source: str
    target: str
    mode: str
    stations: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    distance_m: int = 0
    fare: int = 0
    transfer_count: int = 0
    estimated_time: float = 0.0
    lines: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    transfer_points: list = field(default_factory=list)


def _split_segments(network, stations, edges):
    """Split the route into same-line segments and transfer points.

    Segments and transfer points follow the end-to-start ordering of
    ``stations``. ``edges[i]`` connects ``stations[i + 1]`` and ``stations[i]``.
    """
    segments = []
    transfer_points = []
    if not edges:
        return segments, transfer_points

    current_line = edges[0].line
    current_stations = [stations[0]]
    for i, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append({"line": current_line, "stations": current_stations})
            station = stations[i]
            transfer_points.append({
                "station": station,
                "from_line": current_line,
                "to_line": edge.line,
                "lines": network.lines_of(station),
            })
            current_line = edge.line
            current_stations = [stations[i]]
        current_stations.append(stations[i + 1])
    segments.append({"line": current_line, "stations": current_stations})
    return segments, transfer_points


def query_route(network, source_name, target_name, config=None) -> RouteResult:
    """Compute the route, distance, fare and summary between two stations.

    Args:
        network: A ``SubwayNetwork`` instance.
        source_name: Official name of the starting station.
        target_name: Official name of the ending station.
        config: ``PathfindingConfig`` (defaults are used if None).

    Raises:
        ValueError: If the start and end stations are the same.
        PathNotFoundError: If no route satisfies the constraints.
    """
    if config is None:
        config = PathfindingConfig()
    if source_name == target_name:
        raise ValueError("Starting station cannot be the same as the ending station")

    source = network.number_of(source_name)
    target = network.number_of(target_name)
    search = ShortestPath(network.graph, source, config)
    if not search.has_path_to(target):
        constraint = ""
        if config.max_transfers is not None:
            constraint = f" within {config.max_transfers} transfer(s)"
        raise PathNotFoundError(
            f"No route found from '{source_name}' to '{target_name}'{constraint}")

    numbers, edges = search.path_with_edges(target)
    stations = [network.name_of(n) for n in numbers]
    transfers = search.get_transfer_count(target)
    distance = search.dist_to[target]
    fare = Sum_money(distance)
    estimated = calculate_estimated_time(distance, transfers)
    segments, transfer_points = _split_segments(network, stations, edges)

    lines = []
    for segment in segments:
        if segment["line"] not in lines:
            lines.append(segment["line"])

    return RouteResult(
        source=source_name,
        target=target_name,
        mode=config.mode,
        stations=stations,
        edges=edges,
        distance_m=int(distance),
        fare=fare,
        transfer_count=transfers,
        estimated_time=estimated,
        lines=lines,
        segments=segments,
        transfer_points=transfer_points,
    )


def build_summary(result: RouteResult) -> dict:
    """Extract the key figures of a route."""
    return {
        "distance_m": result.distance_m,
        "fare": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": result.estimated_time,
    }


def format_distance(meters) -> str:
    """Format a distance in meters for short values and kilometers for long ones."""
    if meters < 1000:
        return f"{int(meters)} m"
    return f"{meters / 1000:.2f} km ({int(meters)} m)"


def format_text(result: RouteResult) -> str:
    """Render a route as console-formatted text."""
    lines = []
    lines.append("=" * 50)
    lines.append("Beijing Subway Fare Query")
    lines.append("=" * 50)
    lines.append(f"Start: {result.source}")
    lines.append(f"End:   {result.target}")
    lines.append(f"Mode:  {result.mode}")
    lines.append("")
    lines.append("Station sequence (end to start):")
    lines.append("  " + " -> ".join(result.stations))
    lines.append("")
    lines.append(f"Total distance: {format_distance(result.distance_m)}")
    lines.append(f"Transfers: {result.transfer_count}")
    lines.append(f"Estimated time: {result.estimated_time:.2f} minutes")
    lines.append("")
    lines.append("Route segments (end to start):")
    if not result.segments:
        lines.append("  (no travel required)")
    for segment in result.segments:
        lines.append(f"  [{segment['line']}] " + " -> ".join(segment["stations"]))
    lines.append("")
    lines.append("Transfer stations:")
    if not result.transfer_points:
        lines.append("  (none)")
    for point in result.transfer_points:
        lines.append(f"  {point['station']}: {point['from_line']} -> {point['to_line']} "
                     f"(lines serving station: {', '.join(point['lines'])})")
    lines.append("")
    lines.append("Lines involved: " + (", ".join(result.lines) if result.lines else "none"))
    lines.append(f"Fare: {result.fare} yuan")
    lines.append("=" * 50)
    return "\n".join(lines)


def to_json_dict(result: RouteResult) -> dict:
    """Return a JSON-serialisable representation of a route."""
    return {
        "query": {
            "start": result.source,
            "end": result.target,
            "mode": result.mode,
        },
        "path": result.stations,
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_m / 1000.0, 2),
        },
        "fare": result.fare,
        "estimated_time_min": result.estimated_time,
        "transfer_count": result.transfer_count,
        "lines": result.lines,
        "segments": [
            {"line": seg["line"], "stations": seg["stations"]} for seg in result.segments
        ],
        "transfer_stations": [
            {"station": tp["station"], "from_line": tp["from_line"],
             "to_line": tp["to_line"], "lines": tp["lines"]}
            for tp in result.transfer_points
        ],
    }


def format_json(result: RouteResult) -> str:
    """Render a route as a JSON string."""
    return json.dumps(to_json_dict(result), ensure_ascii=False, indent=2)
