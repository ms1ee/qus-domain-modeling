"""
Core data structures for the Beijing Subway fare calculation system.

Contains:
    * Edge   - a weighted, line-labelled undirected edge between two stations.
    * Graph  - a weighted undirected graph with adjacency lists.  Station
               numbers are assigned by the caller, not by the graph.
    * MinPQ  - a binary-heap based minimum priority queue used to speed up
               Dijkstra's algorithm to O((V + E) log V).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source:   station number of one end point.
        dest:     station number of the other end point.
        distance: distance in meters.
        weight:   same as ``distance`` (used by the path algorithms).
        line:     the name of the subway line this edge belongs to.
    """

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source: int, dest: int, distance: float, line: Optional[str] = None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self) -> int:
        """Return one end point of the edge."""
        return self.source

    def other(self, vertex: int) -> int:
        """Return the end point of the edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an end point of this edge")

    def set_distance(self, distance: float) -> None:
        """Update the distance (and weight) of the edge."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.distance = distance
        self.weight = distance

    def __repr__(self) -> str:
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    Station numbers are assigned by the caller.  The graph additionally keeps
    ``station_lines`` (station name -> list of lines) and optional name/number
    mappings for convenience.
    """

    def __init__(self) -> None:
        self._adj: Dict[int, List[Edge]] = {}
        self._edges: List[Edge] = []
        self.station_lines: Dict[str, List[str]] = {}
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}

    # ------------------------------------------------------------------ nodes
    def add_vertex(self, vertex: int) -> None:
        """Ensure ``vertex`` exists in the graph."""
        if vertex not in self._adj:
            self._adj[vertex] = []

    def add_station(self, name: str, number: int, lines: Optional[Iterable[str]] = None) -> None:
        """Register a station name with a caller-assigned number."""
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.add_vertex(number)
        if lines is not None:
            self.set_station_lines(name, lines)

    def set_station_lines(self, station_name: str, lines: Iterable[str]) -> None:
        """Set the list of lines serving ``station_name``."""
        self.station_lines[station_name] = list(lines)

    def is_transfer_station(self, station_name: str) -> bool:
        return len(self.station_lines.get(station_name, [])) > 1

    def has_vertex(self, vertex: int) -> bool:
        return vertex in self._adj

    def vertices(self) -> List[int]:
        return list(self._adj.keys())

    def V(self) -> int:
        return len(self._adj)

    # ------------------------------------------------------------------ edges
    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex: int) -> List[Edge]:
        """Return edges incident to ``vertex``."""
        return self._adj.get(vertex, [])

    def edges(self) -> List[Edge]:
        return list(self._edges)

    def E(self) -> int:
        return len(self._edges)

    def find_edges(self, source: int, dest: int, line: Optional[str] = None) -> List[Edge]:
        result = []
        for e in self._adj.get(source, []):
            if (e.source == source and e.dest == dest) or (e.source == dest and e.dest == source):
                if line is None or e.line == line:
                    result.append(e)
        return result

    def update_edge_distance(self, source: int, dest: int, distance: float,
                             line: Optional[str] = None) -> int:
        """Update the distance of matching edges.  Returns number updated."""
        matches = self.find_edges(source, dest, line)
        for e in matches:
            e.set_distance(distance)
        return len(matches)

    def remove_edge(self, source: int, dest: int, line: Optional[str] = None) -> int:
        """Remove matching edges.  Returns number of removed edges."""
        matches = self.find_edges(source, dest, line)
        for e in matches:
            if e in self._adj.get(e.source, []):
                self._adj[e.source].remove(e)
            if e.dest != e.source and e in self._adj.get(e.dest, []):
                self._adj[e.dest].remove(e)
            self._edges.remove(e)
        return len(matches)

    def degree(self, vertex: int) -> int:
        return len(self._adj.get(vertex, []))

    def to_dict(self) -> Dict[int, Dict[int, float]]:
        """Return a plain dict adjacency representation {v: {w: min distance}}."""
        result: Dict[int, Dict[int, float]] = {v: {} for v in self._adj}
        for e in self._edges:
            for a, b in ((e.source, e.dest), (e.dest, e.source)):
                if b not in result[a] or e.weight < result[a][b]:
                    result[a][b] = e.weight
        return result

    def __repr__(self) -> str:
        return f"Graph(V={self.V()}, E={self.E()})"


class MinPQ:
    """Binary heap based minimum priority queue.

    Items must be mutually comparable (tuples are typical).
    """

    def __init__(self) -> None:
        self._heap: List[Any] = []

    def insert(self, item: Any) -> None:
        heap = self._heap
        heap.append(item)
        self._swim(len(heap) - 1)

    push = insert

    def min(self) -> Any:
        if not self._heap:
            raise IndexError("Priority queue underflow")
        return self._heap[0]

    def del_min(self) -> Any:
        heap = self._heap
        if not heap:
            raise IndexError("Priority queue underflow")
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            self._sink(0)
        return top

    pop = del_min

    def is_empty(self) -> bool:
        return not self._heap

    def size(self) -> int:
        return len(self._heap)

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)

    def _swim(self, k: int) -> None:
        heap = self._heap
        item = heap[k]
        while k > 0:
            parent = (k - 1) >> 1
            if item < heap[parent]:
                heap[k] = heap[parent]
                k = parent
            else:
                break
        heap[k] = item

    def _sink(self, k: int) -> None:
        heap = self._heap
        n = len(heap)
        item = heap[k]
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and heap[child + 1] < heap[child]:
                child += 1
            if heap[child] < item:
                heap[k] = heap[child]
                k = child
            else:
                break
        heap[k] = item
