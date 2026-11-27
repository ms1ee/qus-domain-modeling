"""
Route planning: combines path finding, fare calculation and route summary.
"""

from fare_calculator import MINUTES_PER_TRANSFER, Sum_money, calculate_estimated_time
from models import Route, Segment, Transfer
from pathfinding import PathCalculationError, PathfindingConfig, ShortestPath


class RouteNotFoundError(PathCalculationError):
    """Raised when no route exists between two stations under the config."""


class RoutePlanner:
    def __init__(self, network):
        self.network = network

    def plan(self, start, end, config=None):
        """Compute a :class:`models.Route` between two official station names."""
        config = config or PathfindingConfig()
        net = self.network
        if start not in net.station_to_number:
            raise LookupError(f"Starting station '{start}' does not exist")
        if end not in net.station_to_number:
            raise LookupError(f"Ending station '{end}' does not exist")
        if start == end:
            raise ValueError("Starting station cannot be the same as the ending station")

        s = net.station_to_number[start]
        t = net.station_to_number[end]
        sp = ShortestPath(net.graph, s, config)
        nodes, edges = sp.path_with_edges(t)
        if not nodes:
            if config.max_transfers is not None:
                raise RouteNotFoundError(
                    f"No route from '{start}' to '{end}' within {config.max_transfers} transfer(s)")
            raise RouteNotFoundError(f"No route from '{start}' to '{end}'")

        names = [net.number_to_station[n] for n in nodes]
        segments = []
        for i, edge in enumerate(edges):
            if not segments or segments[-1].line != edge.line:
                segments.append(Segment(line=edge.line, stations=[names[i]], distance=0))
            segments[-1].stations.append(names[i + 1])
            segments[-1].distance += edge.weight

        transfers = []
        for k in range(1, len(segments)):
            transfers.append(Transfer(station=segments[k].stations[0],
                                      from_line=segments[k - 1].line,
                                      to_line=segments[k].line,
                                      transfer_time=MINUTES_PER_TRANSFER,
                                      transfer_distance=0))

        total = sum(e.weight for e in edges)
        transfer_count = len(transfers)
        involved = []
        for seg in segments:
            if seg.line is not None and seg.line not in involved:
                involved.append(seg.line)

        try:
            fare = Sum_money(total)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Fare calculation failed: {exc}") from exc

        return Route(start=start, end=end, station_sequence=names, total_distance=total,
                     transfer_count=transfer_count, involved_lines=involved,
                     estimated_time=calculate_estimated_time(total, transfer_count),
                     fare=fare, transfers=transfers, segments=segments, mode=config.mode)
