"""Graph data model for the Beijing Subway network.

The graph is an undirected, weighted graph. Vertices are station numbers
(integers) assigned by the caller; each edge stores its distance in meters
(used as the weight) and the subway line it belongs to.
"""

from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(eq=False)
class Edge:
    """An undirected connection between two adjacent stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance in meters (the edge weight).
        line: name of the subway line this connection belongs to.
    """

    source: int
    dest: int
    distance: float
    line: str

    @property
    def weight(self) -> float:
        """Edge weight used by shortest-path algorithms (meters)."""
        return self.distance

    def other_end(self, station: int) -> int:
        """Return the endpoint opposite to ``station``."""
        if station == self.source:
            return self.dest
        if station == self.dest:
            return self.source
        raise ValueError(f"Station {station} is not an endpoint of this edge")


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are supplied by the caller; the graph only stores them.
    ``station_lines`` maps station names to the lines serving them, which is
    used to detect transfer stations.
    """

    def __init__(self) -> None:
        self._adjacency: Dict[int, List[Edge]] = {}
        self._edges: List[Edge] = []
        self.station_lines: Dict[str, List[str]] = {}

    @property
    def vertex_count(self) -> int:
        """Number of vertices (stations) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        """Number of undirected edges in the graph."""
        return len(self._edges)

    def add_vertex(self, station_number: int) -> None:
        """Add a vertex if it does not exist yet."""
        self._adjacency.setdefault(station_number, [])

    def has_vertex(self, station_number: int) -> bool:
        """Return True if the station number is a vertex of the graph."""
        return station_number in self._adjacency

    def vertices(self) -> List[int]:
        """Return all station numbers in insertion order."""
        return list(self._adjacency.keys())

    def set_station_lines(self, station_name: str, lines: Iterable[str]) -> None:
        """Record the (de-duplicated, ordered) lines serving a station."""
        unique: List[str] = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge, creating missing vertices automatically."""
        if edge.source == edge.dest:
            raise ValueError("Self-loops are not allowed in the subway graph")
        if edge.distance <= 0:
            raise ValueError("Edge distance must be positive")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, station_number: int) -> List[Edge]:
        """Return the edges incident to a station."""
        try:
            return self._adjacency[station_number]
        except KeyError:
            raise KeyError(f"Unknown station number: {station_number}") from None

    def edges(self) -> List[Edge]:
        """Return a copy of the list of all edges."""
        return list(self._edges)

    def find_edges(self, a: int, b: int) -> List[Edge]:
        """Return all edges directly connecting stations ``a`` and ``b``."""
        if not self.has_vertex(a):
            return []
        return [e for e in self._adjacency[a] if e.other_end(a) == b]

    def lines(self) -> List[str]:
        """Return the sorted list of distinct line names appearing on edges."""
        return sorted({e.line for e in self._edges})

    def connected_components(self) -> List[List[int]]:
        """Return the connected components as lists of station numbers."""
        seen = set()
        components: List[List[int]] = []
        for start in self._adjacency:
            if start in seen:
                continue
            component: List[int] = []
            queue = deque([start])
            seen.add(start)
            while queue:
                vertex = queue.popleft()
                component.append(vertex)
                for edge in self._adjacency[vertex]:
                    neighbour = edge.other_end(vertex)
                    if neighbour not in seen:
                        seen.add(neighbour)
                        queue.append(neighbour)
            components.append(component)
        return components


@dataclass
class Station:
    """Station information attached to a graph vertex."""

    station_id: int
    name: str
    station_number: str
    is_transfer_station: bool


@dataclass
class SubwayNetwork:
    """The complete network: graph plus name/number lookup tables."""

    graph: Graph
    station_to_number: Dict[str, int]
    stations: Dict[int, Station]
    line_names: List[str]

    def number_of(self, name: str) -> int:
        """Return the station number for a station name."""
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        """Return the station name for a station number."""
        return self.stations[number].name

    def station_names(self) -> List[str]:
        """Return all station names."""
        return list(self.station_to_number.keys())
