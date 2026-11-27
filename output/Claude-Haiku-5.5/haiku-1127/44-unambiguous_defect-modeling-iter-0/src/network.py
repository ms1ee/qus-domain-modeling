"""
Subway network construction and data management.

This module assigns integer station numbers, builds the ``Graph`` from the
raw dataset, handles transfer-station information, and offers update
operations (adding lines, modifying stations, updating distances).
"""

from dataclasses import dataclass, field

from models import Edge, Graph


@dataclass
class Station:
    """Read-only view of a station."""

    station_id: str
    name: str
    lines: list = field(default_factory=list)

    @property
    def is_transfer_station(self):
        """A station served by more than one line is an interchange station."""
        return len(self.lines) > 1


@dataclass
class Line:
    """A subway line with its ordered station names."""

    name: str
    stations: list = field(default_factory=list)


class SubwayNetwork:
    """
    The Beijing Subway network: station registry plus weighted graph.

    Attributes:
        graph (Graph): The weighted undirected graph of stations.
        station_to_number (dict): Mapping station name -> station number.
        number_to_station (list): Station names indexed by station number.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = []

    # ------------------------------------------------------------------
    # Station registry
    # ------------------------------------------------------------------
    def _ensure_station(self, name):
        """Return the number of a station, registering it if necessary."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.number_to_station)
        self.number_to_station.append(name)
        self.station_to_number[name] = number
        self.graph.add_node(number)
        self.graph.station_lines.setdefault(name, [])
        return number

    def add_station(self, name, lines=()):
        """
        Add a station (or merge lines into an existing station).

        Returns:
            int: The station number.
        """
        name = str(name).strip()
        if not name:
            raise ValueError("Station name must not be empty")
        number = self._ensure_station(name)
        merged = list(self.graph.station_lines.get(name, []))
        for line in lines:
            if line not in merged:
                merged.append(line)
        self.graph.set_station_lines(name, merged)
        return number

    def has_station(self, name):
        """Return True if the station exists in the network."""
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number for a station name."""
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station: {name}")
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all station names in registration order."""
        return list(self.number_to_station)

    def get_station(self, name):
        """Return a Station view for the given name."""
        if not self.has_station(name):
            raise KeyError(f"Unknown station: {name}")
        number = self.station_to_number[name]
        return Station(station_id=str(number), name=name,
                       lines=list(self.graph.station_lines.get(name, [])))

    def stations(self):
        """Return Station views for all stations."""
        return [self.get_station(name) for name in self.number_to_station]

    def is_transfer_station(self, name):
        """Return True if the station is served by more than one line."""
        return len(self.graph.station_lines.get(name, [])) > 1

    # ------------------------------------------------------------------
    # Connections and lines
    # ------------------------------------------------------------------
    def add_connection(self, source, dest, distance, line):
        """
        Add a direct connection between two stations on a line.

        Returns:
            Edge: The created edge.
        """
        if source == dest:
            raise ValueError("A station cannot be connected to itself")
        distance = float(distance)
        if distance < 0:
            raise ValueError("Connection distance must be non-negative")
        a = self._ensure_station(source)
        b = self._ensure_station(dest)
        for name in (source, dest):
            lines = list(self.graph.station_lines.get(name, []))
            if line not in lines:
                lines.append(line)
                self.graph.set_station_lines(name, lines)
        edge = Edge(a, b, distance, line)
        self.graph.add_edge(edge)
        return edge

    def line_names(self):
        """Return a sorted list of every line name present in the network."""
        names = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        for edge in self.graph.edges():
            names.add(edge.line)
        return sorted(names)

    def stations_on_line(self, line):
        """Return the names of stations served by a line, in registration order."""
        return [name for name in self.number_to_station
                if line in self.graph.station_lines.get(name, [])]

    def get_line(self, line):
        """Return a Line view with the stations served by the line."""
        return Line(name=line, stations=self.stations_on_line(line))

    def add_line(self, line_name, station_names, distances):
        """
        Add a new line by specifying its ordered stations and segment distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line.
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: If the input sequence is inconsistent.
        """
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        for name in station_names:
            self.add_station(name, [line_name])
        for i, distance in enumerate(distances):
            self.add_connection(station_names[i], station_names[i + 1], distance, line_name)

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------
    def update_station(self, old_name, new_name=None, lines=None):
        """
        Rename a station and/or replace its line affiliations.

        Returns:
            str: The (possibly new) station name.
        """
        if old_name not in self.station_to_number:
            raise KeyError(f"Unknown station: {old_name}")
        number = self.station_to_number[old_name]
        target = old_name
        if new_name and new_name != old_name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station already exists: {new_name}")
            del self.station_to_number[old_name]
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            self.graph.station_lines[new_name] = self.graph.station_lines.pop(old_name, [])
            target = new_name
        if lines is not None:
            self.graph.set_station_lines(target, lines)
        return target

    def update_distance(self, a, b, distance):
        """
        Update the distance between two directly connected stations.

        Returns:
            int: Number of edges updated.

        Raises:
            KeyError: If either station is unknown or no connection exists.
        """
        if distance < 0:
            raise ValueError("Distance must be non-negative")
        na = self.number_of(a)
        nb = self.number_of(b)
        count = self.graph.update_edge_distance(na, nb, distance)
        if count == 0:
            raise KeyError(f"No direct connection between {a} and {b}")
        return count

    def to_dict(self):
        """Export the network in the same structure as subway_data.json."""
        stations = [{"name": name, "lines": list(self.graph.station_lines.get(name, []))}
                    for name in self.number_to_station]
        connections = [{
            "source": self.name_of(edge.source),
            "dest": self.name_of(edge.dest),
            "distance": int(round(edge.distance)),
            "line": edge.line,
        } for edge in self.graph.edges()]
        return {"stations": stations, "connections": connections}


def build_network(data):
    """
    Build a SubwayNetwork from the parsed subway dataset.

    Args:
        data: dict with "stations" ([{name, lines}]) and
              "connections" ([{source, dest, distance, line}]).

    Returns:
        SubwayNetwork: The constructed network.

    Raises:
        ValueError: If the dataset is malformed.
    """
    if not isinstance(data, dict):
        raise ValueError("Subway dataset must be a dictionary")
    network = SubwayNetwork()
    try:
        for item in data.get("stations", []):
            network.add_station(item["name"], item.get("lines", []))
        for item in data.get("connections", []):
            network.add_connection(item["source"], item["dest"], item["distance"], item["line"])
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed subway dataset entry: {exc}") from exc
    return network
