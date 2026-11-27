"""Subway network data management: station mapping, graph construction and updates."""

from errors import DataError, StationNotFoundError
from models import Edge, Graph


class SubwayNetwork:
    """Holds the Beijing Subway network as a weighted graph plus name/number mappings.

    Attributes:
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        graph: The Graph holding adjacency lists and station line data.
        undeclared_stations: set of station names referenced by connections but
            missing from the station list (used by integrity checks).
    """

    def __init__(self, data):
        if not isinstance(data, dict):
            raise DataError("Subway data must be a dictionary")
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.undeclared_stations = set()
        self._connections = []
        self._edge_index = {}
        self._next_number = 1
        self._build(data)

    # ----- construction --------------------------------------------------------
    def _build(self, data):
        """Populate stations and connections from the raw data dictionary."""
        stations = data.get("stations", [])
        connections = data.get("connections", [])
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise DataError("'stations' and 'connections' must be lists")

        declared = set()
        for item in stations:
            if not isinstance(item, dict) or not item.get("name"):
                raise DataError("Each station entry needs a non-empty 'name'")
            name = item["name"]
            declared.add(name)
            self._ensure_station(name, item.get("lines", []))

        for conn in connections:
            try:
                source = conn["source"]
                dest = conn["dest"]
                distance = conn["distance"]
                line = conn["line"]
            except (KeyError, TypeError) as exc:
                raise DataError(f"Malformed connection entry: {conn!r}") from exc
            for name in (source, dest):
                if name not in declared:
                    self.undeclared_stations.add(name)
            self.add_connection(source, dest, distance, line)

    def _ensure_station(self, name, lines=()):
        """Create the station if needed, merge in its lines, and return its number."""
        if not isinstance(name, str) or not name.strip():
            raise DataError("Station names must be non-empty strings")
        if name not in self.station_to_number:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
        merged = self.graph.get_station_lines(name)
        for line in lines:
            if line not in merged:
                merged.append(line)
        self.graph.set_station_lines(name, merged)
        return self.station_to_number[name]

    @staticmethod
    def _edge_key(a, b, line):
        """Canonical key for an undirected connection on a given line (by numbers)."""
        return (min(a, b), max(a, b), line)

    def add_connection(self, source, dest, distance, line):
        """Add a connection between two stations.

        Returns:
            True if a new connection was added, False if it already existed.

        Raises:
            DataError: If the distance or line is invalid.
        """
        if not line:
            raise DataError("Connections must specify a line")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise DataError(f"Invalid distance {distance!r} for {source} - {dest}")
        src = self._ensure_station(source, [line])
        dst = self._ensure_station(dest, [line])
        if src == dst:
            raise DataError(f"A station cannot connect to itself: {source}")
        key = self._edge_key(src, dst, line)
        if key in self._edge_index:
            return False
        edge = Edge(src, dst, distance, line)
        self.graph.add_edge(edge)
        self._edge_index[key] = edge
        self._connections.append({"source": source, "dest": dest,
                                  "distance": distance, "line": line})
        return True

    # ----- queries -------------------------------------------------------------
    def station_count(self):
        """Return the number of stations in the network."""
        return len(self.station_to_number)

    def station_names(self):
        """Return a sorted list of all station names."""
        return sorted(self.station_to_number)

    def line_names(self):
        """Return a sorted list of all subway line names."""
        names = {conn["line"] for conn in self._connections}
        for lines in self.graph.station_lines.values():
            names.update(lines)
        return sorted(names)

    def stations_on_line(self, line):
        """Return a sorted list of station names served by `line`."""
        return sorted(name for name, lines in self.graph.station_lines.items() if line in lines)

    def station_lines(self, name):
        """Return the list of lines serving a station."""
        return self.graph.get_station_lines(name)

    def connections(self):
        """Return a copy of the connection records."""
        return [dict(conn) for conn in self._connections]

    def standardize_name(self, raw):
        """Map user input to an official station name.

        Matching is case-insensitive and tolerates surrounding whitespace and a
        trailing Chinese character '站'.

        Returns:
            The official station name, or None if no station matches.
        """
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if not text:
            return None
        if text in self.station_to_number:
            return text
        if text.endswith("站"):
            trimmed = text[:-1].strip()
            if trimmed in self.station_to_number:
                return trimmed
        lowered = text.lower()
        for name in self.station_to_number:
            if name.lower() == lowered:
                return name
        return None

    def number_of(self, name):
        """Return the station number for an official station name.

        Raises:
            StationNotFoundError: If the station is unknown.
        """
        if name not in self.station_to_number:
            raise StationNotFoundError(name)
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number.

        Raises:
            StationNotFoundError: If the number is unknown.
        """
        if number not in self.number_to_station:
            raise StationNotFoundError(str(number), f"Station number {number} does not exist")
        return self.number_to_station[number]

    # ----- data updates --------------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line as an ordered sequence of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            stations: Ordered list of station names (at least two).
            distances: Distances in meters between consecutive stations
                (len(stations) - 1 values).

        Raises:
            DataError: If the input is invalid. No change is made on failure.
        """
        if not line_name or not isinstance(line_name, str):
            raise DataError("Line name must be a non-empty string")
        if line_name in self.line_names():
            raise DataError(f"Line '{line_name}' already exists")
        if len(stations) < 2:
            raise DataError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise DataError("Number of distances must equal number of stations minus one")
        if len(set(stations)) != len(stations):
            raise DataError("A line cannot visit the same station twice")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise DataError(f"Invalid distance {d!r}")
        for i, d in enumerate(distances):
            self.add_connection(stations[i], stations[i + 1], d, line_name)

    def modify_station(self, name, new_name=None, add_lines=(), remove_lines=()):
        """Modify a station's name and/or the lines serving it.

        Raises:
            StationNotFoundError: If the station does not exist.
            DataError: If the new name is taken, or a removed line still has
                connections at this station.
        """
        number = self.number_of(name)
        remove_set = set(remove_lines)
        incident_lines = {edge.line for edge in self.graph.adjacent(number)}
        blocked = sorted(remove_set & incident_lines)
        if blocked:
            raise DataError(f"Cannot remove lines {blocked} while connections remain at '{name}'")

        lines = [line for line in self.station_lines(name) if line not in remove_set]
        for line in add_lines:
            if line not in lines:
                lines.append(line)

        current = name
        if new_name and new_name.strip() and new_name.strip() != name:
            target = new_name.strip()
            if target in self.station_to_number:
                raise DataError(f"Station '{target}' already exists")
            del self.station_to_number[name]
            self.station_to_number[target] = number
            self.number_to_station[number] = target
            self.graph.station_lines.pop(name, None)
            for conn in self._connections:
                if conn["source"] == name:
                    conn["source"] = target
                if conn["dest"] == name:
                    conn["dest"] = target
            current = target
        self.graph.set_station_lines(current, lines)

    def update_distance(self, name_a, name_b, distance, line=None):
        """Update the distance between two directly connected stations.

        Args:
            name_a, name_b: Station names of the connection endpoints.
            distance: New distance in meters (positive number).
            line: Optional line name to restrict the update to one line.

        Returns:
            Number of connections updated.

        Raises:
            DataError: If the distance is invalid or no matching connection exists.
        """
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise DataError(f"Invalid distance {distance!r}")
        a = self.number_of(name_a)
        b = self.number_of(name_b)
        edges = [edge for edge in self.graph.edges_between(a, b)
                 if line is None or edge.line == line]
        if not edges:
            raise DataError(f"No connection between '{name_a}' and '{name_b}'"
                            + (f" on line '{line}'" if line else ""))
        for edge in edges:
            edge.distance = distance
        for conn in self._connections:
            if {conn["source"], conn["dest"]} == {name_a, name_b} and (line is None or conn["line"] == line):
                conn["distance"] = distance
        return len(edges)

    def to_data_dict(self):
        """Export the current network in the same structure as subway_data.json."""
        return {
            "stations": [{"name": name, "lines": self.station_lines(name)}
                         for name in self.station_names()],
            "connections": self.connections(),
        }
