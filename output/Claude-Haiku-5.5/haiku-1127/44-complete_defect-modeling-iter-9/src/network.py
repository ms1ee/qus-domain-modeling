"""Subway network model: stations, lines, connections and the weighted graph."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Set

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph


def _normalize_name(name: str) -> str:
    """Normalize a station or line name for case/whitespace-insensitive matching."""
    return " ".join(name.split()).casefold()


def _validate_distance(distance: Any) -> float:
    """Return the distance as int (when integral) or float; it must be positive."""
    try:
        value = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid distance: {distance!r}") from exc
    if value <= 0:
        raise ValueError("distance must be positive")
    return int(value) if value.is_integer() else value


class SubwayNetwork:
    """The Beijing Subway network with station numbering and the weighted graph.

    Station numbers are assigned here (the index in ``number_to_station``) and
    passed to the Graph, which does not assign numbers itself.
    """

    def __init__(self, name: str = "Beijing Subway", data_source: str = DATA_FILE_PATH) -> None:
        self.name = name
        self.data_source = data_source
        self.last_updated = datetime.now()
        self.graph = Graph()
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: List[str] = []
        # Stations that appear only in connections (not in the station list).
        self.unlisted_stations: Set[str] = set()
        self._station_lines: Dict[str, List[str]] = {}
        self._connections: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_data(cls, data: Dict[str, Any], data_source: str = DATA_FILE_PATH) -> "SubwayNetwork":
        """Build a network from the dict representation of subway_data.json."""
        if not isinstance(data, dict):
            raise ValueError("subway data must be a dict")
        network = cls(data_source=data_source)
        for entry in data.get("stations", []):
            name = str(entry["name"]).strip()
            lines = [str(line).strip() for line in entry.get("lines", [])]
            network._ensure_station(name, lines)
        for entry in data.get("connections", []):
            conn = network._make_connection(entry["source"], entry["dest"], entry["distance"], entry["line"])
            network._connections.append(conn)
            for endpoint in (conn["source"], conn["dest"]):
                if endpoint not in network.station_to_number:
                    network._ensure_station(endpoint, [conn["line"]])
                    network.unlisted_stations.add(endpoint)
        network.rebuild_graph()
        return network

    @classmethod
    def from_file(cls, path: str = DATA_FILE_PATH) -> "SubwayNetwork":
        """Load the network from a subway_data.json file."""
        data = load_subway_data(path)
        return cls.from_data(data, data_source=path)

    def _make_connection(self, source: Any, dest: Any, distance: Any, line: Any) -> Dict[str, Any]:
        src = str(source).strip()
        dst = str(dest).strip()
        line_name = str(line).strip()
        try:
            value = float(distance)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid distance for connection {src}-{dst}: {distance!r}") from exc
        dist: Any = int(value) if value.is_integer() else value
        return {"source": src, "dest": dst, "distance": dist, "line": line_name}

    def _ensure_station(self, name: str, lines: Iterable[str] = ()) -> int:
        """Register a station (if new) and add the given lines; return its number."""
        if name not in self.station_to_number:
            number = len(self.number_to_station)
            self.number_to_station.append(name)
            self.station_to_number[name] = number
            self._station_lines[name] = []
        for line in lines:
            if line and line not in self._station_lines[name]:
                self._station_lines[name].append(line)
        return self.station_to_number[name]

    def rebuild_graph(self) -> None:
        """Rebuild the weighted undirected graph from stations and connections."""
        graph = Graph()
        for number, name in enumerate(self.number_to_station):
            graph.add_vertex(number)
            graph.set_station_lines(name, self._station_lines.get(name, []))
        for conn in self._connections:
            graph.add_edge(
                Edge(
                    self.station_to_number[conn["source"]],
                    self.station_to_number[conn["dest"]],
                    conn["distance"],
                    conn["line"],
                )
            )
        self.graph = graph
        self.last_updated = datetime.now()

    # ------------------------------------------------------------------ queries
    def station_names(self) -> List[str]:
        return sorted(self.number_to_station)

    def line_names(self) -> List[str]:
        names: Set[str] = set()
        for lines in self._station_lines.values():
            names.update(lines)
        for conn in self._connections:
            names.add(conn["line"])
        return sorted(names)

    def stations_on_line(self, line: str) -> List[str]:
        line_key = line.strip()
        return sorted(name for name, lines in self._station_lines.items() if line_key in lines)

    def lines_of(self, station: str) -> List[str]:
        canonical = self.standardize_station(station)
        if canonical is None:
            return []
        return list(self._station_lines[canonical])

    def is_transfer_station(self, station: str) -> bool:
        return len(self.lines_of(station)) > 1

    def has_station(self, name: str) -> bool:
        return self.standardize_station(name) is not None

    def standardize_station(self, name: Any) -> Optional[str]:
        """Return the official station name matching ``name``, or None if unknown."""
        if not isinstance(name, str):
            return None
        stripped = name.strip()
        if stripped in self.station_to_number:
            return stripped
        key = _normalize_name(stripped)
        for candidate in self.number_to_station:
            if _normalize_name(candidate) == key:
                return candidate
        return None

    def number_of(self, name: str) -> int:
        canonical = self.standardize_station(name)
        if canonical is None:
            raise KeyError(f"unknown station: {name}")
        return self.station_to_number[canonical]

    def connections(self) -> List[Dict[str, Any]]:
        return [dict(conn) for conn in self._connections]

    def _require_station(self, name: str) -> str:
        canonical = self.standardize_station(name)
        if canonical is None:
            raise KeyError(f"unknown station: {name}")
        return canonical

    # ------------------------------------------------------------------ updates
    def add_line(self, line_name: str, station_names: List[str], distances: List[Any]) -> None:
        """Add a new line given its ordered station sequence and consecutive distances."""
        line = line_name.strip()
        if not line:
            raise ValueError("line name must not be empty")
        if line in self.line_names():
            raise ValueError(f"line '{line}' already exists")
        stations = [str(s).strip() for s in station_names]
        if len(stations) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("number of distances must be one less than the number of stations")
        if len({_normalize_name(s) for s in stations}) != len(stations):
            raise ValueError("a line cannot contain duplicate stations")

        canonical = [self.standardize_station(s) or s for s in stations]
        new_connections = []
        for index, distance in enumerate(distances):
            value = _validate_distance(distance)
            new_connections.append(
                {"source": canonical[index], "dest": canonical[index + 1], "distance": value, "line": line}
            )
        for station in canonical:
            self._ensure_station(station, [line])
        self._connections.extend(new_connections)
        self.rebuild_graph()

    def update_station(self, old_name: str, new_name: Optional[str] = None, lines: Optional[List[str]] = None) -> str:
        """Rename a station and/or replace its list of lines. Returns the resulting name."""
        canonical = self._require_station(old_name)
        target = canonical
        if new_name is not None:
            new = new_name.strip()
            if not new:
                raise ValueError("new station name must not be empty")
            if new != canonical and self.standardize_station(new) is not None:
                raise ValueError(f"station '{new}' already exists")
            if new != canonical:
                self._rename_station(canonical, new)
                target = new
        if lines is not None:
            cleaned: List[str] = []
            for line in lines:
                value = str(line).strip()
                if value and value not in cleaned:
                    cleaned.append(value)
            self._station_lines[target] = cleaned
        self.rebuild_graph()
        return target

    def _rename_station(self, old: str, new: str) -> None:
        number = self.station_to_number.pop(old)
        self.station_to_number[new] = number
        self.number_to_station[number] = new
        self._station_lines[new] = self._station_lines.pop(old)
        for conn in self._connections:
            if conn["source"] == old:
                conn["source"] = new
            if conn["dest"] == old:
                conn["dest"] = new
        if old in self.unlisted_stations:
            self.unlisted_stations.discard(old)
            self.unlisted_stations.add(new)

    def update_distance(self, station_a: str, station_b: str, distance: Any, line: Optional[str] = None) -> int:
        """Update the distance between two adjacent stations. Returns the number of connections changed."""
        a = self._require_station(station_a)
        b = self._require_station(station_b)
        value = _validate_distance(distance)
        line_key = line.strip() if line else None
        changed = 0
        for conn in self._connections:
            pair_matches = {conn["source"], conn["dest"]} == {a, b}
            if pair_matches and (line_key is None or conn["line"] == line_key):
                conn["distance"] = value
                changed += 1
        if changed == 0:
            raise ValueError(f"no connection between '{a}' and '{b}'")
        self.rebuild_graph()
        return changed

    # ------------------------------------------------------------------ persistence
    def to_data(self) -> Dict[str, Any]:
        """Return the dict representation compatible with subway_data.json."""
        stations = [
            {"name": name, "lines": list(self._station_lines[name])} for name in self.number_to_station
        ]
        return {"stations": stations, "connections": [dict(conn) for conn in self._connections]}

    def save(self, path: str = DATA_FILE_PATH) -> None:
        save_subway_data(self.to_data(), path)
