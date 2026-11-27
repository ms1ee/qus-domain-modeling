"""
Route planning: combines the network, Dijkstra search and fare calculation.
"""

from fare_calculator import Sum_money, calculate_estimated_time, FareCalculationError
from pathfinding import PathfindingConfig, ShortestPath


class StationNotFoundError(ValueError):
    """Raised when a station name does not exist."""


class RouteNotFoundError(RuntimeError):
    """Raised when no path exists between two stations."""


class Route:
    """Computed route with summary information."""

    def __init__(self, start, end, stations, segments, total_distance_m, fare,
                 transfer_count, estimated_time, mode="shortest_distance",
                 max_transfers=None, preferred_lines=None):
        self.start = start
        self.end = end
        self.station_sequence = stations
        self.segments = segments  # list of {"line": str, "stations": [str]}
        self.total_distance_m = total_distance_m
        self.total_distance_km = round(total_distance_m / 1000.0, 2)
        self.fare = fare
        self.transfer_count = transfer_count
        self.estimated_time = estimated_time
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])

    @property
    def transfer_stations(self):
        return [seg["stations"][0] for seg in self.segments[1:]]

    @property
    def involved_lines(self):
        out = []
        for seg in self.segments:
            if seg["line"] not in out:
                out.append(seg["line"])
        return out

    def to_dict(self):
        return {
            "query": {
                "start": self.start,
                "end": self.end,
                "mode": self.mode,
                "max_transfers": self.max_transfers,
                "line_preference": self.preferred_lines,
            },
            "path": list(self.station_sequence),
            "station_count": len(self.station_sequence),
            "segments": [{"line": s["line"], "stations": list(s["stations"])} for s in self.segments],
            "distance": {"meters": self.total_distance_m, "kilometers": self.total_distance_km},
            "fare": self.fare,
            "estimated_time": self.estimated_time,
            "transfer_count": self.transfer_count,
            "transfer_stations": self.transfer_stations,
            "lines": self.involved_lines,
        }


def compute_route(network, start, end, config=None):
    """Compute a route between two station names. Raises on errors."""
    config = config or PathfindingConfig()
    s = network.find_station(start)
    if s is None:
        raise StationNotFoundError(f"Starting station '{start}' does not exist, please check the station name")
    t = network.find_station(end)
    if t is None:
        raise StationNotFoundError(f"Ending station '{end}' does not exist, please check the station name")
    if s == t:
        raise ValueError("Starting station cannot be the same as the ending station")

    try:
        sp = ShortestPath(network.graph_obj, network.station_to_number[s], config)
        nodes, edges = sp.path_with_edges(network.station_to_number[t])
    except Exception as exc:  # defensive: path calculation exception handling
        raise RouteNotFoundError(f"Path calculation failed: {exc}") from exc
    if not nodes:
        msg = f"No route found from '{s}' to '{t}'"
        if config.max_transfers is not None:
            msg += f" within {config.max_transfers} transfer(s)"
        raise RouteNotFoundError(msg)

    names = [network.number_to_station[n] for n in nodes]
    segments = []
    for i, edge in enumerate(edges):
        if not segments or segments[-1]["line"] != edge.line:
            segments.append({"line": edge.line, "stations": [names[i]]})
        segments[-1]["stations"].append(names[i + 1])
    distance = sum(e.weight for e in edges)
    transfers = max(0, len(segments) - 1)
    try:
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, transfers)
    except FareCalculationError:
        raise
    except Exception as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    return Route(s, t, names, segments, distance, fare, transfers, est,
                 mode=config.mode, max_transfers=config.max_transfers,
                 preferred_lines=config.preferred_lines)
