"""Subway network model: station registry, name standardization and graph building."""

from typing import Dict, List, Optional

from errors import DataError, StationNotFoundError
from models import Edge, Graph


def _clean_text(value):
    """Return a whitespace-normalized string, or '' for non-string values."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _match_key(text):
    """Build a lookup key used for station name standardization.

    The key ignores case, whitespace and a trailing Chinese "站" suffix, so
    "dongzhimen", "Dongzhimen " and "Dongzhimen站" all map to the same station.
    """
    cleaned = _clean_text(text).casefold()
    if cleaned.endswith("站"):
        cleaned = cleaned[:-1]
    return cleaned.replace(" ", "")


def _to_distance(value):
    """Convert a distance value to a non-negative integer number of meters."""
    if isinstance(value, bool):
        raise DataError(f"invalid distance value: {value!r}")
    try:
        meters = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise DataError(f"invalid distance value: {value!r}") from exc
    if meters < 0:
        raise DataError(f"distance must not be negative: {value!r}")
    return meters


class SubwayNetwork:
    """In-memory model of the Beijing Subway network.

    Holds stations (name -> lines), connections (raw records with names) and
    the derived weighted undirected Graph keyed by station numbers. Station
    numbers are assigned in sorted-name order whenever the graph is rebuilt.
    """

    def __init__(self, data):
        self._stations: Dict[str, List[str]] = {}
        self._connections: List[dict] = []
        self._name_index: Dict[str, str] = {}
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self.graph = Graph()
        self._load(data)
        self.rebuild()

    # ----- loading and building ------------------------------------------
    def _load(self, data):
        """Populate internal records from the raw dataset dictionary."""
        if not isinstance(data, dict):
            raise DataError("subway data must be a dictionary")
        for record in data.get("stations", []):
            name = _clean_text(record.get("name"))
            if not name:
                raise DataError("station record without a name")
            self._stations.setdefault(name, [])
            for line in record.get("lines", []):
                self._add_station_line(name, _clean_text(line))
        for conn in data.get("connections", []):
            source = _clean_text(conn.get("source"))
            dest = _clean_text(conn.get("dest"))
            line = _clean_text(conn.get("line"))
            if not source or not dest or not line:
                raise DataError("connection record missing source, dest or line")
            if source == dest:
                raise DataError(f"connection from '{source}' to itself is not allowed")
            distance = _to_distance(conn.get("distance"))
            self._connections.append(
                {"source": source, "dest": dest, "distance": distance, "line": line}
            )
            self._ensure_station(source, [line])
            self._ensure_station(dest, [line])

    def _ensure_station(self, name, default_lines):
        """Create a station with default lines if it does not exist yet."""
        if name not in self._stations:
            self._stations[name] = []
            for line in default_lines:
                self._add_station_line(name, line)

    def _add_station_line(self, name, line):
        """Attach a line to a station (no duplicates)."""
        lines = self._stations.setdefault(name, [])
        if line and line not in lines:
            lines.append(line)

    def rebuild(self):
        """Rebuild station numbers, name index and the weighted graph."""
        names = sorted(self._stations)
        self.station_to_number = {name: idx for idx, name in enumerate(names)}
        self.number_to_station = {idx: name for name, idx in self.station_to_number.items()}
        self._name_index = {}
        self.graph = Graph()
        for name in names:
            number = self.station_to_number[name]
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, self._stations[name])
            self._name_index.setdefault(_match_key(name), name)
        for conn in self._connections:
            self.graph.add_edge(
                Edge(
                    self.station_to_number[conn["source"]],
                    self.station_to_number[conn["dest"]],
                    conn["distance"],
                    conn["line"],
                )
            )

    # ----- queries --------------------------------------------------------
    def stations(self):
        """Return all station names in sorted order."""
        return sorted(self._stations)

    def has_station(self, name):
        """Return True if the exact station name exists."""
        return name in self._stations

    def standardize_name(self, raw):
        """Map user-entered text to the official station name.

        Returns:
            str or None: The canonical name, or None if it is unknown.
        """
        if not isinstance(raw, str):
            return None
        key = _match_key(raw)
        if not key:
            return None
        return self._name_index.get(key)

    def require_station(self, raw):
        """Return the canonical station name or raise StationNotFoundError."""
        name = self.standardize_name(raw)
        if name is None:
            raise StationNotFoundError(f"Station '{raw}' does not exist, please check the station name")
        return name

    def station_number(self, name):
        """Return the graph number of an exact station name."""
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{name}' does not exist")
        return self.station_to_number[name]

    def station_name(self, number):
        """Return the station name for a graph number."""
        if number not in self.number_to_station:
            raise StationNotFoundError(f"No station with number {number}")
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return a copy of the list of lines serving a station."""
        return list(self._stations.get(name, []))

    def line_names(self):
        """Return all known line names, sorted."""
        names = set()
        for lines in self._stations.values():
            names.update(lines)
        for conn in self._connections:
            names.add(conn["line"])
        return sorted(names)

    def stations_on_line(self, line):
        """Return sorted names of stations served by ``line``."""
        return sorted(name for name, lines in self._stations.items() if line in lines)

    def connections(self):
        """Return copies of all connection records."""
        return [dict(conn) for conn in self._connections]

    def to_data(self):
        """Export the network in the same structure as the JSON data file."""
        return {
            "stations": [
                {"name": name, "lines": list(self._stations[name])} for name in self.stations()
            ],
            "connections": self.connections(),
        }

    # ----- data updates ---------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line described by an ordered station list and segment distances.

        Args:
            line_name: Name of the new line (must not exist yet).
            stations: Ordered station names (at least two, unique).
            distances: Distances in meters between consecutive stations.

        Returns:
            str: The cleaned line name.

        Raises:
            DataError: If the input is inconsistent.
        """
        line = _clean_text(line_name)
        if not line:
            raise DataError("line name must not be empty")
        if line in self.line_names():
            raise DataError(f"line '{line}' already exists")
        names = [_clean_text(station) for station in stations]
        if len(names) < 2:
            raise DataError("a new line needs at least two stations")
        if any(not name for name in names):
            raise DataError("station names must not be empty")
        if len(set(names)) != len(names):
            raise DataError("a new line must not repeat stations")
        if len(distances) != len(names) - 1:
            raise DataError("one distance is required between each pair of consecutive stations")
        meters = [_to_distance(value) for value in distances]
        canonical = []
        for name in names:
            known = self.standardize_name(name)
            canonical.append(known if known is not None else name)
        for name in canonical:
            self._add_station_line(name, line)
        for idx, (source, dest) in enumerate(zip(canonical, canonical[1:])):
            self._connections.append(
                {"source": source, "dest": dest, "distance": meters[idx], "line": line}
            )
        self.rebuild()
        return line

    def modify_station(self, name, new_name=None, add_lines=None, remove_lines=None):
        """Rename a station and/or change the lines serving it.

        Returns:
            str: The station's name after modification.
        """
        current = self.require_station(name)
        target = current
        if new_name is not None:
            cleaned = _clean_text(new_name)
            if not cleaned:
                raise DataError("new station name must not be empty")
            if cleaned != current:
                existing = self.standardize_name(cleaned)
                if existing is not None and existing != current:
                    raise DataError(f"station '{existing}' already exists")
                self._stations[cleaned] = self._stations.pop(current)
                for conn in self._connections:
                    if conn["source"] == current:
                        conn["source"] = cleaned
                    if conn["dest"] == current:
                        conn["dest"] = cleaned
                target = cleaned
        for line in add_lines or []:
            self._add_station_line(target, _clean_text(line))
        for line in remove_lines or []:
            lines = self._stations[target]
            if _clean_text(line) in lines:
                lines.remove(_clean_text(line))
        self.rebuild()
        return target

    def update_distance(self, name_a, name_b, distance, line=None):
        """Update the distance between two adjacent stations.

        Returns:
            int: Number of connection records updated.

        Raises:
            DataError: If the stations are not directly connected.
        """
        station_a = self.require_station(name_a)
        station_b = self.require_station(name_b)
        meters = _to_distance(distance)
        count = 0
        for conn in self._connections:
            pair = {conn["source"], conn["dest"]}
            if pair == {station_a, station_b} and (line is None or conn["line"] == line):
                conn["distance"] = meters
                count += 1
        if count == 0:
            raise DataError(f"no direct connection between '{station_a}' and '{station_b}'")
        self.rebuild()
        return count
