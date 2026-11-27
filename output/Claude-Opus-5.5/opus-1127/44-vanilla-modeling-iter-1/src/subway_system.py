"""High-level service combining data, path finding and fare calculation."""

import re

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data
from fare_calculator import FareCalculationError, Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base class for user-facing query errors."""


class InputFormatError(QueryError):
    pass


class StationNotFoundError(QueryError):
    pass


class SameStationError(QueryError):
    pass


class RouteNotFoundError(QueryError):
    pass


class PathCalculationError(QueryError):
    pass


class FareError(QueryError):
    pass


def _simplify(name):
    s = name.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(\s*station|站)$", "", s)
    return re.sub(r"[\s'\-]", "", s)


class SubwaySystem:
    """Facade for route queries on the Beijing Subway network."""

    def __init__(self, data=None, data_path=DATA_FILE_PATH):
        if data is None:
            data = load_subway_data(data_path)
        self.reload(data)

    def reload(self, data):
        self.data = data
        self.graph, self.station_to_number, self.number_to_station = build_graph(data)
        self._lookup = {}
        for name in self.station_to_number:
            self._lookup.setdefault(_simplify(name), name)

    # ----- validation -----
    def resolve_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        cleaned = re.sub(r"\s+", " ", name.strip())
        if cleaned in self.station_to_number:
            return cleaned
        return self._lookup.get(_simplify(cleaned))

    def parse_query(self, text):
        """Validate 'Start; End' input and return official (start, end)."""
        if text is None:
            raise InputFormatError(INPUT_FORMAT_MESSAGE)
        normalized = text.replace("；", ";")
        parts = normalized.split(";")
        if len(parts) != 2:
            raise InputFormatError(INPUT_FORMAT_MESSAGE)
        raw_start, raw_end = parts[0].strip(), parts[1].strip()
        if not raw_start or not raw_end:
            raise InputFormatError(INPUT_FORMAT_MESSAGE)
        start = self.resolve_station(raw_start)
        if start is None:
            raise StationNotFoundError(
                f"Starting station '{raw_start}' does not exist, please check the station name")
        end = self.resolve_station(raw_end)
        if end is None:
            raise StationNotFoundError(
                f"Ending station '{raw_end}' does not exist, please check the station name")
        if start == end:
            raise SameStationError("Starting station cannot be the same as the ending station")
        return start, end

    # ----- query -----
    def find_route(self, start, end, config=None):
        """Compute a route and return a dictionary with all route details."""
        config = config or PathfindingConfig()
        s_name, e_name = self.resolve_station(start), self.resolve_station(end)
        if s_name is None:
            raise StationNotFoundError(
                f"Starting station '{start}' does not exist, please check the station name")
        if e_name is None:
            raise StationNotFoundError(
                f"Ending station '{end}' does not exist, please check the station name")
        if s_name == e_name:
            raise SameStationError("Starting station cannot be the same as the ending station")
        try:
            sp = ShortestPath(self.graph, self.station_to_number[s_name], config)
            nodes, edges = sp.path_with_edges(self.station_to_number[e_name])
        except Exception as exc:  # noqa: BLE001
            raise PathCalculationError(f"Path calculation failed: {exc}") from exc
        if not nodes:
            extra = ""
            if config.max_transfers is not None:
                extra = f" within {config.max_transfers} transfer(s)"
            raise RouteNotFoundError(f"No route found from '{s_name}' to '{e_name}'{extra}")

        path = [self.number_to_station[n] for n in nodes]
        distance = sum(e.distance for e in edges)

        segments = []
        for i, edge in enumerate(edges):
            if segments and segments[-1]["line"] == edge.line:
                segments[-1]["stations"].append(path[i + 1])
                segments[-1]["distance"] += edge.distance
            else:
                segments.append({"line": edge.line, "stations": [path[i], path[i + 1]],
                                 "distance": edge.distance})
        transfer_stations = [seg["stations"][0] for seg in segments[1:]]
        lines = []
        for seg in segments:
            if seg["line"] not in lines:
                lines.append(seg["line"])
        transfer_count = len(transfer_stations)

        try:
            fare = Sum_money(distance)
        except (FareCalculationError, ValueError) as exc:
            raise FareError(f"Fare calculation failed: {exc}") from exc

        return {
            "start": s_name,
            "end": e_name,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
            "path": path,
            "segments": segments,
            "distance_m": distance,
            "distance_km": round(distance / 1000.0, 3),
            "transfer_count": transfer_count,
            "transfer_stations": transfer_stations,
            "lines": lines,
            "fare": fare,
            "estimated_time": round(calculate_estimated_time(distance, transfer_count), 1),
        }
