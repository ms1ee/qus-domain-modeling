"""Graph data structures used to model the subway network."""
from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Sequence


class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: station number of the origin station.
        dest: station number of the destination station.
        weight: edge weight, equal to the actual distance in meters.
        line: name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "weight", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if distance < 0:
            raise ValueError("edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.weight = distance
        self.line = line

    @property
    def distance(self) -> float:
        """Distance in meters (alias of ``weight``)."""
        return self.weight

    @distance.setter
    def distance(self, value: float) -> None:
        if value < 0:
            raise ValueError("edge distance must be non-negative")
        self.weight = value

    def __repr__(self) -> str:
        return (
            f"Edge(source={self.source}, dest={self.dest}, "
            f"distance={self.weight}, line={self.line!r})"
        )


class Graph:
    """Weighted directed graph stored as adjacency lists.

    Station numbers are assigned by the caller. Each connection is usable only
    in the direction in which it was added.

    Attributes:
        station_lines: mapping of station name -> list of line names it belongs to.
    """

    def __init__(self) -> None:
        self._adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------ vertices
    def add_vertex(self, vertex: int) -> None:
        """Ensure that ``vertex`` exists in the graph."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        """Return True if ``vertex`` is a node of the graph."""
        return vertex in self._adj

    def vertices(self) -> List[int]:
        """Return all station numbers in the graph."""
        return list(self._adj.keys())

    @property
    def num_vertices(self) -> int:
        return len(self._adj)

    # --------------------------------------------------------------------- edges
    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge, creating its endpoints if necessary."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)

    def adjacent(self, vertex: int) -> Sequence[Edge]:
        """Return the outgoing edges of ``vertex`` (do not mutate the result)."""
        return self._adj.get(vertex, [])

    def edges(self) -> Iterator[Edge]:
        """Iterate over every edge in the graph."""
        for edge_list in self._adj.values():
            for edge in edge_list:
                yield edge

    def edges_between(self, source: int, dest: int) -> List[Edge]:
        """Return all edges going from ``source`` to ``dest``."""
        return [edge for edge in self._adj.get(source, []) if edge.dest == dest]

    def remove_edge(self, source: int, dest: int, line: Optional[str] = None) -> int:
        """Remove edges from ``source`` to ``dest`` (optionally a single line).

        Returns the number of removed edges.
        """
        current = self._adj.get(source, [])
        kept = [
            edge
            for edge in current
            if not (edge.dest == dest and (line is None or edge.line == line))
        ]
        removed = len(current) - len(kept)
        self._adj[source] = kept
        return removed

    @property
    def num_edges(self) -> int:
        return sum(len(edge_list) for edge_list in self._adj.values())

    # ------------------------------------------------------------ station lines
    def set_station_lines(self, station_name: str, lines: Sequence[str]) -> None:
        """Set the list of lines that serve a station."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name: str) -> List[str]:
        """Return the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))
