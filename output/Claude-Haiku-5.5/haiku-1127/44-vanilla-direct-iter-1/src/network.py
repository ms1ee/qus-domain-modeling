"""Subway network model: station registry, line data and data updates.

``SubwayNetwork`` is built from the dictionary loaded from ``subway_data.json``.
It assigns station numbers, maintains the ``Graph``, and offers name
standardization and data-maintenance operations (adding lines, renaming
stations, updating distances).
"""

from models import Edge, Graph


class StationNotFoundError(ValueError):
    """Raised when a station name is not part of the network."""


def _clean(value):
    """Normalize a text value: convert to str and collapse whitespace."""
    if value is None:
        return ""
    return " ".join(str(value).split())


class SubwayNetwork:
    """Subway network composed of stations (vertices) and connections (edges).

    Attributes:
        graph: The ``models.Graph`` holding adjacency data and station lines.
        station_to_number: Mapping of station name to station number.
        number_to_station: Mapping of station number to station name.
    """

    def __init__(self, data):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._line_order = []
        self._next_number = 0
        self._build(data)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build(self, data):
        """Populate stations, numbers, lines and edges from the raw dataset."""
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a dictionary")

        for station in data.get("stations", []):
            name = _clean(station.get("name"))
            if not name:
                raise ValueError("Station entry without a name")
            lines = [_clean(line) for line in station.get("lines", [])]
            lines = [line for line in lines if line]
            for line in lines:
                self._register_line(line)
            self._add_station(name, lines)

        for conn in data.get("connections", []):
            src = _clean(conn.get("source"))
            dst = _clean(conn.get("dest"))
            line = _clean(conn.get("line"))
            if not src or not dst or not line:
                raise ValueError(f"Malformed connection entry: {conn}")
            distance = int(conn.get("distance"))
            self._register_line(line)
            # Stations referenced only by connections are registered on the fly.
            self._add_station(src, [line])
            self._add_station(dst, [line])
            self._add_edge(src, dst, distance, line)

    def _register_line(self, line):
        """Remember a line name, preserving first-appearance order."""
        if line not in self._line_order:
            self._line_order.append(line)

    def _add_station(self, name, lines):
        """Create a station if needed and return its station number."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = self._next_number
        self._next_number += 1
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, lines)
        return number

    def _add_edge(self, src, dst, distance, line):
        """Add an undirected connection between two registered stations."""
        u = self.station_to_number[src]
        v = self.station_to_number[dst]
        self.graph.add_edge(Edge(u, v, distance, line))

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def has_station(self, name):
        """Return True if ``name`` is an exact station name in the network."""
        return name in self.station_to_number

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def get_number(self, name):
        """Return the station number for ``name``.

        Raises:
            StationNotFoundError: If the station does not exist.
        """
        try:
            return self.station_to_number[name]
        except KeyError as exc:
            raise StationNotFoundError(f"Station '{name}' does not exist") from exc

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return a copy of the list of lines serving station ``name``."""
        return list(self.graph.station_lines.get(name, []))

    def line_names(self):
        """Return all line names in first-appearance order."""
        return list(self._line_order)

    def transfer_stations(self):
        """Return sorted names of stations served by more than one line."""
        return sorted(name for name in self.station_to_number if len(self.lines_of(name)) > 1)

    def standardize_station_name(self, raw):
        """Map user input to an official station name.

        Matching is tolerant of surrounding whitespace, letter case and the
        optional trailing "站" character.

        Returns:
            str or None: The official station name, or None if no station matches.
        """
        text = _clean(raw)
        if not text:
            return None
        if text in self.station_to_number:
            return text
        alternates = []
        if text.endswith("站"):
            alternates.append(text[:-1])
        else:
            alternates.append(text + "站")
        for candidate in alternates:
            if candidate in self.station_to_number:
                return candidate
        folded = text.casefold()
        for name in self.station_to_number:
            if name.casefold() == folded:
                return name
        return None

    def line_stations(self, line):
        """Return the stations of ``line`` in travel order.

        The order is derived by walking the line's connections starting from
        an end station. Stations on unexpected branches are appended at the end.
        """
        adjacency = {}
        for edge in self.graph.edges():
            if edge.line != line:
                continue
            adjacency.setdefault(edge.source, []).append(edge.dest)
            adjacency.setdefault(edge.dest, []).append(edge.source)
        if not adjacency:
            return []

        start = next((n for n, nbrs in adjacency.items() if len(set(nbrs)) <= 1), next(iter(adjacency)))
        order = [start]
        visited = {start}
        current = start
        while True:
            candidates = [n for n in adjacency[current] if n not in visited]
            if not candidates:
                break
            current = candidates[0]
            visited.add(current)
            order.append(current)
        for number in adjacency:
            if number not in visited:
                order.append(number)
        return [self.number_to_station[n] for n in order]

    # ------------------------------------------------------------------
    # Data maintenance
    # ------------------------------------------------------------------
    def add_line(self, line, station_names, distances):
        """Add a new line with its ordered stations and inter-station distances.

        Stations that do not exist yet are created. Existing stations gain the
        new line in their line list.

        Args:
            line: Name of the new line.
            station_names: Ordered list of station names along the line.
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: On duplicate line names, too few stations, a mismatched
                number of distances, or non-positive distances.
        """
        line = _clean(line)
        if not line:
            raise ValueError("Line name cannot be empty")
        if line in self._line_order:
            raise ValueError(f"Line '{line}' already exists")
        names = [_clean(name) for name in station_names]
        if len(names) < 2 or any(not name for name in names):
            raise ValueError("A line needs at least two named stations")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        checked = []
        for value in distances:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("Distances must be positive integers (meters)")
            checked.append(value)

        self._register_line(line)
        for name in names:
            self._add_station(name, [])
            if line not in self.lines_of(name):
                self.graph.set_station_lines(name, self.lines_of(name) + [line])
        for a, b, distance in zip(names, names[1:], checked):
            self._add_edge(a, b, distance, line)

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its served lines.

        Args:
            name: Current official station name.
            new_name: Optional new name for the station.
            lines: Optional full replacement list of lines serving the station.

        Returns:
            str: The (possibly renamed) station name.

        Raises:
            StationNotFoundError: If ``name`` does not exist.
            ValueError: If ``new_name`` is already used by another station.
        """
        if not self.has_station(name):
            raise StationNotFoundError(f"Station '{name}' does not exist")
        number = self.station_to_number[name]

        new_name = _clean(new_name) if new_name is not None else None
        if new_name and new_name != name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            del self.station_to_number[name]
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            current_lines = self.graph.station_lines.pop(name, [])
            self.graph.set_station_lines(new_name, current_lines)
            name = new_name

        if lines is not None:
            cleaned = [_clean(line) for line in lines]
            cleaned = [line for line in cleaned if line]
            for line in cleaned:
                self._register_line(line)
            self.graph.set_station_lines(name, cleaned)
        return name

    def update_distance(self, src_name, dst_name, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        Returns:
            int: Number of connections updated.

        Raises:
            StationNotFoundError: If a station does not exist.
            ValueError: If the distance is not a positive integer or no
                connection exists between the stations.
        """
        u = self.get_number(src_name)
        v = self.get_number(dst_name)
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            raise ValueError("Distance must be a positive integer (meters)")
        count = self.graph.update_distance(u, v, distance, line)
        if count == 0:
            raise ValueError(f"No connection found between '{src_name}' and '{dst_name}'")
        return count
