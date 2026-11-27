"""Data update mechanisms: adding lines, modifying stations, updating distances."""

from models import Edge


class DataManager:
    """Applies updates to a Graph while keeping it consistent."""

    def __init__(self, graph):
        self.graph = graph

    def add_line(self, line_name, station_names, distances_m):
        """Add a new line through an ordered list of stations.

        Args:
            line_name: name of the new line (must not already exist).
            station_names: ordered station names (at least two).
            distances_m: distances in meters between consecutive stations.

        Raises:
            ValueError: on invalid or conflicting input.
        """
        if not isinstance(line_name, str) or not line_name.strip():
            raise ValueError("line name must be a non-empty string")
        if line_name in self.graph.all_lines():
            raise ValueError(f"line already exists: {line_name}")
        if len(station_names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances_m) != len(station_names) - 1:
            raise ValueError("expected one distance per consecutive station pair")
        if len(set(station_names)) != len(station_names):
            raise ValueError("station names on a line must be unique")

        for name in station_names:
            if not self.graph.has_station(name):
                self.graph.add_station(name, self.graph.allocate_number(), [])
            self.graph.add_line_to_station(name, line_name)

        for i, distance in enumerate(distances_m):
            a = self.graph.number_of(station_names[i])
            b = self.graph.number_of(station_names[i + 1])
            self.graph.add_edge(Edge(a, b, distance, line_name))

    def modify_station(self, name, new_name=None, lines=None):
        """Change a station's name and/or its list of lines.

        Raises:
            KeyError: if the station does not exist.
            ValueError: if the new name is already used.
        """
        if not self.graph.has_station(name):
            raise KeyError(f"unknown station: {name}")
        if lines is not None:
            self.graph.set_station_lines(name, lines)
        if new_name and new_name != name:
            self.graph.rename_station(name, new_name)

    def update_distance(self, name_a, name_b, distance_m):
        """Update the distance between two adjacent stations.

        Raises:
            KeyError: if either station is unknown.
            ValueError: if the stations are not adjacent or distance is invalid.
        """
        if not self.graph.has_station(name_a) or not self.graph.has_station(name_b):
            raise KeyError("unknown station in distance update")
        a = self.graph.number_of(name_a)
        b = self.graph.number_of(name_b)
        edge = self.graph.edge_between(a, b)
        if edge is None:
            raise ValueError(f"stations are not adjacent: {name_a} - {name_b}")
        self.graph.add_edge(Edge(a, b, distance_m, edge.line))
