"""Domain models: a weighted undirected graph and the Beijing Subway network built on it.

Graph nodes are integer station numbers assigned by the SubwayNetwork builder.
Station names are kept in mapping dictionaries and in Graph.station_lines.
"""

import math


class StationNotFoundError(LookupError):
    """Raised when a station name or number does not exist in the network."""


class Edge:
    """A weighted, undirected connection between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        weight: Distance in meters (the edge weight used by Dijkstra's algorithm).
        line: Name of the subway line the connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.weight = distance
        self.line = line

    @property
    def distance(self):
        """Distance in meters; identical to ``weight``."""
        return self.weight

    @distance.setter
    def distance(self, value):
        self.weight = value

    def other(self, vertex):
        """Return the endpoint of this edge opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.weight!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are supplied by the caller. ``station_lines`` maps station
    names to the list of lines serving that station.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    def add_vertex(self, vertex):
        """Add a vertex (station number) if it does not already exist."""
        if vertex not in self._adjacency:
            self._adjacency[vertex] = []

    def has_vertex(self, vertex) -> bool:
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def vertices(self) -> list:
        """Return a list of all vertices."""
        return list(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station, identified by its name."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge: Edge):
        """Add an undirected edge; it is visible from both endpoints.

        Raises:
            ValueError: For self-loops or negative weights.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        if edge.weight < 0:
            raise ValueError("Edge weight must be non-negative")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, vertex) -> list:
        """Return the list of edges incident to ``vertex`` (do not modify it)."""
        if vertex not in self._adjacency:
            raise KeyError(f"Unknown vertex {vertex!r}")
        return self._adjacency[vertex]

    def find_edges(self, a, b, line=None) -> list:
        """Return all edges between vertices ``a`` and ``b``, optionally on one line."""
        return [
            edge
            for edge in self._adjacency.get(a, [])
            if edge.other(a) == b and (line is None or edge.line == line)
        ]

    def remove_edge(self, edge: Edge):
        """Remove an edge from the graph."""
        self._adjacency[edge.source].remove(edge)
        self._adjacency[edge.dest].remove(edge)
        self._edges.remove(edge)

    def edges(self) -> list:
        """Return a list of all distinct edges."""
        return list(self._edges)

    def num_vertices(self) -> int:
        """Return the number of vertices."""
        return len(self._adjacency)

    def num_edges(self) -> int:
        """Return the number of distinct edges."""
        return len(self._edges)


def _clean_name(name) -> str:
    """Normalize a station or line name by converting to str and stripping spaces."""
    if name is None:
        return ""
    return str(name).strip()


def _clean_lines(lines) -> list:
    """Return a de-duplicated list of cleaned, non-empty line names in order."""
    if isinstance(lines, str):
        lines = [lines]
    result = []
    for line in lines or []:
        cleaned = _clean_name(line)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _validate_distance(distance) -> int:
    """Validate a distance in meters and return it as a positive integer."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number of meters")
    if not math.isfinite(distance):
        raise ValueError("Distance must be finite")
    value = int(round(distance))
    if value <= 0:
        raise ValueError("Distance must be positive")
    return value


class SubwayNetwork:
    """The Beijing Subway network: a Graph plus name/number mappings and line indexes.

    Attributes:
        graph: The weighted undirected Graph keyed by station numbers.
        station_to_number: Mapping station name -> station number.
        number_to_station: Mapping station number -> station name.
        line_stations: Mapping line name -> list of station names on that line.
        build_warnings: Messages describing records skipped while loading.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.line_stations = {}
        self.build_warnings = []
        self._next_number = 0

    @classmethod
    def from_data(cls, data: dict):
        """Build a network from a dataset dictionary (see data_loader)."""
        network = cls()
        network._load(data)
        return network

    def _load(self, data: dict):
        """Populate the network from stations and connections, recording problems."""
        for item in data.get("stations", []):
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) \
                    or not item["name"].strip():
                self.build_warnings.append(f"Skipped station record without a valid name: {item!r}")
                continue
            try:
                self.add_station(item["name"], item.get("lines", []))
            except ValueError as exc:
                self.build_warnings.append(f"Skipped station {item['name']!r}: {exc}")

        for conn in data.get("connections", []):
            try:
                source = conn["source"]
                dest = conn["dest"]
                distance = conn["distance"]
                line = conn["line"]
            except (KeyError, TypeError):
                self.build_warnings.append(f"Skipped malformed connection record: {conn!r}")
                continue
            for name in (source, dest):
                if not self.has_station(name) and _clean_name(name):
                    self.add_station(name, [line])
                    self.build_warnings.append(
                        f"Station '{_clean_name(name)}' is referenced by a connection "
                        f"but not listed; it was added automatically"
                    )
            try:
                self.add_connection(source, dest, distance, line)
            except ValueError as exc:
                self.build_warnings.append(
                    f"Skipped connection {_clean_name(source)} - {_clean_name(dest)} "
                    f"({_clean_name(line)}): {exc}"
                )

    def _index_line(self, line: str, station_name: str):
        """Record that ``station_name`` is served by ``line``."""
        stations = self.line_stations.setdefault(line, [])
        if station_name not in stations:
            stations.append(station_name)

    def _ensure_station_line(self, station_name: str, line: str):
        """Make sure the station's line list contains ``line``."""
        current = self.graph.station_lines[station_name]
        if line not in current:
            self.graph.set_station_lines(station_name, current + [line])
        self._index_line(line, station_name)

    def add_station(self, name, lines=()) -> int:
        """Add a station (or merge lines into an existing one) and return its number."""
        name = _clean_name(name)
        if not name:
            raise ValueError("Station name must not be empty")
        lines = _clean_lines(lines)
        if name in self.station_to_number:
            number = self.station_to_number[name]
            current = self.graph.station_lines[name]
            self.graph.set_station_lines(name, current + [l for l in lines if l not in current])
        else:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, lines)
        for line in lines:
            self._index_line(line, name)
        return number

    def add_connection(self, source, dest, distance, line):
        """Add a connection between two existing stations on a line.

        Raises:
            StationNotFoundError: If a station does not exist.
            ValueError: For invalid distances, self-connections or duplicates.
        """
        source_name = _clean_name(source)
        dest_name = _clean_name(dest)
        line = _clean_name(line)
        a = self.get_station_number(source_name)
        b = self.get_station_number(dest_name)
        if not line:
            raise ValueError("Line name must not be empty")
        if a == b:
            raise ValueError("Source and destination are the same station")
        value = _validate_distance(distance)
        if self.graph.find_edges(a, b, line):
            raise ValueError(f"Connection already exists on {line}")
        self.graph.add_edge(Edge(a, b, value, line))
        self._ensure_station_line(source_name, line)
        self._ensure_station_line(dest_name, line)

    def has_station(self, name) -> bool:
        """Return True if a station with this name exists."""
        return _clean_name(name) in self.station_to_number

    def get_station_number(self, name) -> int:
        """Return the station number for a station name."""
        key = _clean_name(name)
        if key not in self.station_to_number:
            raise StationNotFoundError(f"Station '{key}' does not exist")
        return self.station_to_number[key]

    def station_name(self, number) -> str:
        """Return the station name for a station number."""
        if number not in self.number_to_station:
            raise StationNotFoundError(f"No station with number {number!r}")
        return self.number_to_station[number]

    def station_names(self) -> list:
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def lines(self) -> list:
        """Return all line names sorted alphabetically."""
        return sorted(self.line_stations)

    def stations_on_line(self, line) -> list:
        """Return the station names served by a line."""
        return list(self.line_stations.get(line, []))

    def station_lines(self, name) -> list:
        """Return the lines serving a station."""
        key = _clean_name(name)
        if key not in self.graph.station_lines:
            raise StationNotFoundError(f"Station '{key}' does not exist")
        return list(self.graph.station_lines[key])

    def is_transfer_station(self, name) -> bool:
        """Return True if the station is served by more than one line."""
        return len(self.station_lines(name)) > 1

    def transfer_stations(self) -> list:
        """Return the sorted names of all multi-line interchange stations."""
        return sorted(
            name for name, lines in self.graph.station_lines.items() if len(lines) > 1
        )

    def add_line(self, line_name, station_names, distances):
        """Add a new line with an ordered station sequence and consecutive distances.

        Existing stations are reused (the new line is added to them); unknown
        stations are created.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered list of station names along the line.
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: If the input is inconsistent. Nothing is changed on error.
        """
        line = _clean_name(line_name)
        if not line:
            raise ValueError("Line name must not be empty")
        if line in self.line_stations:
            raise ValueError(f"Line '{line}' already exists")
        names = [_clean_name(n) for n in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if any(not n for n in names):
            raise ValueError("Station names must not be empty")
        if len(set(names)) != len(names):
            raise ValueError("Station sequence must not contain duplicates")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        values = [_validate_distance(d) for d in distances]

        for name in names:
            if self.has_station(name):
                self._ensure_station_line(name, line)
            else:
                self.add_station(name, [line])
        for i, value in enumerate(values):
            self.add_connection(names[i], names[i + 1], value, line)

    def modify_station(self, old_name, new_name=None, lines=None) -> str:
        """Rename a station and/or replace the lines serving it.

        Args:
            old_name: Current station name.
            new_name: New name (optional).
            lines: New list of lines (optional; replaces the existing list).

        Returns:
            The resulting station name.

        Raises:
            StationNotFoundError: If the station does not exist.
            ValueError: If the new name is taken or the new line list is empty.
        """
        old = _clean_name(old_name)
        number = self.get_station_number(old)
        target = _clean_name(new_name) if new_name else old
        if target != old and target in self.station_to_number:
            raise ValueError(f"Station '{target}' already exists")
        if lines is not None:
            new_lines = _clean_lines(lines)
            if not new_lines:
                raise ValueError("A station must be served by at least one line")
        else:
            new_lines = list(self.graph.station_lines[old])
        old_lines = list(self.graph.station_lines[old])

        if target != old:
            del self.station_to_number[old]
            self.station_to_number[target] = number
            self.number_to_station[number] = target
            self.graph.station_lines[target] = self.graph.station_lines.pop(old)
            for line, names in self.line_stations.items():
                self.line_stations[line] = [target if n == old else n for n in names]

        for line in old_lines:
            if line not in new_lines and line in self.line_stations:
                self.line_stations[line] = [n for n in self.line_stations[line] if n != target]
        self.graph.set_station_lines(target, new_lines)
        for line in new_lines:
            self._index_line(line, target)
        return target

    def update_distance(self, source, dest, distance, line=None) -> int:
        """Update the distance of the connection(s) between two stations.

        Args:
            source: Name of one station.
            dest: Name of the other station.
            distance: New distance in meters.
            line: Optional line to restrict the update to.

        Returns:
            The number of connections updated.

        Raises:
            StationNotFoundError: If a station does not exist.
            ValueError: If the distance is invalid or no connection is found.
        """
        a = self.get_station_number(source)
        b = self.get_station_number(dest)
        value = _validate_distance(distance)
        line_key = _clean_name(line) if line else None
        edges = self.graph.find_edges(a, b, line_key)
        if not edges:
            raise ValueError(
                f"No connection between '{_clean_name(source)}' and '{_clean_name(dest)}'"
            )
        for edge in edges:
            edge.weight = value
        return len(edges)

    def export_data(self) -> dict:
        """Export the network to a dataset dictionary (same format as subway_data.json)."""
        stations = [
            {"name": name, "lines": list(self.graph.station_lines[name])}
            for name in self.station_names()
        ]
        connections = [
            {
                "source": self.number_to_station[edge.source],
                "dest": self.number_to_station[edge.dest],
                "distance": edge.weight,
                "line": edge.line,
            }
            for edge in self.graph.edges()
        ]
        return {"stations": stations, "connections": connections}
