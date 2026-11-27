"""Graph data structures for the weighted undirected subway network.

Stations are identified by integer numbers inside the graph; the caller
(see network.py) is responsible for assigning those numbers. The graph also
keeps a mapping from station names to the lines they belong to.
"""


class Edge:
    """An undirected weighted edge representing a track segment on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line this segment belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest path search (equal to the distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self):
        return (
            f"Edge({self.source}, {self.dest}, "
            f"distance={self.distance}, line={self.line!r})"
        )


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adjacency = {}   # station number -> list of incident Edge objects
        self._edges = []       # every edge exactly once
        self.station_lines = {}

    # ----- vertices -----------------------------------------------------

    def add_vertex(self, vertex):
        """Add a vertex if it is not already present."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def vertices(self):
        """Return a list of all vertex numbers."""
        return list(self._adjacency)

    def vertex_count(self):
        """Return the number of vertices."""
        return len(self._adjacency)

    # ----- edges --------------------------------------------------------

    def add_edge(self, edge):
        """Add an undirected edge, creating its endpoints if necessary.

        Raises:
            ValueError: If the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("self-loops are not allowed in the subway network")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex):
        """Return the incident edges of ``vertex``.

        The returned list is the internal adjacency list (for speed); callers
        must not modify it.
        """
        return self._adjacency.get(vertex, [])

    def edges(self):
        """Return a copy of the list of all edges."""
        return list(self._edges)

    def edge_count(self):
        """Return the number of edges."""
        return len(self._edges)

    def find_edges(self, u, v):
        """Return all edges directly connecting ``u`` and ``v``."""
        return [edge for edge in self.adj(u) if edge.other(u) == v]

    def update_distance(self, u, v, distance, line=None):
        """Update the distance of edges between ``u`` and ``v``.

        Args:
            u, v: Station numbers.
            distance: New distance in meters.
            line: If given, only edges of this line are updated.

        Returns:
            int: Number of edges updated.
        """
        count = 0
        for edge in self.find_edges(u, v):
            if line is None or edge.line == line:
                edge.distance = distance
                count += 1
        return count

    def connected_component_count(self):
        """Return the number of connected components of the graph."""
        seen = set()
        components = 0
        for start in self._adjacency:
            if start in seen:
                continue
            components += 1
            seen.add(start)
            stack = [start]
            while stack:
                node = stack.pop()
                for edge in self._adjacency[node]:
                    nxt = edge.other(node)
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
        return components

    # ----- station line membership -------------------------------------

    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) list of lines of a station."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def get_station_lines(self, station_name):
        """Return a copy of the lines a station belongs to."""
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        """Return True if the station is served by more than one line."""
        return len(self.station_lines.get(station_name, [])) > 1
