"""Route, RouteSummary, Query and route computation."""
from pathfinding import ShortestPath, PathfindingConfig
from fare_calculator import Sum_money, calculate_estimated_time

MODES = ("shortest_distance", "least_transfer", "comprehensive")


class Query:
    def __init__(self, start_station, end_station, mode="shortest_distance",
                 max_transfers=None, line_preference=None):
        self.start_station = start_station
        self.end_station = end_station
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference


class Route:
    def __init__(self, stations, total_distance, transfer_count, lines_involved,
                 segments=None, transfer_stations=None):
        self.stations = stations
        self.total_distance = total_distance
        self.transfer_count = transfer_count
        self.lines_involved = lines_involved
        self.segments = segments or []  # (line, [stations])
        self.transfer_stations = transfer_stations or []


class RouteSummary:
    def __init__(self, route):
        self.total_distance = route.total_distance
        self.fare = Sum_money(route.total_distance)
        self.transfer_count = route.transfer_count
        self.estimated_time = calculate_estimated_time(route.total_distance, route.transfer_count)


def find_route(graph, query):
    s = graph.station_to_number[query.start_station]
    t = graph.station_to_number[query.end_station]
    cfg = PathfindingConfig(query.mode, query.max_transfers,
                            [query.line_preference] if query.line_preference else [])
    sp = ShortestPath(graph, s, cfg)
    nodes, edges = sp.path_with_edges(t)
    if not nodes:
        return None
    names = [graph.number_to_station[n] for n in nodes]
    segments, transfers, lines = [], [], []
    for i, e in enumerate(edges):
        if not segments or segments[-1][0] != e.line:
            if segments:
                transfers.append(names[i])
            segments.append((e.line, [names[i]]))
        segments[-1][1].append(names[i + 1])
        if e.line not in lines:
            lines.append(e.line)
    return Route(names, sum(e.distance for e in edges), sp.get_transfer_count(t),
                 lines, segments, transfers)
