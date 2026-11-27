"""Graph data model for the subway network.

The network is a weighted undirected graph. Stations are identified by
integer numbers that are assigned by the caller (see ``DataManager``);
each station name maps to exactly one number, so a transfer station is a
single graph node shared by all of its lines.
"""

from __future__ import annotations


class Edge:
    """An undirected, weighted connection between two stations on one line."""

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        """Create an edge.

        Args:
            source: Station number of one endpoint.
            dest: Station number of the other endpoint.
            distance: Physical distance between the stations in meters.
            line: Name of the subway line this segment belongs to.

        Raises:
            ValueError: If the endpoints are equal or the distance is negative.
        """
        if source == dest:
            raise ValueError("an edge must connect two different stations")
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def other(self, number: int) -> int:
        """Return the endpoint opposite to ``number``.

        Raises:
            ValueError: If ``number`` is not an endpoint of this edge.
        """
        if number == self.source:
            return self.dest
        if number == self.dest:
            return self.source
        raise ValueError(f"station {number} is not an endpoint of this edge")

    def connects(self, a: int, b: int) -> bool:
        """Return True if this edge joins stations ``a`` and ``b`` (in either order)."""
        return (self.source == a and self.dest == b) or (self.source == b and self.dest == a)

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Attributes:
        adjacency: Mapping of station number -> list of incident ``Edge`` objects.
        station_lines: Mapping of station name -> list of line names serving it.
        station_to_number: Mapping of station name -> station number.
        number_to_name: Mapping of station number -> station name.
    """

    def __init__(self) -> None:
        self.adjacency: dict[int, list[Edge]] = {}
        self.station_lines: dict[str, list[str]] = {}
        self.station_to_number: dict[str, int] = {}
        self.number_to_name: dict[int, str] = {}
        self._edges: list[Edge] = []

    # ------------------------------------------------------------------ stations
    def add_station(self, name: str, number: int) -> None:
        """Register a station with a caller-assigned number.

        Re-registering an existing name with the same number is a no-op.

        Raises:
            ValueError: If the name or number is already bound to a different station.
        """
        existing = self.station_to_number.get(name)
        if existing is not None:
            if existing != number:
                raise ValueError(f"station '{name}' already has number {existing}")
            return
        if number in self.number_to_name:
            raise ValueError(f"number {number} is already used by '{self.number_to_name[number]}'")
        self.station_to_number[name] = number
        self.number_to_name[number] = name
        self.adjacency.setdefault(number, [])
        self.station_lines.setdefault(name, [])

    def set_station_lines(self, station_name: str, lines: list[str]) -> None:
        """Replace the list of lines serving a station (duplicates removed, order kept)."""
        unique: list[str] = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def rename_station(self, old_name: str, new_name: str) -> None:
        """Rename a station while keeping its number and its edges."""
        number = self.station_to_number.pop(old_name)
        self.station_to_number[new_name] = number
        self.number_to_name[number] = new_name
        self.station_lines[new_name] = self.station_lines.pop(old_name, [])

    def has_station(self, name: str) -> bool:
        """Return True if a station with this exact name exists."""
        return name in self.station_to_number

    def number_of(self, name: str) -> int:
        """Return the station number for a name.

        Raises:
            KeyError: If the station is unknown.
        """
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        """Return the station name for a station number."""
        return self.number_to_name[number]

    def lines_of(self, name: str) -> list[str]:
        """Return the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(name, []))

    def station_names(self) -> list[str]:
        """Return all station names, sorted alphabetically."""
        return sorted(self.station_to_number)

    def transfer_stations(self) -> list[str]:
        """Return names of stations served by more than one line."""
        return [name for name, lines in self.station_lines.items() if len(lines) > 1]

    def station_count(self) -> int:
        """Return the number of stations in the graph."""
        return len(self.station_to_number)

    # --------------------------------------------------------------------- edges
    def add_edge(self, edge: Edge) -> None:
        """Insert an undirected edge into the adjacency lists of both endpoints.

        Raises:
            ValueError: If an endpoint number has not been registered.
        """
        for number in (edge.source, edge.dest):
            if number not in self.adjacency:
                raise ValueError(f"station number {number} is not registered in the graph")
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, number: int) -> list[Edge]:
        """Return the edges incident to a station number (empty if unknown)."""
        return self.adjacency.get(number, [])

    def find_edges(self, a: int, b: int, line: str | None = None) -> list[Edge]:
        """Return edges joining stations ``a`` and ``b``, optionally filtered by line."""
        return [
            edge
            for edge in self.adjacency.get(a, [])
            if edge.connects(a, b) and (line is None or edge.line == line)
        ]

    def edges(self) -> list[Edge]:
        """Return a copy of the list of all edges."""
        return list(self._edges)

    def edge_count(self) -> int:
        """Return the number of undirected edges."""
        return len(self._edges)

    # ------------------------------------------------------------------ analysis
    def lines(self) -> list[str]:
        """Return the sorted list of all line names known to the graph."""
        names: set[str] = set()
        for lines in self.station_lines.values():
            names.update(lines)
        for edge in self._edges:
            names.add(edge.line)
        return sorted(names)

    def connected_components(self) -> int:
        """Return the number of connected components (isolated stations count as one each)."""
        seen: set[int] = set()
        count = 0
        for start in self.adjacency:
            if start in seen:
                continue
            count += 1
            seen.add(start)
            stack = [start]
            while stack:
                node = stack.pop()
                for edge in self.adjacency[node]:
                    neighbour = edge.other(node)
                    if neighbour not in seen:
                        seen.add(neighbour)
                        stack.append(neighbour)
        return count
