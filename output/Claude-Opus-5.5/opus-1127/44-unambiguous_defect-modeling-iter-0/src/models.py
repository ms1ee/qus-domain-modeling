"""Graph data structures for subway network modeling.

The network is a weighted undirected graph. Vertices are station numbers
(assigned by the caller); every edge carries the inter-station distance in
meters as weight together with the line it belongs to.
"""

from dataclasses import dataclass, field


class Edge:
    """A weighted edge between two stations on a given line."""

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    # Convenience aliases following the domain model naming.
    @property
    def from_(self):
        return self.source

    @property
    def to(self):
        return self.dest

    def other(self, vertex):
        """Return the endpoint that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError("Vertex %r is not an endpoint of this edge" % (vertex,))

    def reversed(self):
        """Return the same edge in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == (
            other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.weight, self.line)


class Graph:
    """Weighted undirected graph using adjacency lists.

    Attributes:
        graph: dict mapping station number -> list of outgoing ``Edge``.
        station_lines: dict mapping station name -> list of line names.
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self._edge_count = 0

    # ----- vertices -------------------------------------------------
    def add_vertex(self, number):
        self.graph.setdefault(number, [])

    def add_station(self, name, number, lines=None):
        """Register a station name with its (caller-assigned) number."""
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.add_vertex(number)
        if lines is not None:
            self.set_station_lines(name, lines)
        else:
            self.station_lines.setdefault(name, [])

    def set_station_lines(self, station_name, lines):
        """Set the lines a station belongs to."""
        if isinstance(lines, str):
            lines = [lines]
        unique = []
        for line in lines or []:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def has_vertex(self, number):
        return number in self.graph or number in self.number_to_station

    def vertices(self):
        result = set(self.graph.keys())
        result.update(self.number_to_station.keys())
        return result

    @property
    def vertex_count(self):
        return len(self.vertices())

    @property
    def edge_count(self):
        return self._edge_count

    # ----- edges ----------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both adjacency lists)."""
        if edge.weight is None or edge.weight < 0:
            raise ValueError("Edge weight must be a non-negative number")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self._edge_count += 1

    def adj(self, number):
        """Return the edges leaving the given vertex."""
        return self.graph.get(number, [])

    def edges(self):
        """Return every undirected edge once."""
        seen = set()
        result = []
        for v, edges in self.graph.items():
            for e in edges:
                key = (min(e.source, e.dest), max(e.source, e.dest), e.weight, e.line)
                if key not in seen:
                    seen.add(key)
                    result.append(e)
        return result

    # ----- stations -------------------------------------------------
    def get_station_name(self, number):
        return self.number_to_station.get(number, str(number))

    def get_station_number(self, name):
        return self.station_to_number.get(name)

    def is_transfer_station(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def __repr__(self):
        return "Graph(V=%d, E=%d)" % (self.vertex_count, self.edge_count)


@dataclass
class Station:
    """A subway station."""
    name: str
    number: int
    lines: list = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    """A subway line with its ordered station sequence."""
    name: str
    stations: list = field(default_factory=list)
