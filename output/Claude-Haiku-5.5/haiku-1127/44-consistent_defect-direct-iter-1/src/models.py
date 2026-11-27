"""Graph data structures and the Beijing Subway network model.

``Graph`` stores station numbers as nodes. Numbers are assigned by the
caller (``SubwayNetwork``), not by ``Graph`` itself. ``SubwayNetwork`` keeps
the mapping between official station names and numbers and offers name
resolution with fuzzy matching for user input.
"""

import difflib


class UnknownStationError(Exception):
    """Raised when a station name cannot be matched to any known station."""


class Edge:
    """A directed, weighted connection between two stations on one line.

    Attributes:
        source: Station number of the origin station.
        dest: Station number of the destination station.
        distance: Distance in meters (also used as the edge weight).
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance)."""
        return self.distance

    def __repr__(self):
        return (f"Edge({self.source!r} -> {self.dest!r}, "
                f"distance={self.distance}, line={self.line!r})")


class Graph:
    """Weighted directed graph implemented with adjacency lists.

    Each connection is usable only in its listed direction. Undirected
    connections must be added as two directed edges.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adjacency = {}
        self._nodes = set()
        self.station_lines = {}

    # ----- node management -------------------------------------------------
    def add_node(self, node):
        """Add a node (station number) to the graph if it is not present."""
        self._nodes.add(node)
        self._adjacency.setdefault(node, [])

    def has_node(self, node):
        """Return True if ``node`` is part of the graph."""
        return node in self._nodes

    def nodes(self):
        """Return a sorted list of all node numbers."""
        return sorted(self._nodes)

    @property
    def node_count(self):
        """Number of nodes in the graph."""
        return len(self._nodes)

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (by station name)."""
        self.station_lines[station_name] = list(lines)

    # ----- edge management -------------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge, creating its endpoint nodes if needed."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)

    def adjacent(self, node):
        """Return the outgoing edges of ``node`` (empty list if unknown).

        The returned list must not be modified by callers.
        """
        return self._adjacency.get(node, [])

    def edges(self):
        """Iterate over all edges in the graph."""
        for edge_list in self._adjacency.values():
            for edge in edge_list:
                yield edge

    @property
    def edge_count(self):
        """Number of directed edges in the graph."""
        return sum(len(edges) for edges in self._adjacency.values())


class SubwayNetwork:
    """Subway network model: station numbering, lines and the graph.

    Attributes:
        graph: The underlying ``Graph`` instance.
        station_to_number: dict mapping official station name -> number.
        number_to_station: dict mapping number -> official station name.
        line_names: Ordered list of all known line names.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.line_names = []

    # ----- internal helpers ------------------------------------------------
    def _register_line(self, line):
        """Remember a line name (keeping insertion order, no duplicates)."""
        if line and line not in self.line_names:
            self.line_names.append(line)

    def _ensure_station(self, name, line=None):
        """Return the number of ``name``, creating the station if needed."""
        if name not in self.station_to_number:
            number = len(self.number_to_station)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_node(number)
            self.graph.set_station_lines(name, [line] if line else [])
        return self.station_to_number[name]

    # ----- station management ----------------------------------------------
    def add_station(self, name, lines=()):
        """Add a station (or merge lines into an existing one).

        Returns:
            int: The station number.
        """
        name = str(name).strip()
        if not name:
            raise ValueError("Station name must not be empty")
        number = self._ensure_station(name)
        current = self.graph.station_lines[name]
        for line in lines:
            if line not in current:
                current.append(line)
            self._register_line(line)
        return number

    def set_station_lines(self, name, lines):
        """Replace the list of lines serving station ``name``."""
        number = self.get_number(name)
        del number  # validation only
        self.graph.set_station_lines(name, lines)
        for line in lines:
            self._register_line(line)

    def rename_station(self, old_name, new_name):
        """Rename a station. Edges reference numbers, so they stay valid."""
        new_name = str(new_name).strip()
        if not new_name:
            raise ValueError("New station name must not be empty")
        number = self.get_number(old_name)
        if new_name != old_name and new_name in self.station_to_number:
            raise ValueError(f"Station '{new_name}' already exists")
        lines = self.graph.station_lines.pop(old_name, [])
        del self.station_to_number[old_name]
        self.station_to_number[new_name] = number
        self.number_to_station[number] = new_name
        self.graph.station_lines[new_name] = lines

    def has_station(self, name):
        """Return True if a station with this official name exists."""
        return name in self.station_to_number

    def get_number(self, name):
        """Return the station number for an official name.

        Raises:
            UnknownStationError: If the station does not exist.
        """
        if name not in self.station_to_number:
            raise UnknownStationError(f"Unknown station: '{name}'")
        return self.station_to_number[name]

    def get_name(self, number):
        """Return the official station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return a sorted list of all official station names."""
        return sorted(self.station_to_number)

    def lines_of(self, name):
        """Return a copy of the list of lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    # ----- connection management -------------------------------------------
    def add_connection(self, source, dest, distance, line):
        """Add a directed connection between two stations.

        Stations that do not exist yet are created and assigned ``line``.
        """
        distance = int(distance)
        if distance < 0:
            raise ValueError("Distance must not be negative")
        src = self._ensure_station(str(source).strip(), line)
        dst = self._ensure_station(str(dest).strip(), line)
        self.graph.add_edge(Edge(src, dst, distance, line))
        self._register_line(line)

    # ----- name resolution -------------------------------------------------
    def resolve_station(self, text):
        """Map user input to an official station name.

        Matching order: exact name, case-insensitive name, then the nearest
        station name by string similarity (cutoff 0.5).

        Returns:
            tuple: (official_name, matched_fuzzy) where ``matched_fuzzy`` is
            True when the name was matched to the nearest station instead of
            matching exactly.

        Raises:
            UnknownStationError: If no station is reasonably close.
        """
        cleaned = " ".join(str(text).split())
        if not cleaned:
            raise UnknownStationError("Station name is empty")
        if cleaned in self.station_to_number:
            return cleaned, False

        lowered = {}
        for name in self.station_to_number:
            lowered.setdefault(name.lower(), name)
        if cleaned.lower() in lowered:
            return lowered[cleaned.lower()], False

        matches = difflib.get_close_matches(cleaned.lower(), list(lowered), n=1, cutoff=0.5)
        if matches:
            return lowered[matches[0]], True
        raise UnknownStationError(f"Station '{cleaned}' does not exist")


def build_network(data):
    """Build a ``SubwayNetwork`` from the parsed subway data dictionary.

    Args:
        data: dict with "stations" and "connections" lists (see data_loader).

    Returns:
        SubwayNetwork: The populated network model.
    """
    network = SubwayNetwork()
    for station in data.get("stations", []):
        network.add_station(station["name"], station.get("lines", []))
    for conn in data.get("connections", []):
        network.add_connection(conn["source"], conn["dest"],
                               conn["distance"], conn["line"])
    return network
