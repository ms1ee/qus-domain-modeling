"""Subway network model: station registry, graph construction and data updates.

The network keeps the raw station/connection data so that it can be modified
(add lines, rename or edit stations, update distances) and the graph rebuilt
consistently. Station numbers are assigned here (1-based, in dataset order).
"""

import json

import data_loader
from models import Edge, Graph


class NetworkError(Exception):
    """Base error for invalid network operations."""


class UnknownStationError(NetworkError):
    """Raised when a station name or number does not exist."""


def _normalize(name):
    """Normalise a station name for comparison (ignore spaces, case and the '站' suffix)."""
    text = "".join(str(name).split()).casefold()
    if text.endswith("站"):
        text = text[:-1]
    return text


def _unique(items):
    """Return items without duplicates, keeping the first occurrence order."""
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _validate_distance(distance):
    """Validate and return a positive integer distance in meters."""
    if isinstance(distance, bool):
        raise NetworkError("Distance must be an integer number of meters")
    try:
        value = int(distance)
    except (TypeError, ValueError) as exc:
        raise NetworkError("Distance must be an integer number of meters: %r" % (distance,)) from exc
    if value <= 0:
        raise NetworkError("Distance must be positive, got %r" % (distance,))
    return value


class SubwayNetwork:
    """The Beijing Subway network.

    Attributes:
        name: Network name.
        dataSource: Source of the data.
        version: Data version string.
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        graph: The weighted undirected ``Graph`` of the network.
    """

    def __init__(self, data=None, name="Beijing Subway", version=None, data_source=None):
        if data is None:
            data = data_loader.load_subway_data()
        self.name = name
        self.dataSource = data_source or "subway_data.json"
        self.version = str(version if version is not None else data.get("version", "1.0"))
        self._stations = {}      # station name -> list of line names (insertion ordered)
        self._connections = []   # list of dicts: source, dest, distance, line
        self._undeclared = []    # station names referenced by connections but not declared
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self._load(data)
        self._rebuild()

    # ------------------------------------------------------------------
    # Loading and graph construction
    # ------------------------------------------------------------------
    def _load(self, data):
        """Read stations and connections from the raw dataset."""
        try:
            for item in data.get("stations", []):
                name = str(item["name"]).strip()
                lines = [str(line).strip() for line in item.get("lines", [])]
                if name in self._stations:
                    merged = self._stations[name] + [l for l in lines if l not in self._stations[name]]
                    self._stations[name] = merged
                else:
                    self._stations[name] = _unique(lines)

            for item in data.get("connections", []):
                conn = {
                    "source": str(item["source"]).strip(),
                    "dest": str(item["dest"]).strip(),
                    "distance": item["distance"],
                    "line": str(item["line"]).strip(),
                }
                self._connections.append(conn)
        except (KeyError, TypeError, AttributeError) as exc:
            raise NetworkError("Malformed subway data: %s" % exc) from exc

        # Stations referenced only by connections are registered so the graph is complete.
        for conn in self._connections:
            for key in ("source", "dest"):
                name = conn[key]
                if name not in self._stations:
                    self._stations[name] = []
                    self._undeclared.append(name)
                if name in self._undeclared and conn["line"] not in self._stations[name]:
                    self._stations[name].append(conn["line"])

    def _rebuild(self):
        """Rebuild station numbers and the graph from the raw data."""
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for number, (name, lines) in enumerate(self._stations.items(), start=1):
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.set_station_lines(name, lines)
            self.graph.add_vertex(number)
        for conn in self._connections:
            distance = _validate_distance(conn["distance"])
            u = self.station_to_number[conn["source"]]
            v = self.station_to_number[conn["dest"]]
            try:
                self.graph.add_edge(Edge(u, v, distance, conn["line"]))
            except ValueError as exc:
                raise NetworkError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def station_names(self):
        """Return all official station names in dataset order."""
        return list(self._stations.keys())

    def has_station(self, name):
        """Return True if the exact official station name exists."""
        return name in self._stations

    def standardize_name(self, name):
        """Map a user-entered name to the official station name.

        Returns:
            str or None: the official name, or None if no station matches.
        """
        key = _normalize(name)
        if not key:
            return None
        for official in self._stations:
            if _normalize(official) == key:
                return official
        return None

    def get_number(self, name):
        """Return the station number of an official station name."""
        if name not in self.station_to_number:
            raise UnknownStationError("Station '%s' does not exist" % name)
        return self.station_to_number[name]

    def get_name(self, number):
        """Return the official station name of a station number."""
        if number not in self.number_to_station:
            raise UnknownStationError("Station number %r does not exist" % (number,))
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return the lines serving a station."""
        if name not in self._stations:
            raise UnknownStationError("Station '%s' does not exist" % name)
        return list(self._stations[name])

    def is_transfer_station(self, name):
        """Return True if the station is served by two or more lines."""
        return len(self._stations.get(name, [])) >= 2

    def transfer_stations(self):
        """Return the names of all transfer (interchange) stations."""
        return [name for name in self._stations if self.is_transfer_station(name)]

    def line_names(self):
        """Return the sorted names of all lines in the network."""
        lines = set()
        for station_lines in self._stations.values():
            lines.update(station_lines)
        for conn in self._connections:
            lines.add(conn["line"])
        return sorted(lines)

    def line_stations(self, line):
        """Return the names of stations served by a line."""
        return [name for name, lines in self._stations.items() if line in lines]

    def connections(self):
        """Return a copy of all connection records."""
        return [dict(conn) for conn in self._connections]

    def raw_undeclared_stations(self):
        """Return station names referenced by connections but missing from the station list."""
        return list(self._undeclared)

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line described by its ordered station sequence.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names (new names create new stations).
            distances: Distances in meters between consecutive stations
                (length must be ``len(station_names) - 1``).
        """
        line = str(line_name).strip()
        if not line:
            raise NetworkError("Line name must not be empty")
        if line in self.line_names():
            raise NetworkError("Line '%s' already exists" % line)
        if len(station_names) < 2:
            raise NetworkError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise NetworkError("Expected %d distances, got %d" % (len(station_names) - 1, len(distances)))
        validated = [_validate_distance(d) for d in distances]

        official = []
        for raw in station_names:
            std = self.standardize_name(raw)
            if std is None:
                std = str(raw).strip()
                if not std:
                    raise NetworkError("Station name must not be empty")
            official.append(std)

        for name in official:
            self._stations.setdefault(name, [])
            if line not in self._stations[name]:
                self._stations[name].append(line)
        for i, distance in enumerate(validated):
            self._connections.append({
                "source": official[i],
                "dest": official[i + 1],
                "distance": distance,
                "line": line,
            })
        self._rebuild()

    def modify_station(self, name, new_name=None, add_lines=None, remove_lines=None):
        """Modify a station: rename it and/or change the lines serving it.

        Returns:
            str: The (possibly new) official name of the station.
        """
        official = self.standardize_name(name)
        if official is None:
            raise UnknownStationError("Station '%s' does not exist" % name)

        if new_name is not None:
            target = str(new_name).strip()
            if not target:
                raise NetworkError("New station name must not be empty")
            if target != official and self.standardize_name(target) is not None:
                raise NetworkError("Station '%s' already exists" % target)
            if target != official:
                self._stations = {
                    (target if key == official else key): value
                    for key, value in self._stations.items()
                }
                for conn in self._connections:
                    if conn["source"] == official:
                        conn["source"] = target
                    if conn["dest"] == official:
                        conn["dest"] = target
                if official in self._undeclared:
                    self._undeclared = [target if n == official else n for n in self._undeclared]
                official = target

        lines = self._stations[official]
        for line in add_lines or []:
            line = str(line).strip()
            if line and line not in lines:
                lines.append(line)
        for line in remove_lines or []:
            line = str(line).strip()
            if line in lines:
                lines.remove(line)
        self._rebuild()
        return official

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance of the direct connection(s) between two stations.

        Returns:
            int: number of connection records updated.
        """
        a = self.standardize_name(station_a)
        b = self.standardize_name(station_b)
        if a is None:
            raise UnknownStationError("Station '%s' does not exist" % station_a)
        if b is None:
            raise UnknownStationError("Station '%s' does not exist" % station_b)
        value = _validate_distance(distance)
        matches = [
            conn for conn in self._connections
            if {conn["source"], conn["dest"]} == {a, b} and (line is None or conn["line"] == line)
        ]
        if not matches:
            raise NetworkError("No direct connection between '%s' and '%s'" % (a, b))
        for conn in matches:
            conn["distance"] = value
        self._rebuild()
        return len(matches)

    def to_dict(self):
        """Return the network as a dataset dictionary (same schema as subway_data.json)."""
        return {
            "stations": [{"name": n, "lines": list(l)} for n, l in self._stations.items()],
            "connections": self.connections(),
        }

    def save(self, path):
        """Write the network to a JSON file."""
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)
