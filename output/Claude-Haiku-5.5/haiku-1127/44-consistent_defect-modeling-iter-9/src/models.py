"""Core domain models and exception types for the subway fare system."""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SubwayError(Exception):
    """Base class for all errors raised by the subway system."""


class DataError(SubwayError):
    """The subway dataset is malformed or an update is invalid."""


class InputFormatError(SubwayError):
    """The user query does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(SubwayError):
    """A station name could not be resolved to any known station."""


class LogicalValidationError(SubwayError):
    """A query is logically invalid (e.g. start equals end)."""


class PathNotFoundError(SubwayError):
    """No path exists between two stations under the given constraints."""


class FareCalculationError(SubwayError):
    """A fare or time estimate could not be computed."""


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

@dataclass
class Station:
    """A subway station with its numeric identifier and transfer flag."""

    station_id: int
    name: str
    is_transfer: bool = False


@dataclass
class Line:
    """A subway line and the ordered list of station names it serves."""

    name: str
    station_sequence: list = field(default_factory=list)

    def add_station(self, station_name):
        """Append a station to the line if it is not already present."""
        if station_name not in self.station_sequence:
            self.station_sequence.append(station_name)


class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: station number of the origin.
        dest: station number of the destination.
        distance: actual distance in meters (used as the weight).
        line: name of the line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph of stations with adjacency lists.

    Station numbers are assigned by the caller. The graph also keeps a mapping
    from station name to the list of lines serving that station.
    """

    def __init__(self):
        self._adjacency = {}
        self._edge_count = 0
        self.station_lines = {}

    def add_node(self, node):
        """Register a station number as a node of the graph."""
        self._adjacency.setdefault(node, [])

    def add_edge(self, edge):
        """Add a directed edge, creating its endpoint nodes if needed."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._edge_count += 1

    def adj(self, node):
        """Return the list of outgoing edges of a node."""
        return self._adjacency.get(node, [])

    def nodes(self):
        """Return all station numbers in the graph."""
        return list(self._adjacency.keys())

    def edges(self):
        """Iterate over all edges of the graph."""
        for outgoing in self._adjacency.values():
            for edge in outgoing:
                yield edge

    def has_node(self, node):
        return node in self._adjacency

    @property
    def node_count(self):
        return len(self._adjacency)

    @property
    def edge_count(self):
        return self._edge_count

    def set_station_lines(self, station_name, lines):
        """Record the (de-duplicated, order-preserving) lines serving a station."""
        unique = []
        for line_name in lines:
            if line_name not in unique:
                unique.append(line_name)
        self.station_lines[station_name] = unique
