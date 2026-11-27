"""Subway network model built from the dataset, with data management features.

``SubwayNetwork`` converts the station/connection records into a ``models.Graph``
with integer station numbers, and provides lookup, update and integrity-check
operations.
"""

from data_loader import load_subway_data
from models import Edge, Graph

# Main lines named in the requirements document.
REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Tiananmen West"],
    "Line 2": ["Xizhimen", "Dongzhimen"],
    "Line 4": ["Beijing Zoo"],
    "Line 5": ["Songjiazhuang"],
}

# Distances above this value (meters) are reported as suspicious.
MAX_REASONABLE_DISTANCE_M = 6000


def normalize_name(text):
    """Normalise a station name for comparison (case and whitespace insensitive)."""
    return " ".join(str(text).split()).casefold()


class SubwayNetwork:
    """Subway network with station numbering, graph and data management.

    Attributes:
        station_to_number: dict mapping official station name to station number.
        number_to_station: dict mapping station number to station name.
        graph: ``models.Graph`` holding the weighted undirected network.
        connections: list of raw connection records (dicts) as loaded or added.
    """

    def __init__(self, data=None):
        """Build the network.

        Args:
            data: Parsed dataset dict. If None, ``subway_data.json`` is loaded.
        """
        if data is None:
            data = load_subway_data()
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.connections = []
        self._next_number = 1
        self._build(data)

    # ----------------------------------------------------------- construction
    def _build(self, data):
        """Populate stations and connections from the raw dataset."""
        for record in data.get("stations", []):
            name = record.get("name")
            if not name:
                continue
            self.add_station(name, record.get("lines", []))
        for conn in data.get("connections", []):
            self._load_connection(conn)

    def _load_connection(self, conn):
        """Record a connection and add its edge to the graph when possible.

        Connections that reference unknown stations are kept in ``connections``
        (so the integrity check can report them) but are not added to the graph.
        Duplicate listings of the same undirected edge on the same line are
        added only once.
        """
        self.connections.append(dict(conn))
        src = conn.get("source")
        dst = conn.get("dest")
        distance = conn.get("distance")
        line = conn.get("line")
        if src not in self.station_to_number or dst not in self.station_to_number:
            return
        if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance <= 0:
            return
        a = self.station_to_number[src]
        b = self.station_to_number[dst]
        if self.graph.find_edges(a, b, line):
            return
        self.graph.add_edge(Edge(a, b, distance, line))

    def add_station(self, name, lines):
        """Add a station (or merge lines into an existing station).

        Returns:
            int: The station number.
        """
        if name in self.station_to_number:
            number = self.station_to_number[name]
            existing = self.graph.station_lines.get(name, [])
            for line in lines:
                if line not in existing:
                    existing.append(line)
            self.graph.set_station_lines(name, existing)
            return number
        number = self._next_number
        self._next_number += 1
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, lines)
        return number

    # ---------------------------------------------------------------- lookup
    def get_number(self, name):
        """Return the station number for an official station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the official station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def line_names(self):
        """Return all known line names sorted alphabetically."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for conn in self.connections:
            if conn.get("line"):
                lines.add(conn["line"])
        return sorted(lines)

    def stations_on_line(self, line):
        """Return the sorted names of stations serving ``line``."""
        return sorted(
            name for name, lines in self.graph.station_lines.items() if line in lines
        )

    def find_station(self, text):
        """Standardise user input to an official station name.

        Matching ignores letter case and extra whitespace.

        Returns:
            str or None: The official station name, or None if not found.
        """
        if text is None:
            return None
        if text in self.station_to_number:
            return text
        key = normalize_name(text)
        for name in self.station_to_number:
            if normalize_name(name) == key:
                return name
        return None

    # ----------------------------------------------------------- data updates
    def add_line(self, line_name, station_names, distances):
        """Add a new line through an ordered list of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered list of station names on the line (at least 2).
            distances: List of distances in meters between consecutive stations.

        Raises:
            ValueError: If the input is invalid.
        """
        if not line_name or not str(line_name).strip():
            raise ValueError("Line name must not be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Exactly one distance is required between consecutive stations")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance {d!r}; distances must be positive numbers")

        for name in station_names:
            self.add_station(name, [line_name])
        for i, d in enumerate(distances):
            self._load_connection({
                "source": station_names[i],
                "dest": station_names[i + 1],
                "distance": int(d),
                "line": line_name,
            })

    def update_station_lines(self, name, lines):
        """Replace the list of lines serving an existing station."""
        if name not in self.station_to_number:
            raise KeyError(f"Station '{name}' does not exist")
        self.graph.set_station_lines(name, lines)

    def rename_station(self, old_name, new_name):
        """Rename an existing station, keeping its number and connections."""
        if old_name not in self.station_to_number:
            raise KeyError(f"Station '{old_name}' does not exist")
        if new_name in self.station_to_number:
            raise ValueError(f"Station '{new_name}' already exists")
        number = self.station_to_number.pop(old_name)
        self.station_to_number[new_name] = number
        self.number_to_station[number] = new_name
        self.graph.station_lines[new_name] = self.graph.station_lines.pop(old_name, [])
        for conn in self.connections:
            if conn.get("source") == old_name:
                conn["source"] = new_name
            if conn.get("dest") == old_name:
                conn["dest"] = new_name

    def update_distance(self, a, b, distance, line=None):
        """Update the distance between two adjacent stations.

        Returns:
            int: Number of graph edges updated.

        Raises:
            KeyError: If a station does not exist.
            ValueError: If the distance is invalid or no connection exists.
        """
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number of meters")
        if a not in self.station_to_number or b not in self.station_to_number:
            raise KeyError("Both stations must exist")
        changed = self.graph.update_edge_distance(
            self.station_to_number[a], self.station_to_number[b], distance, line
        )
        if changed == 0:
            raise ValueError(f"No connection between '{a}' and '{b}'" + (f" on {line}" if line else ""))
        for conn in self.connections:
            if {conn.get("source"), conn.get("dest")} == {a, b} and (line is None or conn.get("line") == line):
                conn["distance"] = int(distance)
        return changed

    # ------------------------------------------------------- integrity checks
    def check_integrity(self):
        """Run data integrity checks.

        Checks performed:
            * coverage of main lines and representative stations;
            * connection validity (known stations, no self-loops, line membership);
            * network connectivity;
            * distance accuracy (positive, plausible, consistent across listings).

        Returns:
            dict: ``{"errors": [...], "warnings": [...], "ok": bool}``.
        """
        errors = []
        warnings = []

        # Coverage
        for line in REQUIRED_LINES:
            if not self.stations_on_line(line):
                warnings.append(f"Main line '{line}' has no stations in the network")
        for line, representatives in REPRESENTATIVE_STATIONS.items():
            for name in representatives:
                if name not in self.station_to_number:
                    warnings.append(f"Representative station '{name}' of {line} is missing")
        for name, number in self.station_to_number.items():
            if self.graph.degree(number) == 0:
                warnings.append(f"Station '{name}' has no connections")

        # Connections and distances
        seen = {}
        for conn in self.connections:
            src = conn.get("source")
            dst = conn.get("dest")
            line = conn.get("line")
            distance = conn.get("distance")
            label = f"{src} -> {dst} ({line})"
            if src not in self.station_to_number or dst not in self.station_to_number:
                errors.append(f"Connection {label} references an unknown station")
                continue
            if src == dst:
                errors.append(f"Connection {label} is a self-loop")
                continue
            for name in (src, dst):
                if line not in self.graph.station_lines.get(name, []):
                    warnings.append(f"Station '{name}' is not listed as serving {line} (connection {label})")
            if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
                errors.append(f"Connection {label} has invalid distance {distance!r}")
                continue
            if distance > MAX_REASONABLE_DISTANCE_M:
                warnings.append(f"Connection {label} has an unusually long distance ({distance} m)")
            key = (frozenset((src, dst)), line)
            if key in seen and seen[key] != distance:
                errors.append(
                    f"Inconsistent distances for {src} <-> {dst} on {line}: {seen[key]} m vs {distance} m"
                )
            else:
                seen.setdefault(key, distance)

        components = self.graph.connected_components()
        if components > 1:
            errors.append(f"Network is split into {components} disconnected components")

        return {"errors": errors, "warnings": warnings, "ok": not errors}
