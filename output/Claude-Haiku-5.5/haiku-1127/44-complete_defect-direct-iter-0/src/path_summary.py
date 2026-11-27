"""Route query service: computes a complete route summary for two stations.

The summary is a plain dictionary that the visualization module renders as
console text or JSON. It contains the station sequence, line segments,
transfer details, total distance, fare, transfer count and estimated time.
"""

from typing import Any, Dict, List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class QueryError(Exception):
    """Base class for errors raised while answering a route query."""


class StationNotFoundError(QueryError):
    """Raised when a station name does not exist in the network."""


class RouteNotFoundError(QueryError):
    """Raised when no route exists under the current settings."""


class FareCalculationError(QueryError):
    """Raised when the fare or time calculation fails."""


def _build_segments(network: Any, nodes: List[int], edges: List[Any]) -> List[Dict[str, Any]]:
    """Group consecutive edges served by the same line into segments."""
    segments: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for index, edge in enumerate(edges):
        from_name = network.number_to_station[nodes[index]]
        to_name = network.number_to_station[nodes[index + 1]]
        if current is None or current["line"] != edge.line:
            current = {
                "line": edge.line,
                "from": from_name,
                "to": to_name,
                "stations": [from_name, to_name],
                "distance_m": 0,
            }
            segments.append(current)
        else:
            current["to"] = to_name
            current["stations"].append(to_name)
        current["distance_m"] += edge.distance
    return segments


def _build_transfers(segments: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Describe every line change: station, leaving line and joining line."""
    transfers: List[Dict[str, str]] = []
    for index in range(len(segments) - 1):
        transfers.append({
            "station": segments[index]["to"],
            "from_line": segments[index]["line"],
            "to_line": segments[index + 1]["line"],
        })
    return transfers


def compute_route_summary(network: Any, start_name: str, end_name: str,
                          config: Optional[PathfindingConfig] = None) -> Dict[str, Any]:
    """Compute the optimal route between two stations and its summary.

    Args:
        network: A subway_network.SubwayNetwork instance.
        start_name: Starting station (official or lenient name).
        end_name: Ending station (official or lenient name).
        config: Path query configuration (defaults to shortest distance).

    Returns:
        Dictionary with keys: query, path, stations_count, distance_m,
        distance_km, fare, estimated_time_min, transfer_count, lines,
        segments, transfers.

    Raises:
        StationNotFoundError: If a station name is unknown.
        QueryError: If the start equals the end or the configuration is invalid.
        RouteNotFoundError: If no route satisfies the constraints.
        FareCalculationError: If fare or time calculation fails.
    """
    config = config if config is not None else PathfindingConfig()
    try:
        config.validate()
    except ValueError as exc:
        raise QueryError(f"Invalid query settings: {exc}") from exc

    start = network.official_name(start_name)
    if start is None:
        raise StationNotFoundError(
            f"Starting station '{start_name}' does not exist, please check the station name"
        )
    end = network.official_name(end_name)
    if end is None:
        raise StationNotFoundError(
            f"Ending station '{end_name}' does not exist, please check the station name"
        )
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    source = network.station_to_number[start]
    target = network.station_to_number[end]
    try:
        shortest = ShortestPath(network.graph, source, config)
    except ValueError as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    if not shortest.has_path_to(target):
        raise RouteNotFoundError(
            f"No route found from '{start}' to '{end}' under the current settings"
        )

    nodes, edges = shortest.path_with_edges(target)
    transfer_count = shortest.get_transfer_count(target)
    path_names = [network.number_to_station[node] for node in nodes]
    distance_m = sum(edge.distance for edge in edges)
    segments = _build_segments(network, nodes, edges)
    transfers = _build_transfers(segments)

    lines: List[str] = []
    for segment in segments:
        if segment["line"] not in lines:
            lines.append(segment["line"])

    try:
        fare = Sum_money(distance_m)
        estimated_time = calculate_estimated_time(distance_m, transfer_count)
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    return {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": path_names,
        "stations_count": len(path_names),
        "distance_m": distance_m,
        "distance_km": round(distance_m / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": estimated_time,
        "transfer_count": transfer_count,
        "lines": lines,
        "segments": segments,
        "transfers": transfers,
    }
