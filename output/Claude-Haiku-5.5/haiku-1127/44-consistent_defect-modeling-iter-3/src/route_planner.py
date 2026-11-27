"""Route planning: combines the network model with path search."""

from models import Route, TransferPoint
from pathfinding import ShortestPath, PathfindingConfig


class PathNotFoundError(Exception):
    """Raised when no path satisfying the constraints exists."""


def _extract_transfers(stations, edges):
    """Identify line changes along a route.

    Args:
        stations: Station names from start to end.
        edges: Edges traversed in order (len(stations) - 1 items).
    """
    transfers = []
    for i in range(1, len(edges)):
        previous, current = edges[i - 1], edges[i]
        if previous.line != current.line:
            transfers.append(TransferPoint(stations[i], previous.line, current.line))
    return transfers


def plan_route(network, start_name, end_name, config=None) -> Route:
    """Compute the optimal route between two stations.

    Args:
        network: network.SubwayNetwork instance.
        start_name: Exact name of the starting station.
        end_name: Exact name of the ending station.
        config: pathfinding.PathfindingConfig (defaults to shortest distance).

    Returns:
        A models.Route describing the journey.

    Raises:
        PathNotFoundError: If the destination cannot be reached under the constraints.
    """
    config = config or PathfindingConfig()
    src = network.station_number(start_name)
    dst = network.station_number(end_name)

    searcher = ShortestPath(network.graph, src, config)
    if not searcher.has_path_to(dst):
        raise PathNotFoundError(
            f"no route from '{start_name}' to '{end_name}'"
            + (f" with at most {config.max_transfers} transfer(s)" if config.max_transfers is not None else ""))

    numbers, edges = searcher.path_with_edges(dst)
    stations = [network.station_name(n) for n in numbers]
    total_distance = sum(edge.distance for edge in edges)
    transfers = _extract_transfers(stations, edges)

    if config.max_transfers is not None and len(transfers) > config.max_transfers:
        raise PathNotFoundError(
            f"no route from '{start_name}' to '{end_name}' with at most {config.max_transfers} transfer(s)")

    involved = []
    for edge in edges:
        if edge.line not in involved:
            involved.append(edge.line)

    return Route(
        stations=stations,
        edges=edges,
        total_distance_m=total_distance,
        transfer_count=len(transfers),
        involved_lines=involved,
        transfers=transfers,
    )
