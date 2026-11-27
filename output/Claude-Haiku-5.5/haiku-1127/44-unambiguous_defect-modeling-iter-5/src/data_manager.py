"""Management of the Beijing Subway network data.

The DataManager owns the raw station/connection data, assigns station numbers,
builds the weighted undirected Graph, and supports data updates (adding lines,
modifying stations, updating distances) followed by an automatic graph rebuild.
"""

import json
import os
import unicodedata

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

DATA_VERSION = "1.0"


def normalize_line_name(name):
    """Normalize a line name so that 'Line 1', '1号线' and '1' compare equal.

    'Changping Line', '昌平线' and 'changping' also compare equal.
    """
    text = "".join(str(name).split()).lower()
    for suffix in ("号线", "line", "线"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    if text.startswith("line") and len(text) > 4:
        text = text[4:]
    return text


def _fold(name):
    """Fold a station or line name for case- and width-insensitive comparison."""
    text = unicodedata.normalize("NFKC", str(name))
    return "".join(text.split()).casefold()


class DataManager:
    """Owns the subway network data and the Graph built from it.

    Attributes:
        source_file: Path of the dataset file.
        data_version: Version string of the data manager.
        graph: The current Graph (rebuilt after every update).
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        station_lines: dict station name -> list of line names.
    """

    def __init__(self, source_file=DATA_FILE_PATH):
        self.source_file = source_file
        self.data_version = DATA_VERSION
        self._stations = []      # list of {"name": str, "lines": [str]}
        self._connections = []   # list of {"source", "dest", "distance", "line"}
        self._order = []         # station names in numbering order
        self._folded = {}
        self._line_names = []
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}
        self.load()

    # ------------------------------------------------------------------ loading
    def load(self, path=None):
        """(Re)load the dataset from ``path`` (defaults to the current source file)."""
        path = path or self.source_file
        data = load_subway_data(path)
        stations, connections = self._parse(data)
        self._stations = stations
        self._connections = connections
        self.source_file = path
        self._rebuild()

    @staticmethod
    def _parse(data):
        """Validate and normalize the raw dataset structure."""
        stations = []
        for idx, item in enumerate(data["stations"]):
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                raise ValueError(f"Invalid station entry at index {idx}")
            lines = item.get("lines", [])
            if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
                raise ValueError(f"Invalid 'lines' for station '{item['name']}'")
            stations.append({"name": item["name"].strip(), "lines": [x.strip() for x in lines]})

        connections = []
        for idx, item in enumerate(data["connections"]):
            if not isinstance(item, dict):
                raise ValueError(f"Invalid connection entry at index {idx}")
            for key in ("source", "dest", "line"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError(f"Connection {idx} has an invalid '{key}'")
            distance = item.get("distance")
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                raise ValueError(f"Connection {idx} has an invalid 'distance'")
            connections.append({
                "source": item["source"].strip(),
                "dest": item["dest"].strip(),
                "distance": int(round(distance)),
                "line": item["line"].strip(),
            })
        return stations, connections

    def _rebuild(self):
        """Recompute station numbers, station-line map, and the Graph from raw data."""
        order = []
        lines_map = {}

        def ensure(name):
            if name not in lines_map:
                lines_map[name] = []
                order.append(name)
            return lines_map[name]

        for st in self._stations:
            name_lines = ensure(st["name"])
            for line in st["lines"]:
                if line not in name_lines:
                    name_lines.append(line)
        for conn in self._connections:
            for endpoint in (conn["source"], conn["dest"]):
                endpoint_lines = ensure(endpoint)
                if conn["line"] not in endpoint_lines:
                    endpoint_lines.append(conn["line"])

        numbers = {name: idx for idx, name in enumerate(order)}
        graph = Graph()
        for name in order:
            graph.set_station_lines(name, lines_map[name])
            graph.add_node(numbers[name])
        for conn in self._connections:
            graph.add_edge(Edge(numbers[conn["source"]], numbers[conn["dest"]],
                                conn["distance"], conn["line"]))

        self._order = order
        self.graph = graph
        self.station_to_number = numbers
        self.number_to_station = {num: name for name, num in numbers.items()}
        self.station_lines = lines_map
        self._folded = {}
        for name in order:
            self._folded.setdefault(_fold(name), name)
        line_set = set()
        for lines in lines_map.values():
            line_set.update(lines)
        self._line_names = sorted(line_set)

    # ------------------------------------------------------------------ queries
    @property
    def connections(self):
        """Copy of the raw connection records."""
        return [dict(c) for c in self._connections]

    def station_names(self):
        """Sorted list of all official station names."""
        return sorted(self.station_to_number)

    def line_names(self):
        """Sorted list of all line names."""
        return list(self._line_names)

    def stations_on_line(self, line):
        """Return the station names served by ``line`` in dataset order."""
        return [name for name in self._order if line in self.station_lines[name]]

    def standardize_station_name(self, raw_name):
        """Map user input to an official station name.

        Accepts exact names, names with or without the trailing '站', and
        case/width/space-insensitive matches.

        Returns:
            The official station name, or None if no station matches.
        """
        if not isinstance(raw_name, str):
            return None
        cleaned = unicodedata.normalize("NFKC", raw_name).strip()
        if not cleaned:
            return None
        alt = cleaned[:-1] if cleaned.endswith("站") else cleaned + "站"
        for candidate in (cleaned, alt):
            if candidate in self.station_to_number:
                return candidate
        for candidate in (cleaned, alt):
            found = self._folded.get(_fold(candidate))
            if found is not None:
                return found
        return None

    def find_line(self, raw_name):
        """Return the official line name matching ``raw_name``, or None."""
        if not isinstance(raw_name, str) or not raw_name.strip():
            return None
        text = raw_name.strip()
        if text in self._line_names:
            return text
        folded = _fold(text)
        for line in self._line_names:
            if _fold(line) == folded:
                return line
        key = normalize_line_name(text)
        for line in self._line_names:
            if normalize_line_name(line) == key:
                return line
        return None

    def get_station_number(self, name):
        """Return the station number of an official station name."""
        return self.station_to_number[name]

    def get_station_name(self, number):
        """Return the official station name of a station number."""
        return self.number_to_station[number]

    def _require_station(self, raw_name):
        std = self.standardize_station_name(raw_name)
        if std is None:
            raise ValueError(f"Station '{raw_name}' does not exist")
        return std

    @staticmethod
    def _validate_distance(distance):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError("distance must be a number of meters")
        if distance <= 0:
            raise ValueError("distance must be positive")
        return int(round(distance))

    def _find_entry(self, name):
        for entry in self._stations:
            if entry["name"] == name:
                return entry
        return None

    def _get_or_create_entry(self, name):
        entry = self._find_entry(name)
        if entry is None:
            entry = {"name": name, "lines": []}
            self._stations.append(entry)
        return entry

    # ------------------------------------------------------------------ updates
    def add_line(self, line_name, station_names, distances):
        """Add a new line as an ordered station sequence with consecutive distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of at least two station names. Existing
                stations are reused; unknown names create new stations.
            distances: List of positive distances in meters, one per consecutive pair.

        Raises:
            ValueError: On invalid input or if the line already exists.
        """
        line = str(line_name).strip()
        if not line:
            raise ValueError("Line name must not be empty")
        if self.find_line(line) is not None:
            raise ValueError(f"Line '{line}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        names = []
        for raw in station_names:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("Station names must be non-empty strings")
            names.append(self.standardize_station_name(raw) or raw.strip())
        if len(set(names)) != len(names):
            raise ValueError("Duplicate station in the line sequence")
        if len(distances) != len(names) - 1:
            raise ValueError("Exactly one distance per consecutive station pair is required")
        dists = [self._validate_distance(d) for d in distances]

        for name in names:
            entry = self._get_or_create_entry(name)
            if line not in entry["lines"]:
                entry["lines"].append(line)
        for idx, dist in enumerate(dists):
            self._connections.append({
                "source": names[idx],
                "dest": names[idx + 1],
                "distance": dist,
                "line": line,
            })
        self._rebuild()

    def modify_station(self, station_name, new_name=None, add_lines=None, remove_lines=None):
        """Rename a station and/or change the lines it is served by.

        Raises:
            ValueError: On invalid input, duplicate names, or removing a line
                that still has connections at this station.
        """
        old = self._require_station(station_name)
        target = old
        if new_name is not None:
            target = str(new_name).strip()
            if not target:
                raise ValueError("New station name must not be empty")
            if target != old and target in self.station_to_number:
                raise ValueError(f"Station '{target}' already exists")

        remove_set = [str(x).strip() for x in (remove_lines or [])]
        for line in remove_set:
            if any(c["line"] == line and old in (c["source"], c["dest"]) for c in self._connections):
                raise ValueError(f"Line '{line}' still has connections at '{old}' and cannot be removed")

        entry = self._get_or_create_entry(old)
        for line in (add_lines or []):
            line = str(line).strip()
            if line and line not in entry["lines"]:
                entry["lines"].append(line)
        for line in remove_set:
            if line in entry["lines"]:
                entry["lines"].remove(line)

        if target != old:
            entry["name"] = target
            for conn in self._connections:
                if conn["source"] == old:
                    conn["source"] = target
                if conn["dest"] == old:
                    conn["dest"] = target
        self._rebuild()

    def update_distance(self, source_name, dest_name, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        Args:
            source_name: One station name.
            dest_name: The other station name.
            distance: New distance in meters (positive).
            line: Restrict the update to one line; None updates all matching connections.

        Returns:
            Number of connections updated.

        Raises:
            ValueError: If no matching connection exists or the input is invalid.
        """
        a = self._require_station(source_name)
        b = self._require_station(dest_name)
        dist = self._validate_distance(distance)
        matched = [
            c for c in self._connections
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line)
        ]
        if not matched:
            raise ValueError(f"No connection between '{a}' and '{b}'" + (f" on '{line}'" if line else ""))
        for conn in matched:
            conn["distance"] = dist
        self._rebuild()
        return len(matched)

    # ------------------------------------------------------------------ export
    def to_dict(self):
        """Return the current dataset in the same structure as subway_data.json."""
        return {
            "stations": [{"name": n, "lines": list(self.station_lines[n])} for n in self._order],
            "connections": self.connections,
        }

    def save(self, path=None):
        """Write the current dataset to ``path`` (defaults to the source file)."""
        target = path or self.source_file
        directory = os.path.dirname(os.path.abspath(target))
        os.makedirs(directory, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
        return target
