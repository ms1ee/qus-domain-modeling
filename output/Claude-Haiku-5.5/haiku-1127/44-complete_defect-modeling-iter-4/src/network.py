"""Subway network management: station registry, graph construction and data updates.

``SubwayNetwork`` owns the station-to-number mapping (``station_to_number``),
the weighted ``Graph`` and the operations used by the data management module
(adding lines, modifying stations, updating distances and persisting data).
"""

from typing import Dict, List, Optional

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph


class SubwayNetwork:
    """Beijing Subway network built from the ``subway_data.json`` dataset.

    Attributes:
        graph: The weighted undirected graph of stations.
        station_to_number: Mapping of official station name to station number.
    """

    def __init__(self, data: Optional[dict] = None) -> None:
        if data is None:
            data = load_subway_data(DATA_FILE_PATH)
        self.graph = Graph()
        self.station_to_number: Dict[str, str] = {}
        self._number_to_name: Dict[str, str] = {}
        self._station_order: List[str] = []
        self._counter = 0
        self._build(data)

    @classmethod
    def from_file(cls, path: str = DATA_FILE_PATH) -> "SubwayNetwork":
        """Create a network by loading the dataset from ``path``."""
        return cls(load_subway_data(path))

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    def _build(self, data: dict) -> None:
        """Populate the graph from the raw dataset."""
        for station in data.get("stations", []):
            name = str(station["name"]).strip()
            lines = [str(line).strip() for line in station.get("lines", [])]
            self._register_station(name)
            merged = self.graph.get_station_lines(name)
            for line in lines:
                if line not in merged:
                    merged.append(line)
            self.graph.set_station_lines(name, merged)

        for conn in data.get("connections", []):
            self._add_edge_by_name(
                str(conn["source"]).strip(),
                str(conn["dest"]).strip(),
                conn["distance"],
                str(conn["line"]).strip(),
            )

    def _new_number(self) -> str:
        """Generate the next unique station number."""
        self._counter += 1
        return f"S{self._counter:04d}"

    def _register_station(self, name: str) -> str:
        """Ensure a station exists and return its station number."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = self._new_number()
        self.station_to_number[name] = number
        self._number_to_name[number] = name
        self._station_order.append(name)
        self.graph.add_vertex(number)
        self.graph.station_lines.setdefault(name, [])
        return number

    def _add_edge_by_name(self, source: str, dest: str, distance: float, line: str) -> Edge:
        """Create an edge between two stations identified by name."""
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            raise ValueError(f"Distance between '{source}' and '{dest}' must be numeric")
        number_a = self._register_station(source)
        number_b = self._register_station(dest)
        edge = Edge(number_a, number_b, distance, line)
        self.graph.add_edge(edge)
        return edge

    # ------------------------------------------------------------------
    # Lookup API
    # ------------------------------------------------------------------
    def station_names(self) -> List[str]:
        """Return all official station names in registration order."""
        return list(self._station_order)

    def station_exists(self, name: str) -> bool:
        """Return True if the exact station name is registered."""
        return name in self.station_to_number

    def number_of(self, name: str) -> str:
        """Return the station number for a station name.

        Raises:
            KeyError: If the station does not exist.
        """
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station '{name}'")
        return self.station_to_number[name]

    def name_of(self, number: str) -> str:
        """Return the station name for a station number.

        Raises:
            KeyError: If the station number does not exist.
        """
        if number not in self._number_to_name:
            raise KeyError(f"Unknown station number '{number}'")
        return self._number_to_name[number]

    def standardize_name(self, name: str) -> Optional[str]:
        """Map user input to the official station name.

        Matching ignores surrounding whitespace, inner spaces and letter case.

        Returns:
            The official station name, or None if no station matches.
        """
        if not name:
            return None
        cleaned = name.strip()
        if cleaned in self.station_to_number:
            return cleaned
        key = _normalize(cleaned)
        for official in self._station_order:
            if _normalize(official) == key:
                return official
        return None

    def lines_of_station(self, name: str) -> List[str]:
        """Return the lines serving a station (copy)."""
        return self.graph.get_station_lines(name)

    def line_names(self) -> List[str]:
        """Return all line names known to the network, sorted."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for edge in self.graph.edges():
            lines.add(edge.line)
        return sorted(lines)

    def stations_on_line(self, line: str) -> List[str]:
        """Return the station names served by a line, in registration order."""
        return [name for name in self._station_order if line in self.lines_of_station(name)]

    def transfer_stations(self) -> List[str]:
        """Return the names of interchange stations (served by multiple lines)."""
        return [name for name in self._station_order if len(self.lines_of_station(name)) > 1]

    # ------------------------------------------------------------------
    # Data update API
    # ------------------------------------------------------------------
    def add_line(self, line_name: str, station_names: List[str], distances: List[float]) -> None:
        """Add a new line described by an ordered station sequence.

        Args:
            line_name: Name of the new line.
            station_names: Ordered station names along the new line.
            distances: Distance in meters between consecutive stations.

        Raises:
            ValueError: If the input is inconsistent or the line already exists.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        names = [name.strip() for name in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len({_normalize(name) for name in names}) != len(names):
            raise ValueError("Station sequence of a line must not contain duplicates")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        for distance in distances:
            if distance <= 0:
                raise ValueError("Distances must be positive")

        for name in names:
            if name in self.station_to_number:
                lines = self.lines_of_station(name)
                if line_name not in lines:
                    lines.append(line_name)
                self.graph.set_station_lines(name, lines)
            else:
                self._register_station(name)
                self.graph.set_station_lines(name, [line_name])

        for index, distance in enumerate(distances):
            self._add_edge_by_name(names[index], names[index + 1], distance, line_name)

    def modify_station(
        self,
        old_name: str,
        new_name: Optional[str] = None,
        lines: Optional[List[str]] = None,
    ) -> str:
        """Rename a station and/or replace the lines serving it.

        Returns:
            The current (possibly new) official name of the station.

        Raises:
            ValueError: If the station does not exist or the new name is taken.
        """
        old = old_name.strip()
        if old not in self.station_to_number:
            raise ValueError(f"Station '{old}' does not exist")
        current = old
        if new_name is not None and new_name.strip() and new_name.strip() != old:
            new = new_name.strip()
            if new in self.station_to_number:
                raise ValueError(f"Station '{new}' already exists")
            number = self.station_to_number.pop(old)
            self.station_to_number[new] = number
            self._number_to_name[number] = new
            index = self._station_order.index(old)
            self._station_order[index] = new
            self.graph.station_lines[new] = self.graph.station_lines.pop(old, [])
            current = new
        if lines is not None:
            self.graph.set_station_lines(current, [str(line).strip() for line in lines])
        return current

    def update_distance(
        self,
        name_a: str,
        name_b: str,
        distance: float,
        line: Optional[str] = None,
    ) -> int:
        """Update the distance of connection(s) between two adjacent stations.

        Returns:
            The number of connections updated.

        Raises:
            ValueError: If the distance is invalid or no matching connection exists.
        """
        if distance <= 0:
            raise ValueError("Distance must be positive")
        number_a = self.number_of(name_a.strip())
        number_b = self.number_of(name_b.strip())
        edges = self.graph.find_edges(number_a, number_b)
        if line is not None:
            edges = [edge for edge in edges if edge.line == line]
        if not edges:
            raise ValueError(
                f"No connection found between '{name_a}' and '{name_b}'"
            )
        for edge in edges:
            edge.distance = distance
        return len(edges)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Export the network in the ``subway_data.json`` structure."""
        stations = [
            {"name": name, "lines": self.lines_of_station(name)}
            for name in self._station_order
        ]
        connections = [
            {
                "source": self.name_of(edge.source),
                "dest": self.name_of(edge.dest),
                "distance": edge.distance,
                "line": edge.line,
            }
            for edge in self.graph.edges()
        ]
        return {"stations": stations, "connections": connections}

    def save(self, path: str = DATA_FILE_PATH) -> None:
        """Persist the current network to a JSON file."""
        save_subway_data(self.to_dict(), path)


def _normalize(name: str) -> str:
    """Normalize a station name for tolerant comparison."""
    return "".join(name.split()).casefold()
