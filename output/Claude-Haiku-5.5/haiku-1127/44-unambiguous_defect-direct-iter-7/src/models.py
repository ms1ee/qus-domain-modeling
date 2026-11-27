"""Graph data structures and the subway network model.

``Graph`` is a generic weighted undirected graph whose vertices are integer
station numbers. The numbers are assigned by the caller (``SubwayNetwork``),
not by ``Graph`` itself. ``SubwayNetwork`` maps official station names to
numbers, keeps line information, and offers data update operations.
"""

from __future__ import annotations


class Edge:
    """An undirected connection between two stations on one subway line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters (also used as the edge weight).
        line: Name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance)."""
        return self.distance

    @weight.setter
    def weight(self, value: float) -> None:
        self.distance = value

    def other(self, vertex: int) -> int:
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        station_lines: Mapping from station name to the list of line names
            the station belongs to (interchange stations have several).
    """

    def __init__(self) -> None:
        self._adj: dict[int, list[Edge]] = {}
        self._edges: list[Edge] = []
        self.station_lines: dict[str, list[str]] = {}

    # ----- vertices -----------------------------------------------------
    def add_vertex(self, vertex: int) -> None:
        """Add a vertex if it does not exist yet."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        return vertex in self._adj

    def vertices(self) -> list[int]:
        return list(self._adj.keys())

    def set_station_lines(self, station_name: str, lines) -> None:
        """Record the lines a station belongs to."""
        self.station_lines[station_name] = list(lines)

    # ----- edges --------------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge (stored in both endpoints' adjacency lists)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def neighbors(self, vertex: int) -> list[Edge]:
        """Return the edges incident to ``vertex`` (do not modify the list)."""
        return self._adj.get(vertex, [])

    def edges_between(self, u: int, v: int) -> list[Edge]:
        """Return all edges joining ``u`` and ``v``."""
        return [edge for edge in self.neighbors(u) if edge.other(u) == v]

    def edges(self) -> list[Edge]:
        return list(self._edges)

    @property
    def vertex_count(self) -> int:
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        return len(self._edges)


def _clean_name(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string")
    return value.strip()


def _validate_distance(distance) -> int:
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("distance must be a number of meters")
    value = int(round(distance))
    if value <= 0:
        raise ValueError("distance must be a positive number of meters")
    return value


class SubwayNetwork:
    """The Beijing Subway network: stations, lines and connections.

    Attributes:
        graph: The underlying weighted undirected ``Graph``.
        station_to_number: Official station name -> station number.
        number_to_station: Station number -> official station name.
    """

    def __init__(self) -> None:
        self.graph = Graph()
        self.station_to_number: dict[str, int] = {}
        self.number_to_station: dict[int, str] = {}
        self._line_order: list[str] = []
        self._next_number = 0

    # ----- queries ------------------------------------------------------
    def has_station(self, name: str) -> bool:
        return name in self.station_to_number

    def station_names(self) -> list[str]:
        return list(self.station_to_number.keys())

    def station_count(self) -> int:
        return len(self.station_to_number)

    def number_of(self, name: str) -> int:
        """Return the station number of ``name`` (KeyError if unknown)."""
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        """Return the station name of ``number`` (KeyError if unknown)."""
        return self.number_to_station[number]

    def station_lines(self, name: str) -> list[str]:
        """Return a copy of the line names a station belongs to."""
        return list(self.graph.station_lines.get(name, []))

    def lines(self) -> list[str]:
        """Return all line names in the order they were first seen."""
        return list(self._line_order)

    def stations_on_line(self, line: str) -> list[str]:
        """Return the names of all stations serving ``line``."""
        return [name for name in self.station_names() if line in self.station_lines(name)]

    def transfer_stations(self) -> list[str]:
        """Return stations served by two or more lines."""
        return [name for name in self.station_names() if len(self.station_lines(name)) >= 2]

    # ----- construction and updates ------------------------------------
    def _register_line(self, line: str) -> None:
        if line not in self._line_order:
            self._line_order.append(line)

    def add_station(self, name: str, lines=None) -> int:
        """Add a station (or merge lines into an existing one).

        Returns:
            The station number assigned to ``name``.
        """
        name = _clean_name(name, "station name")
        new_lines = [_clean_name(line, "line name") for line in (lines or [])]
        if name in self.station_to_number:
            number = self.station_to_number[name]
            base = self.station_lines(name)
        else:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            base = []
        merged = list(base)
        for line in new_lines:
            if line not in merged:
                merged.append(line)
        self.graph.set_station_lines(name, merged)
        for line in new_lines:
            self._register_line(line)
        return number

    def update_station_lines(self, name: str, lines) -> None:
        """Replace the line list of an existing station."""
        if name not in self.station_to_number:
            raise ValueError(f"station '{name}' does not exist")
        cleaned: list[str] = []
        for line in lines:
            line = _clean_name(line, "line name")
            if line not in cleaned:
                cleaned.append(line)
            self._register_line(line)
        self.graph.set_station_lines(name, cleaned)

    def rename_station(self, old_name: str, new_name: str) -> None:
        """Rename an existing station, keeping its number and connections."""
        new_name = _clean_name(new_name, "station name")
        if old_name not in self.station_to_number:
            raise ValueError(f"station '{old_name}' does not exist")
        if new_name != old_name and new_name in self.station_to_number:
            raise ValueError(f"station '{new_name}' already exists")
        number = self.station_to_number.pop(old_name)
        lines = self.graph.station_lines.pop(old_name, [])
        self.station_to_number[new_name] = number
        self.number_to_station[number] = new_name
        self.graph.station_lines[new_name] = lines

    def add_connection(self, source: str, dest: str, distance, line: str) -> Edge:
        """Add a connection between two adjacent stations on ``line``.

        Stations that do not exist yet are created and assigned ``line``.
        """
        source = _clean_name(source, "station name")
        dest = _clean_name(dest, "station name")
        line = _clean_name(line, "line name")
        if source == dest:
            raise ValueError("a connection must join two different stations")
        dist = _validate_distance(distance)
        if source not in self.station_to_number:
            self.add_station(source, [line])
        if dest not in self.station_to_number:
            self.add_station(dest, [line])
        edge = Edge(self.number_of(source), self.number_of(dest), dist, line)
        self.graph.add_edge(edge)
        self._register_line(line)
        return edge

    def update_distance(self, source: str, dest: str, distance, line: str = None) -> int:
        """Update the distance of the connection(s) between two stations.

        Returns:
            The number of edges updated.
        Raises:
            ValueError: If no matching connection exists.
        """
        if source not in self.station_to_number or dest not in self.station_to_number:
            raise ValueError("both stations must exist")
        dist = _validate_distance(distance)
        matched = [
            edge
            for edge in self.graph.edges_between(self.number_of(source), self.number_of(dest))
            if line is None or edge.line == line
        ]
        if not matched:
            raise ValueError(f"no connection between '{source}' and '{dest}'")
        for edge in matched:
            edge.distance = dist
        return len(matched)

    def add_line(self, line: str, station_names, distances) -> None:
        """Add a new line from an ordered station sequence.

        Args:
            line: Name of the new line (must not exist yet).
            station_names: Ordered station names along the line.
            distances: Distances in meters between consecutive stations
                (``len(station_names) - 1`` values).
        """
        line = _clean_name(line, "line name")
        if line in self._line_order:
            raise ValueError(f"line '{line}' already exists")
        names = [_clean_name(n, "station name") for n in station_names]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise ValueError("expected one distance per pair of consecutive stations")
        for name in names:
            self.add_station(name, [line])
        for index in range(len(names) - 1):
            self.add_connection(names[index], names[index + 1], distances[index], line)


def build_network(data: dict) -> SubwayNetwork:
    """Build a ``SubwayNetwork`` from the parsed subway data dictionary."""
    network = SubwayNetwork()
    for station in data.get("stations", []):
        network.add_station(station["name"], station.get("lines", []))
    for conn in data.get("connections", []):
        network.add_connection(conn["source"], conn["dest"], conn["distance"], conn["line"])
    return network
