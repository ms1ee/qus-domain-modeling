"""Graph-based data model of the Beijing Subway network.

Station names are mapped to integer station numbers by SubwayNetwork, and the
weighted undirected graph is stored in Graph using those numbers.
"""

from collections import deque


def _clean(value):
    """Normalize a text value: convert to str, collapse whitespace, strip ends."""
    if value is None:
        return ""
    return " ".join(str(value).split())


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: inter-station distance in meters (also used as weight).
        line: name of the subway line operating this connection.
    """

    def __init__(self, source, dest, distance, line):
        distance = float(distance)
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to the distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller. The graph also keeps a
    mapping ``station_lines`` from station name to the lines serving it.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self._edge_keys = set()
        self.station_lines = {}

    def add_node(self, vertex):
        """Add a node (station number) if it is not already present."""
        self._adjacency.setdefault(vertex, [])

    def has_node(self, vertex):
        """Return True if the node exists in the graph."""
        return vertex in self._adjacency

    def add_edge(self, edge):
        """Add an undirected edge.

        Duplicate edges (same endpoints and same line) are ignored.

        Returns:
            True if the edge was added, False if it was a duplicate.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
        if key in self._edge_keys:
            return False
        self._edge_keys.add(key)
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)
        return True

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (keyed by station name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the list of lines serving a station name."""
        return list(self.station_lines.get(station_name, []))

    def adjacent(self, vertex):
        """Return the edges incident to ``vertex`` (read-only view)."""
        return self._adjacency.get(vertex, ())

    def nodes(self):
        """Return the list of node identifiers."""
        return list(self._adjacency.keys())

    def edges(self):
        """Return the list of unique edges."""
        return list(self._edges)

    @property
    def node_count(self):
        return len(self._adjacency)

    @property
    def edge_count(self):
        return len(self._edges)

    def connected_components(self):
        """Return the connected components as a list of sets of node identifiers."""
        seen = set()
        components = []
        for start in self._adjacency:
            if start in seen:
                continue
            component = set()
            queue = deque([start])
            seen.add(start)
            while queue:
                vertex = queue.popleft()
                component.add(vertex)
                for edge in self._adjacency[vertex]:
                    neighbour = edge.other(vertex)
                    if neighbour not in seen:
                        seen.add(neighbour)
                        queue.append(neighbour)
            components.append(component)
        return components


def _normalize_key(text):
    """Key used for case- and space-insensitive name matching."""
    return "".join(text.split()).casefold()


class SubwayNetwork:
    """The Beijing Subway network: stations, lines, connections and graph.

    Built from the raw dataset dict (see data_loader.load_subway_data).
    Station numbers start at 1 and follow the order of the stations list.
    """

    def __init__(self, data):
        if not isinstance(data, dict):
            raise TypeError("Network data must be a dict")
        self.name = "Beijing Subway"
        self.data_source = "subway_data.json"
        self.version = str(data.get("version", "1.0"))
        self._station_lines = {}
        self._name_to_number = {}
        self._number_to_name = {}
        self._station_lookup = {}
        self._line_lookup = {}
        self.connections = []
        self.graph = Graph()
        self._build(data)

    def _build(self, data):
        """Populate stations, connections, station numbers and the graph."""
        for entry in data.get("stations", []):
            name = _clean(entry.get("name"))
            if not name:
                continue
            lines = [_clean(line) for line in entry.get("lines", [])]
            self._station_lines.setdefault(name, [])
            for line in lines:
                if line and line not in self._station_lines[name]:
                    self._station_lines[name].append(line)

        for conn in data.get("connections", []):
            src = _clean(conn.get("source"))
            dst = _clean(conn.get("dest"))
            line = _clean(conn.get("line"))
            if not src or not dst or not line:
                raise ValueError(f"Malformed connection record: {conn}")
            try:
                distance = float(conn.get("distance"))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid distance in connection {src}-{dst}") from exc
            for name in (src, dst):
                if name not in self._station_lines:
                    self._station_lines[name] = [line]
            self.connections.append({
                "source": src,
                "dest": dst,
                "distance": distance,
                "line": line,
            })

        for number, name in enumerate(self._station_lines, start=1):
            self._name_to_number[name] = number
            self._number_to_name[number] = name
            self.graph.set_station_lines(name, self._station_lines[name])
            self.graph.add_node(number)

        for conn in self.connections:
            edge = Edge(
                self._name_to_number[conn["source"]],
                self._name_to_number[conn["dest"]],
                conn["distance"],
                conn["line"],
            )
            self.graph.add_edge(edge)

        self._station_lookup = {_normalize_key(name): name for name in self._station_lines}
        self._line_lookup = {_normalize_key(line): line for line in self.line_names()}

    # ----- station queries -------------------------------------------------

    def station_names(self):
        """Return all official station names in numbering order."""
        return list(self._station_lines.keys())

    @property
    def station_count(self):
        return len(self._station_lines)

    def has_station(self, name):
        return name in self._station_lines

    def get_number(self, name):
        """Return the station number of a (standardized) station name."""
        if name not in self._name_to_number:
            raise KeyError(f"Unknown station: {name}")
        return self._name_to_number[name]

    def get_name(self, number):
        """Return the station name for a station number."""
        if number not in self._number_to_name:
            raise KeyError(f"Unknown station number: {number}")
        return self._number_to_name[number]

    def get_station_lines(self, name):
        """Return a copy of the list of lines serving a station."""
        return list(self._station_lines.get(name, []))

    def transfer_stations(self):
        """Return names of stations served by more than one line."""
        return [name for name, lines in self._station_lines.items() if len(lines) > 1]

    def standardize_name(self, raw):
        """Map a user-entered station name to the official name.

        Matching ignores case, whitespace and a trailing "站" suffix.

        Returns:
            the official station name, or None if no station matches.
        """
        text = _clean(raw)
        if not text:
            return None
        if text in self._station_lines:
            return text
        candidates = [text]
        if text.endswith("站"):
            candidates.append(text[:-1].strip())
        for candidate in candidates:
            key = _normalize_key(candidate)
            if key and key in self._station_lookup:
                return self._station_lookup[key]
        return None

    # ----- line queries ----------------------------------------------------

    def line_names(self):
        """Return sorted names of all lines appearing in stations or connections."""
        names = set()
        for lines in self._station_lines.values():
            names.update(lines)
        for conn in self.connections:
            names.add(conn["line"])
        return sorted(names)

    def canonical_line(self, raw):
        """Return the official line name matching ``raw`` (case/space-insensitive), or None."""
        key = _normalize_key(_clean(raw))
        return self._line_lookup.get(key)

    def stations_on_line(self, line):
        """Return names of stations whose line list contains ``line``."""
        return [name for name, lines in self._station_lines.items() if line in lines]
