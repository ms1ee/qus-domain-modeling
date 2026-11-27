"""
Route planning service: combines path calculation and fare calculation
into a Route object.
"""

try:
    from pathfinding import PathfindingConfig, ShortestPath
    from fare_calculator import Sum_money, calculate_estimated_time
    from models import Route, Transfer
except ImportError:  # pragma: no cover
    from .pathfinding import PathfindingConfig, ShortestPath
    from .fare_calculator import Sum_money, calculate_estimated_time
    from .models import Route, Transfer


class StationNotFoundError(Exception):
    pass


class PathNotFoundError(Exception):
    pass


class PathCalculationError(Exception):
    pass


class FareError(Exception):
    pass


def build_segments(network, nodes, edges):
    """Group consecutive edges on the same line into segments."""
    segments = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = network.number_to_station[e.dest]
            segments[-1]["stops"] += 1
            segments[-1]["distance"] += e.weight
            segments[-1]["stations"].append(network.number_to_station[e.dest])
        else:
            segments.append({
                "line": e.line,
                "from": network.number_to_station[e.source],
                "to": network.number_to_station[e.dest],
                "stops": 1,
                "distance": e.weight,
                "stations": [network.number_to_station[e.source], network.number_to_station[e.dest]],
            })
    return segments


def plan_route(network, start, end, config=None):
    """Compute the route between two canonical station names."""
    config = config or PathfindingConfig()
    if start not in network.station_to_number:
        raise StationNotFoundError(f"Starting station '{start}' does not exist, please check the station name")
    if end not in network.station_to_number:
        raise StationNotFoundError(f"Ending station '{end}' does not exist, please check the station name")
    s = network.station_to_number[start]
    t = network.station_to_number[end]
    try:
        sp = ShortestPath(network.graph_obj, s, config)
        nodes, edges = sp.path_with_edges(t)
    except Exception as exc:  # defensive
        raise PathCalculationError(f"Path calculation failed: {exc}") from exc
    if not nodes:
        extra = ""
        if config.max_transfers is not None:
            extra = f" within {config.max_transfers} transfer(s)"
        raise PathNotFoundError(f"No path found from '{start}' to '{end}'{extra}")

    distance = sum(e.weight for e in edges)
    transfers = []
    for prev, cur in zip(edges, edges[1:]):
        if cur.line != prev.line:
            transfers.append(Transfer(network.number_to_station[cur.source], prev.line, cur.line))
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    try:
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, len(transfers))
    except (ValueError, TypeError) as exc:
        raise FareError(f"Fare calculation failed: {exc}") from exc

    return Route(
        start=start,
        end=end,
        mode=config.mode,
        station_sequence=[network.number_to_station[n] for n in nodes],
        total_distance_meters=distance,
        transfer_count=len(transfers),
        estimated_time_minutes=est,
        involved_lines=lines,
        transfers=transfers,
        segments=build_segments(network, nodes, edges),
        fare=fare,
        max_transfers=config.max_transfers,
        line_preference=list(config.preferred_lines),
    )
