"""
Data management for the subway network.

The DataManager loads ``subway_data.json``, builds the station numbering and the
Graph, answers station-name lookups, and supports data updates (adding lines,
modifying stations, updating distances) followed by a graph rebuild.
"""

import json

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph
from data_integrity import DataIntegrityChecker


def normalize_name(name):
    """
    Normalise a station name for lenient matching.

    Lower-cases the text, removes spaces, underscores and dashes and drops a
    trailing '站' (station) or 'station' suffix.
    """
    text = str(name).strip().lower()
    for ch in (" ", "\t", "_", "-"):
        text = text.replace(ch, "")
    if text.endswith("站"):
        text = text[:-1]
    if text.endswith("station"):
        text = text[:-len("station")]
    return text


class DataManager:
    """
    Manages the subway dataset and the derived graph.

    Attributes:
        data_path: Path of the JSON data source.
        data: Raw dataset dict with ``stations`` and ``connections``.
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        graph: The Graph built from the dataset.
        skipped_connections: Indices of connection records that were ignored.
        checker: DataIntegrityChecker used by ``run_integrity_check``.
    """

    def __init__(self, data_path=DATA_FILE_PATH):
        self.data_path = data_path
        self.data = {"stations": [], "connections": []}
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.skipped_connections = []
        self.checker = DataIntegrityChecker()
        self._norm_index = {}

    # ------------------------------------------------------------ loading
    def load(self):
        """Load the dataset from ``data_path`` and build the graph."""
        raw = load_subway_data(self.data_path)
        self.data = {
            "stations": list(raw.get("stations", []) or []),
            "connections": list(raw.get("connections", []) or []),
        }
        self.rebuild()

    def rebuild(self):
        """(Re)build station numbering, the graph and the name index from ``data``."""
        self.station_to_number = {}
        self.number_to_station = {}
        self._norm_index = {}
        self.graph = Graph()
        self.skipped_connections = []

        for st in self.data["stations"]:
            if not isinstance(st, dict):
                continue
            name = str(st.get("name", "")).strip()
            if not name:
                continue
            self._register(name)
            self.graph.set_station_lines(name, st.get("lines", []))

        for index, conn in enumerate(self.data["connections"]):
            try:
                src = str(conn["source"]).strip()
                dst = str(conn["dest"]).strip()
                line = str(conn["line"]).strip()
                distance = float(conn["distance"])
            except (KeyError, TypeError, ValueError):
                self.skipped_connections.append(index)
                continue
            if not src or not dst or src == dst or distance <= 0:
                self.skipped_connections.append(index)
                continue
            a = self._register(src)
            b = self._register(dst)
            self.graph.station_lines.setdefault(src, [])
            self.graph.station_lines.setdefault(dst, [])
            self.graph.add_edge(Edge(a, b, distance, line))

    def _register(self, name):
        """Assign a station number to ``name`` if it has none yet and return it."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.number_to_station)
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self._norm_index.setdefault(normalize_name(name), name)
        self.graph.add_node(number)
        return number

    # ------------------------------------------------------------ lookups
    def standard_name(self, user_input):
        """
        Map user input to the official station name.

        Returns:
            str or None: the official name, or None if no station matches.
        """
        text = str(user_input or "").strip()
        if not text:
            return None
        if text in self.station_to_number:
            return text
        return self._norm_index.get(normalize_name(text))

    def get_station_number(self, name):
        """Return the station number of an official station name, or None."""
        return self.station_to_number.get(name)

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def line_names(self):
        """Return all line names present in the dataset, sorted."""
        names = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        for conn in self.data["connections"]:
            if isinstance(conn, dict) and conn.get("line"):
                names.add(str(conn["line"]).strip())
        return sorted(n for n in names if n)

    def station_lines_of(self, name):
        """Return the list of lines a station serves."""
        return list(self.graph.station_lines.get(name, []))

    def is_transfer_station(self, name):
        """Return True if a station serves more than one line."""
        return len(self.station_lines_of(name)) > 1

    def _find_station_entry(self, name):
        """Return the raw station record with the given name, or None."""
        for entry in self.data["stations"]:
            if isinstance(entry, dict) and entry.get("name") == name:
                return entry
        return None

    # ------------------------------------------------------------ updates
    def add_line(self, line_name, station_names, distances):
        """
        Add a new line with an ordered list of stations and inter-station distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line.
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: If the input is inconsistent.
        """
        line_name = str(line_name or "").strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal the number of stations minus one")

        resolved = []
        for raw in station_names:
            official = self.standard_name(raw)
            resolved.append(official if official else str(raw).strip())
        if len(set(resolved)) != len(resolved):
            raise ValueError("A line cannot visit the same station twice")

        values = []
        for d in distances:
            value = int(round(float(d)))
            if value <= 0:
                raise ValueError("Distances must be positive")
            values.append(value)

        for name in resolved:
            entry = self._find_station_entry(name)
            if entry is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in entry.get("lines", []):
                entry.setdefault("lines", []).append(line_name)

        for i in range(len(resolved) - 1):
            self.data["connections"].append({
                "source": resolved[i],
                "dest": resolved[i + 1],
                "distance": values[i],
                "line": line_name,
            })
        self.rebuild()

    def modify_station(self, old_name, new_name=None, lines=None):
        """
        Modify a station's name and/or line list.

        Args:
            old_name: Existing station name (lenient matching allowed).
            new_name: Optional new official name.
            lines: Optional replacement list of lines.

        Returns:
            str: The resulting station name.

        Raises:
            ValueError: If the station does not exist or the new name is taken.
        """
        official = self.standard_name(old_name)
        if official is None:
            raise ValueError(f"Station '{old_name}' does not exist")
        entry = self._find_station_entry(official)
        if entry is None:
            entry = {"name": official, "lines": []}
            self.data["stations"].append(entry)

        if lines is not None:
            entry["lines"] = [str(x).strip() for x in lines if str(x).strip()]

        result = official
        if new_name and new_name.strip():
            new_name = new_name.strip()
            if new_name != official:
                existing = self.standard_name(new_name)
                if existing is not None and existing != official:
                    raise ValueError(f"Station '{new_name}' already exists")
                entry["name"] = new_name
                for conn in self.data["connections"]:
                    if isinstance(conn, dict):
                        if conn.get("source") == official:
                            conn["source"] = new_name
                        if conn.get("dest") == official:
                            conn["dest"] = new_name
                result = new_name
        self.rebuild()
        return result

    def update_distance(self, a, b, distance, line=None):
        """
        Update the distance between two adjacent stations.

        Args:
            a: First station name.
            b: Second station name.
            distance: New distance in meters (positive integer).
            line: Optional line name to restrict the update.

        Returns:
            int: Number of connection records updated.

        Raises:
            ValueError: If stations or connection do not exist, or distance is invalid.
        """
        sa = self.standard_name(a)
        sb = self.standard_name(b)
        if sa is None or sb is None:
            raise ValueError("Both stations must exist")
        try:
            value = int(distance)
        except (TypeError, ValueError):
            raise ValueError("Distance must be a positive integer")
        if value <= 0:
            raise ValueError("Distance must be a positive integer")

        changed = 0
        for conn in self.data["connections"]:
            if not isinstance(conn, dict):
                continue
            pair = {conn.get("source"), conn.get("dest")}
            if pair == {sa, sb} and (line is None or conn.get("line") == line):
                conn["distance"] = value
                changed += 1
        if changed == 0:
            raise ValueError(f"No connection found between '{sa}' and '{sb}'")
        self.rebuild()
        return changed

    def save(self, path=None):
        """Write the current dataset to a JSON file (defaults to ``data_path``)."""
        target = path or self.data_path
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        return target

    # ----------------------------------------------------------- checking
    def run_integrity_check(self):
        """Run the data integrity checker on the current dataset."""
        return self.checker.check(self.data)
