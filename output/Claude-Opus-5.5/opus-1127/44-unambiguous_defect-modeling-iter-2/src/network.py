"""Subway network model: builds the graph and answers route queries."""

import math
import re

from data_loader import DATA_FILE_PATH, load_subway_data
from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Graph, Route, Station
from pathfinding import PathfindingConfig, ShortestPath

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class SubwayError(Exception):
    """Base class of all user facing errors."""


class InputFormatError(SubwayError):
    pass


class StationNotFoundError(SubwayError):
    pass


class SameStationError(SubwayError):
    pass


class RouteNotFoundError(SubwayError):
    pass


class PathCalculationError(SubwayError):
    pass


class FareCalculationError(SubwayError):
    pass


_SEPARATOR_RE = re.compile(r"\s*(?:;|；|,|，|->|→)\s*")


def parse_query_input(text):
    """Parse 'Start; End' style input. Returns (start, end)."""
    if text is None:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    parts = _SEPARATOR_RE.split(text.strip())
    if len(parts) != 2:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return start, end


def normalize_name(name):
    return re.sub(r"\s+", " ", str(name)).strip().casefold()


def build_graph(data):
    """Build a Graph from the raw subway data dict."""
    graph = Graph()
    number = 0
    for st in data.get("stations", []):
        name = st.get("name") if isinstance(st, dict) else None
        if not name or name in graph.station_to_number:
            continue
        graph.add_station(name, number, st.get("lines", []) or [])
        number += 1
    for conn in data.get("connections", []):
        if not isinstance(conn, dict):
            continue
        src, dst = conn.get("source"), conn.get("dest")
        dist = conn.get("distance")
        if not src or not dst or src == dst:
            continue
        if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
            continue
        for name in (src, dst):
            if name not in graph.station_to_number:
                graph.add_station(name, number, [conn.get("line")] if conn.get("line") else [])
                number += 1
        graph.add_edge(Edge(graph.station_to_number[src], graph.station_to_number[dst],
                            dist, conn.get("line")))
    return graph


class SubwayNetwork:
    """The Beijing Subway network with routing and fare functionality."""

    def __init__(self, data=None, data_source=DATA_FILE_PATH):
        if data is None:
            data = load_subway_data(data_source)
        self.data_source = data_source
        self.data = data
        self.graph = build_graph(data)
        self.station_to_number = self.graph.station_to_number
        self.number_to_station = self.graph.number_to_station
        self._normalized = {}
        for name in self.station_to_number:
            self._normalized.setdefault(normalize_name(name), name)

    # ------------------------------------------------------------------
    def stations(self):
        return [Station(n, num, list(self.graph.station_lines.get(n, [])))
                for n, num in self.station_to_number.items()]

    def resolve_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        name = str(name).strip()
        if name in self.station_to_number:
            return name
        key = normalize_name(name)
        if key in self._normalized:
            return self._normalized[key]
        for suffix in (" station", "站"):
            if key.endswith(suffix) and key[: -len(suffix)].strip() in self._normalized:
                return self._normalized[key[: -len(suffix)].strip()]
        return None

    def validate_stations(self, start, end):
        s = self.resolve_station(start)
        if s is None:
            raise StationNotFoundError(
                "Starting station '%s' does not exist, please check the station name" % start)
        e = self.resolve_station(end)
        if e is None:
            raise StationNotFoundError(
                "Ending station '%s' does not exist, please check the station name" % end)
        if s == e:
            raise SameStationError("Starting station cannot be the same as the ending station")
        return s, e

    # ------------------------------------------------------------------
    def plan_route(self, start, end, config=None):
        """Compute a Route between two station names."""
        config = config if config is not None else PathfindingConfig()
        s_name, e_name = self.validate_stations(start, end)
        s_num = self.station_to_number[s_name]
        e_num = self.station_to_number[e_name]
        try:
            sp = ShortestPath(self.graph, s_num, config)
            nodes, edges = sp.path_with_edges(e_num)
        except SubwayError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise PathCalculationError("Path calculation failed: %s" % exc) from exc
        if not nodes or len(nodes) < 2:
            msg = "No route found from '%s' to '%s'" % (s_name, e_name)
            if config.max_transfers is not None:
                msg += " within %d transfer(s)" % config.max_transfers
            raise RouteNotFoundError(msg)

        names = [self.graph.get_station_name(n) for n in nodes]
        total = sum(e.weight for e in edges)
        if isinstance(total, float) and total.is_integer():
            total = int(total)
        transfer_stations = []
        segments = []
        for i, e in enumerate(edges):
            if i > 0 and e.line != edges[i - 1].line:
                transfer_stations.append(names[i])
            if not segments or segments[-1]["line"] != e.line:
                segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                                 "stations": [names[i], names[i + 1]], "stops": 1,
                                 "distance": e.weight})
            else:
                seg = segments[-1]
                seg["to"] = names[i + 1]
                seg["stations"].append(names[i + 1])
                seg["stops"] += 1
                seg["distance"] += e.weight
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        transfer_count = len(transfer_stations)
        try:
            fare = Sum_money(total)
        except (TypeError, ValueError) as exc:
            raise FareCalculationError("Fare calculation failed: %s" % exc) from exc
        try:
            est = calculate_estimated_time(total, transfer_count)
        except (TypeError, ValueError):
            est = math.nan
        return Route(start=s_name, end=e_name, mode=config.mode, stations=names,
                     edge_lines=[e.line for e in edges], edge_distances=[e.weight for e in edges],
                     total_distance=total, transfer_count=transfer_count,
                     transfer_stations=transfer_stations, lines=lines, segments=segments,
                     fare=fare, estimated_time=est, max_transfers=config.max_transfers,
                     line_preference=list(config.preferred_lines or []))
