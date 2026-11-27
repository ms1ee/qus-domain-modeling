"""Core graph data structures for the subway network.

The Graph is a weighted directed graph. Station numbers (integers) are
assigned by the caller (see network.SubwayNetwork); the Graph only manages
nodes, edges and the station-to-lines table.
"""

import re


# Keyword rules for recognising non-numbered lines. Each entry maps a tuple
# of keywords (English or Chinese) to the canonical line name.
_KEYWORD_LINES = (
    (("changping", "昌平"), "Changping Line"),
    (("yizhuang", "亦庄"), "Yizhuang Line"),
    (("fangshan", "房山"), "Fangshan Line"),
    (("airport", "机场"), "Airport Line"),
)


def canonical_line(name) -> str:
    """Return a canonical line name so that equivalent spellings compare equal.

    For example "Line 1", "1号线" and "Subway Line 1" all map to "Line 1".
    """
    text = str(name).strip()
    lowered = text.lower()
    for keywords, canonical in _KEYWORD_LINES:
        if any(keyword in lowered or keyword in text for keyword in keywords):
            return canonical
    match = re.search(r"\d+", text)
    if match:
        return f"Line {int(match.group())}"
    return text


def line_matches(first, second) -> bool:
    """Return True if two line names refer to the same subway line."""
    return canonical_line(first) == canonical_line(second)


class Edge:
    """A directed, weighted connection between two station numbers.

    Attributes:
        source: Station number of the origin.
        dest: Station number of the destination.
        distance: Distance in meters (int).
        line: Name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        distance = int(distance)
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> int:
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def __repr__(self) -> str:
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph with adjacency lists.

    Attributes:
        station_lines: dict mapping station name to the list of line names it serves.
    """

    def __init__(self):
        self._adjacency = {}  # station number -> list[Edge] (outgoing edges)
        self.station_lines = {}  # station name -> list[str]

    # ----- node management -------------------------------------------------
    def add_node(self, number) -> None:
        """Ensure a node with the given station number exists."""
        self._adjacency.setdefault(number, [])

    def has_node(self, number) -> bool:
        """Return True if the station number is a node of the graph."""
        return number in self._adjacency

    def nodes(self) -> list:
        """Return the list of station numbers in the graph."""
        return list(self._adjacency)

    def set_station_lines(self, station_name, lines) -> None:
        """Set the lines served by a station, removing duplicates while keeping order."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    # ----- edge management -------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge. Only the listed direction is added."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)

    def adjacent(self, number) -> list:
        """Return the outgoing edges of a station number."""
        return self._adjacency.get(number, [])

    def find_edges(self, source, dest) -> list:
        """Return all edges from source to dest."""
        return [edge for edge in self._adjacency.get(source, []) if edge.dest == dest]

    def all_edges(self):
        """Yield every edge in the graph."""
        for edges in self._adjacency.values():
            yield from edges

    @property
    def node_count(self) -> int:
        """Number of nodes (stations)."""
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        """Number of directed edges."""
        return sum(len(edges) for edges in self._adjacency.values())
