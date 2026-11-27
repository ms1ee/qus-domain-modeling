"""Subway network data management: loading, name lookup, data updates,
and data integrity checks."""

import re

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

# Main lines that must be represented in the dataset (integrity coverage check).
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Plausible range for a single inter-station distance in meters (accuracy check).
MIN_SEGMENT_DISTANCE_M = 100
MAX_SEGMENT_DISTANCE_M = 10000


def _clean_name(value):
    """Normalise a name: convert to string and collapse whitespace."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _is_positive_int(value):
    """Return True for positive integers (booleans are rejected)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _line_sort_key(line):
    """Sort lines naturally, e.g. 'Line 2' before 'Line 10'."""
    match = re.search(r"\d+", line)
    number = int(match.group()) if match else 10 ** 6
    return (number, line)


class DataManager:
    """Owns the subway graph and the mapping between station names and numbers.

    Attributes:
        data_source_path: path of the JSON dataset.
        graph: the weighted undirected Graph of stations.
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
        last_check_passed: result of the most recent integrity check.
    """

    def __init__(self, data_source_path=DATA_FILE_PATH):
        self.data_source_path = data_source_path
        self.last_check_passed = False
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._station_order = []
        self._connections = []
        self._next_number = 0
        self.load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self):
        """(Re)load the network from the JSON data source."""
        data = load_subway_data(self.data_source_path)
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._station_order = []
        self._connections = []
        self._next_number = 0

        for entry in data.get("stations", []):
            name = _clean_name(entry.get("name"))
            if not name:
                continue
            if name not in self.station_to_number:
                self._register_station(name)
            # Merge line lists: a station may appear more than once in the data.
            merged = self.graph.station_lines[name]
            for line in entry.get("lines") or []:
                line = _clean_name(line)
                if line and line not in merged:
                    merged.append(line)

        for conn in data.get("connections", []):
            record = {
                "source": _clean_name(conn.get("source")),
                "dest": _clean_name(conn.get("dest")),
                "distance": conn.get("distance"),
                "line": _clean_name(conn.get("line")),
            }
            self._connections.append(record)
            self._add_graph_edge(record)

        self.last_check_passed = False

    def _register_station(self, name):
        """Assign a new station number to ``name`` and add it to the graph."""
        number = self._next_number
        self._next_number += 1
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self._station_order.append(name)
        self.graph.add_node(number)
        self.graph.set_station_lines(name, [])
        return number

    def _add_graph_edge(self, record):
        """Add a graph edge for a connection record if it is valid.

        Invalid records are kept in the connection list so that the integrity
        check can report them, but they are not added to the graph.
        """
        src = self.station_to_number.get(record["source"])
        dst = self.station_to_number.get(record["dest"])
        distance = record["distance"]
        if src is None or dst is None or src == dst:
            return False
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            return False
        self.graph.add_edge(Edge(src, dst, distance, record["line"]))
        return True

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def standardize_station_name(self, text):
        """Map user input to an official station name.

        Matching is case-insensitive and ignores extra whitespace; a trailing
        '站' or ' station' suffix is also accepted.

        Returns:
            The official station name, or None if no station matches.
        """
        cleaned = _clean_name(text)
        if not cleaned:
            return None
        if cleaned in self.station_to_number:
            return cleaned
        candidates = {name.casefold(): name for name in self.station_to_number}
        lowered = cleaned.casefold()
        if lowered in candidates:
            return candidates[lowered]
        for suffix in ("站", " station"):
            if lowered.endswith(suffix):
                trimmed = lowered[: -len(suffix)].strip()
                if trimmed in candidates:
                    return candidates[trimmed]
        return None

    def has_station(self, name):
        """Return True if the official station name exists."""
        return name in self.station_to_number

    def get_number(self, name):
        """Return the station number for an official station name."""
        return self.station_to_number[name]

    def station_names(self):
        """Return all station names in dataset order."""
        return list(self._station_order)

    def lines(self):
        """Return all line names sorted naturally."""
        found = set()
        for line_list in self.graph.station_lines.values():
            found.update(line_list)
        for record in self._connections:
            if record["line"]:
                found.add(record["line"])
        return sorted(found, key=_line_sort_key)

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line made of consecutive stations.

        Args:
            line_name: name of the new line, e.g. "Line 99".
            station_names: ordered list of station names on the line. Unknown
                stations are created.
            distances: list of positive integer distances (meters) between
                consecutive stations; must have one entry fewer than stations.

        Raises:
            ValueError: if the input is invalid or the line already exists.
        """
        line = _clean_name(line_name)
        if not line:
            raise ValueError("Line name cannot be empty")
        if line in self.lines():
            raise ValueError(f"Line '{line}' already exists")
        names = [_clean_name(name) for name in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if any(not name for name in names):
            raise ValueError("Station names cannot be empty")
        if len(set(names)) != len(names):
            raise ValueError("A line cannot contain duplicate stations")
        distances = list(distances)
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")
        for distance in distances:
            if not _is_positive_int(distance):
                raise ValueError(f"Invalid distance {distance!r}; must be a positive integer")

        for name in names:
            if name not in self.station_to_number:
                self._register_station(name)
            if line not in self.graph.station_lines[name]:
                self.graph.station_lines[name].append(line)

        for index, distance in enumerate(distances):
            record = {"source": names[index], "dest": names[index + 1],
                      "distance": distance, "line": line}
            self._connections.append(record)
            self._add_graph_edge(record)

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace the list of lines serving it.

        Returns:
            The final (possibly new) station name.

        Raises:
            KeyError: if the station does not exist.
            ValueError: if the new name is empty or already used.
        """
        current = _clean_name(name)
        if current not in self.station_to_number:
            raise KeyError(f"Station '{name}' does not exist")
        number = self.station_to_number[current]
        final = _clean_name(new_name) if new_name else current
        if not final:
            raise ValueError("Station name cannot be empty")

        if final != current:
            if final in self.station_to_number:
                raise ValueError(f"Station '{final}' already exists")
            del self.station_to_number[current]
            self.station_to_number[final] = number
            self.number_to_station[number] = final
            self._station_order[self._station_order.index(current)] = final
            self.graph.station_lines[final] = self.graph.station_lines.pop(current)
            for record in self._connections:
                if record["source"] == current:
                    record["source"] = final
                if record["dest"] == current:
                    record["dest"] = final

        if lines is not None:
            cleaned = []
            for line in lines:
                line = _clean_name(line)
                if line and line not in cleaned:
                    cleaned.append(line)
            self.graph.set_station_lines(final, cleaned)
        return final

    def update_distance(self, a, b, distance):
        """Update the distance (meters) of the direct connection between two stations.

        Raises:
            KeyError: if a station does not exist.
            ValueError: if the distance is invalid, the stations are identical,
                or no direct connection exists between them.
        """
        first = _clean_name(a)
        second = _clean_name(b)
        if first not in self.station_to_number or second not in self.station_to_number:
            raise KeyError("Both stations must exist")
        if first == second:
            raise ValueError("A connection needs two different stations")
        if not _is_positive_int(distance):
            raise ValueError("Distance must be a positive integer (meters)")

        found = False
        for record in self._connections:
            if {record["source"], record["dest"]} == {first, second}:
                record["distance"] = distance
                found = True
        if not found:
            raise ValueError(f"No direct connection between '{first}' and '{second}'")
        self.graph.update_distance(self.station_to_number[first],
                                   self.station_to_number[second], distance)
        return True

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    def check_integrity(self):
        """Run all data integrity checks.

        Checks performed:
            * coverage: every main line has at least one station;
            * connectivity: connections reference known stations, distinct
              endpoints, valid line names served by both endpoints, and every
              station has at least one connection;
            * consistency: repeated connections between the same pair agree;
            * accuracy: distances are positive integers in a plausible range.

        Returns:
            A list of human-readable issue strings (empty if the data is valid).
        """
        issues = []
        if not self._station_order:
            issues.append("Coverage: no stations are loaded")

        served = set()
        for name in self._station_order:
            served.update(self.graph.station_lines.get(name, []))
        for line in MAIN_LINES:
            if line not in served:
                issues.append(f"Coverage: main line '{line}' has no stations in the dataset")

        connected = set()
        seen_pairs = {}
        for record in self._connections:
            src = record["source"]
            dst = record["dest"]
            line = record["line"]
            distance = record["distance"]
            label = f"Connection '{src}' - '{dst}' ({line})"
            valid_endpoints = True

            for endpoint in (src, dst):
                if endpoint not in self.station_to_number:
                    issues.append(f"Connectivity: {label} references unknown station '{endpoint}'")
                    valid_endpoints = False
            if src == dst:
                issues.append(f"Connectivity: {label} links a station to itself")
                valid_endpoints = False

            if not line:
                issues.append(f"Connectivity: {label} has no line name")
            elif valid_endpoints:
                for endpoint in (src, dst):
                    if line not in self.graph.station_lines.get(endpoint, []):
                        issues.append(f"Connectivity: line '{line}' is not served by station '{endpoint}'")

            if valid_endpoints:
                connected.add(src)
                connected.add(dst)
                key = frozenset((src, dst))
                if key in seen_pairs and seen_pairs[key] != distance:
                    issues.append(f"Consistency: {src} - {dst} has conflicting distances "
                                  f"{seen_pairs[key]} and {distance}")
                seen_pairs.setdefault(key, distance)

            if not _is_positive_int(distance):
                issues.append(f"Accuracy: {label} has invalid distance {distance!r}")
            elif distance < MIN_SEGMENT_DISTANCE_M or distance > MAX_SEGMENT_DISTANCE_M:
                issues.append(f"Accuracy: {label} distance {distance} m is outside the plausible "
                              f"range [{MIN_SEGMENT_DISTANCE_M}, {MAX_SEGMENT_DISTANCE_M}]")

        for name in self._station_order:
            if name not in connected:
                issues.append(f"Connectivity: station '{name}' has no connections")

        self.last_check_passed = not issues
        return issues
