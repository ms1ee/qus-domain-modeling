"""Core data models: weighted undirected graph and the subway network wrapper."""

import re


def natural_sort_key(text):
    """Sort key that orders embedded numbers numerically (e.g. 'Line 2' < 'Line 10')."""
    parts = re.split(r"(\d+)", text)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


class Edge:
    """An undirected, weighted connection between two stations.

    ``source`` and ``dest`` are station numbers, ``distance`` is in meters,
    and ``line`` is the name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph using adjacency lists.

    Vertices are station numbers assigned by the caller. The ``station_lines``
    dictionary maps station names to the list of line names serving them.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    def add_vertex(self, vertex):
        """Add a vertex if it is not already present."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Set the line list of a station (duplicates removed, order preserved)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge):
        """Add an undirected edge, registering both endpoints as vertices."""
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not supported")
        if edge.distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def remove_edge(self, edge):
        """Remove an edge from the graph."""
        self._adjacency[edge.source].remove(edge)
        self._adjacency[edge.dest].remove(edge)
        self._edges.remove(edge)

    def adjacent_edges(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return self._adjacency.get(vertex, [])

    def neighbors(self, vertex):
        """Return the neighbouring vertices of ``vertex``."""
        return [edge.other(vertex) for edge in self.adjacent_edges(vertex)]

    def find_edges(self, u, v):
        """Return all edges directly connecting vertices ``u`` and ``v``."""
        return [edge for edge in self.adjacent_edges(u) if edge.other(u) == v]

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adjacency)

    def edges(self):
        """Return a list of all edges."""
        return list(self._edges)

    @property
    def num_vertices(self):
        return len(self._adjacency)

    @property
    def num_edges(self):
        return len(self._edges)

    def __len__(self):
        return self.num_vertices


class Network:
    """Subway network: a Graph plus station name <-> number mappings."""

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = {}
        self.load_warnings = []
        self._next_number = 0

    def add_station(self, name, lines=()):
        """Add a station (or merge lines into an existing one) and return its number."""
        if name in self.station_to_number:
            number = self.station_to_number[name]
            merged = list(self.graph.station_lines.get(name, []))
            for line in lines:
                if line not in merged:
                    merged.append(line)
            self.graph.set_station_lines(name, merged)
            return number

        number = self._next_number
        self._next_number += 1
        self.station_to_number[name] = number
        self.number_to_name[number] = name
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, lines)
        return number

    def has_station(self, name):
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number for a station name."""
        if name not in self.station_to_number:
            raise ValueError(f"Unknown station: {name}")
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_name[number]

    def lines_of(self, name):
        """Return the line names serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number, key=natural_sort_key)

    def all_line_names(self):
        """Return all known line names in natural order."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for edge in self.graph.edges():
            lines.add(edge.line)
        return sorted(lines, key=natural_sort_key)

    def add_connection(self, source_name, dest_name, distance, line):
        """Create an edge between two existing stations and return it."""
        u = self.number_of(source_name)
        v = self.number_of(dest_name)
        edge = Edge(u, v, distance, line)
        self.graph.add_edge(edge)
        return edge

    def connections_between(self, source_name, dest_name):
        """Return all edges directly connecting two stations."""
        if not (self.has_station(source_name) and self.has_station(dest_name)):
            return []
        return self.graph.find_edges(self.number_of(source_name), self.number_of(dest_name))

    def rename_station(self, old_name, new_name):
        """Rename a station; edges keep referencing the same station number."""
        if old_name not in self.station_to_number:
            raise ValueError(f"Unknown station: {old_name}")
        if new_name != old_name and new_name in self.station_to_number:
            raise ValueError(f"Station already exists: {new_name}")
        number = self.station_to_number.pop(old_name)
        self.station_to_number[new_name] = number
        self.number_to_name[number] = new_name
        lines = self.graph.station_lines.pop(old_name, [])
        self.graph.station_lines[new_name] = lines
