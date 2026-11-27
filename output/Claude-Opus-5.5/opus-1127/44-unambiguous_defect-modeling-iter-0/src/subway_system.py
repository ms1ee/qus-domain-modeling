"""High level subway route service: station validation, routing and fares."""

import math
import re
import unicodedata
from dataclasses import dataclass, field

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import SubwayDataManager
from exceptions import (FareCalculationError, InvalidQueryError, PathCalculationError,
                        StationNotFoundError)
from fare_calculator import Sum_money, calculate_estimated_time
from line_utils import canonical_line_key
from pathfinding import PathfindingConfig, ShortestPath


def _normalize(name):
    text = unicodedata.normalize("NFKC", str(name)).strip()
    return re.sub(r"\s+", " ", text).casefold()


def _compact(name):
    return re.sub(r"[\s'’`\-·.]", "", _normalize(name))


@dataclass
class RouteSegment:
    """A part of a route travelled on a single line."""
    order: int
    line: str
    stations: list
    distance: float = 0

    @property
    def stop_count(self):
        return len(self.stations) - 1


@dataclass
class Route:
    """A computed route with distance, fare and transfer information."""
    start: str
    end: str
    stations: list
    segments: list
    total_distance: float
    transfer_count: int
    transfer_stations: list
    lines: list
    fare: int
    estimated_time: float
    query: dict = field(default_factory=dict)

    @property
    def total_distance_km(self):
        return self.total_distance / 1000.0


class SubwaySystem:
    """Facade combining data management, path finding and fare calculation."""

    def __init__(self, data=None, data_path=None):
        if data is None:
            data = load_subway_data(data_path or DATA_FILE_PATH)
        self.manager = SubwayDataManager(data)
        self.rebuild()

    def rebuild(self):
        """(Re)build the graph after data updates."""
        self.graph = self.manager.build_graph()
        self.station_to_number = self.graph.station_to_number
        self._index = {}
        self._compact_index = {}
        for name in self.station_to_number:
            self._index.setdefault(_normalize(name), name)
            self._compact_index.setdefault(_compact(name), name)

    # ----- validation ----------------------------------------------
    def resolve_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        raw = str(name).strip()
        if not raw:
            return None
        if raw in self.station_to_number:
            return raw
        key = _normalize(raw)
        candidates = [key]
        for suffix in ("站", " station"):
            if key.endswith(suffix) and len(key) > len(suffix):
                candidates.append(key[:-len(suffix)].strip())
        candidates.append(key + "站")
        candidates.append(key + " station")
        for c in candidates:
            if c in self._index:
                return self._index[c]
        for c in candidates:
            comp = _compact(c)
            if comp in self._compact_index:
                return self._compact_index[comp]
        return None

    def validate_query(self, start, end):
        s = self.resolve_station(start)
        if s is None:
            raise StationNotFoundError(
                "Starting station '%s' does not exist, please check the station name" % str(start).strip())
        e = self.resolve_station(end)
        if e is None:
            raise StationNotFoundError(
                "Ending station '%s' does not exist, please check the station name" % str(end).strip())
        if s == e:
            raise InvalidQueryError("Starting station cannot be the same as the ending station")
        return s, e

    def resolve_lines(self, preferred):
        """Map preferred line names to line names present in the data.

        Returns (resolved, unknown).
        """
        known = {}
        for lines in self.graph.station_lines.values():
            for line in lines:
                known.setdefault(canonical_line_key(line), line)
        resolved, unknown = [], []
        for p in preferred or []:
            key = canonical_line_key(p)
            if key in known:
                resolved.append(known[key])
            else:
                unknown.append(p)
        return resolved, unknown

    # ----- routing --------------------------------------------------
    def find_route(self, start, end, config=None):
        config = config or PathfindingConfig()
        s, e = self.validate_query(start, end)
        src, dst = self.station_to_number[s], self.station_to_number[e]
        try:
            sp = ShortestPath(self.graph, src, config)
            path, edges = sp.path_with_edges(dst)
        except Exception as exc:  # pragma: no cover - defensive
            raise PathCalculationError("Path calculation failed: %s" % exc)
        if not path:
            msg = "No route found from '%s' to '%s'" % (s, e)
            if config.max_transfers is not None:
                msg += " within %d transfer(s)" % config.max_transfers
            raise PathCalculationError(msg)

        names = [self.graph.get_station_name(n) for n in path]
        segments = []
        for edge in edges:
            a = self.graph.get_station_name(edge.source)
            b = self.graph.get_station_name(edge.dest)
            line = edge.line
            if segments and (line is None or line == segments[-1].line):
                segments[-1].stations.append(b)
                segments[-1].distance += edge.weight
            else:
                segments.append(RouteSegment(len(segments) + 1, line if line else "Unknown line",
                                             [a, b], edge.weight))
        total = sum(edge.weight for edge in edges)
        transfer_stations = [seg.stations[-1] for seg in segments[:-1]]
        lines = []
        for seg in segments:
            if seg.line not in lines:
                lines.append(seg.line)
        transfer_count = len(segments) - 1 if segments else 0

        try:
            fare = Sum_money(total)
        except (TypeError, ValueError) as exc:
            raise FareCalculationError("Fare calculation failed: %s" % exc)
        try:
            est = calculate_estimated_time(total, transfer_count)
        except (TypeError, ValueError):
            est = 0.0
        if isinstance(total, float) and total.is_integer():
            total = int(total)

        query = {
            "start": s,
            "end": e,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines or []),
        }
        return Route(s, e, names, segments, total, transfer_count, transfer_stations, lines,
                     fare, est, query)
