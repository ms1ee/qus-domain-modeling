"""Core data models: graph edges, the weighted undirected subway graph,
transfer records, and computed routes."""


class Edge:
    """A weighted, line-labelled connection between two station nodes.

    Attributes:
        source: station number of the starting node.
        dest: station number of the ending node.
        distance: physical distance in meters (also used as the edge weight).
        line: name of the subway line the connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest path algorithms (equals the distance)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source!r}->{self.dest!r}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Nodes are station numbers assigned by the caller (e.g. DataManager).
    Every undirected connection is stored as two directed Edge objects, one in
    each endpoint's adjacency list, so that adjacency lookups are O(degree).

    Attributes:
        station_lines: mapping from station name to the list of line names
            serving that station (used to detect transfer stations).
    """

    def __init__(self):
        self._adjacency = {}
        self.station_lines = {}
        self._edge_count = 0

    @property
    def node_count(self):
        """Number of nodes (stations) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of undirected edges (connections) in the graph."""
        return self._edge_count

    def add_node(self, node):
        """Add a node if it does not already exist."""
        self._adjacency.setdefault(node, [])

    def has_node(self, node):
        """Return True if the node exists in the graph."""
        return node in self._adjacency

    def nodes(self):
        """Return a list of all node identifiers."""
        return list(self._adjacency.keys())

    def set_station_lines(self, station_name, lines):
        """Set (replace) the list of lines that serve a station."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected connection described by ``edge``.

        Both directions are stored so the graph behaves as undirected.

        Raises:
            ValueError: if the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError(f"Self-loop edges are not allowed (station {edge.source})")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(Edge(edge.dest, edge.source, edge.distance, edge.line))
        self._edge_count += 1

    def adjacent(self, node):
        """Return the list of directed edges leaving ``node`` (read-only use)."""
        return self._adjacency.get(node, [])

    def get_edges_between(self, u, v):
        """Return the directed edges going from ``u`` to ``v``."""
        return [edge for edge in self._adjacency.get(u, []) if edge.dest == v]

    def update_distance(self, u, v, distance):
        """Update the distance of the connection between ``u`` and ``v``.

        Returns:
            True if at least one edge was updated, False otherwise.
        """
        edges = self.get_edges_between(u, v) + self.get_edges_between(v, u)
        for edge in edges:
            edge.distance = distance
        return bool(edges)


class Transfer:
    """A transfer event: passengers change from one line to another at a station."""

    def __init__(self, station_name, from_line, to_line):
        self.station_name = station_name
        self.from_line = from_line
        self.to_line = to_line

    def to_dict(self):
        """Return a JSON-serialisable representation of the transfer."""
        return {
            "station": self.station_name,
            "from_line": self.from_line,
            "to_line": self.to_line,
        }


class Route:
    """The result of a path query, ready for reporting."""

    def __init__(self, start_name, end_name, mode, max_transfers, line_preference,
                 stations, segments, transfers, total_distance_m, fare,
                 estimated_time_minutes):
        self.start_name = start_name
        self.end_name = end_name
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference
        self.stations = list(stations)
        self.segments = list(segments)          # [{"line": str, "stations": [str]}]
        self.transfers = list(transfers)        # [Transfer]
        self.total_distance_m = total_distance_m
        self.fare = fare
        self.estimated_time_minutes = estimated_time_minutes
        self.transfer_count = len(self.transfers)
        self.lines = []
        for segment in self.segments:
            if segment["line"] not in self.lines:
                self.lines.append(segment["line"])
