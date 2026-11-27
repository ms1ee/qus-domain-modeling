"""Route computation combining path finding and fare calculation."""

from dataclasses import dataclass, field

from fare_calculator import FareCalculationError, Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteNotFoundError(Exception):
    """No route satisfies the query."""


class PathCalculationError(Exception):
    """Unexpected failure in path calculation."""


@dataclass
class RouteResult:
    start: str
    end: str
    mode: str
    stations: list
    distance: float
    lines: list
    segments: list
    transfer_stations: list
    transfer_count: int
    fare: int
    estimated_time: float
    max_transfers: object = None
    line_preference: list = field(default_factory=list)


def find_route(network, start, end, config=None):
    """Compute the route between two official station names."""
    config = config or PathfindingConfig()
    try:
        s = network.station_to_number[start]
        t = network.station_to_number[end]
        sp = ShortestPath(network.graph, s, config)
        numbers, edges = sp.path_with_edges(t)
    except (ValueError, TypeError) as exc:
        raise PathCalculationError(str(exc)) from exc
    except KeyError as exc:
        raise PathCalculationError(f"Unknown station {exc}") from exc
    if not numbers:
        if config.max_transfers is not None:
            raise RouteNotFoundError(
                f"No route found from '{start}' to '{end}' within "
                f"{config.max_transfers} transfer(s)")
        raise RouteNotFoundError(f"No route found from '{start}' to '{end}'")

    names = [network.number_to_station[n] for n in numbers]
    distance = sum(e.weight for e in edges)

    segments = []
    for i, edge in enumerate(edges):
        if segments and segments[-1]["line"] == edge.line:
            seg = segments[-1]
            seg["stations"].append(names[i + 1])
            seg["distance"] += edge.weight
            seg["to"] = names[i + 1]
        else:
            segments.append({"line": edge.line, "from": names[i], "to": names[i + 1],
                             "stations": [names[i], names[i + 1]], "distance": edge.weight})
    transfers = []
    for a, b in zip(segments, segments[1:]):
        transfers.append({"station": a["to"], "from_line": a["line"], "to_line": b["line"]})
    lines = list(dict.fromkeys(seg["line"] for seg in segments))

    try:
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, len(transfers))
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(str(exc)) from exc

    return RouteResult(start=start, end=end, mode=config.mode, stations=names,
                       distance=distance, lines=lines, segments=segments,
                       transfer_stations=transfers, transfer_count=len(transfers),
                       fare=fare, estimated_time=est,
                       max_transfers=config.max_transfers,
                       line_preference=list(config.preferred_lines))
