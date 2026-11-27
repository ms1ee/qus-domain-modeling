"""Subway network model: station numbering, graph construction, data
management (line/station/distance updates) and integrity checks.
"""

import math
from collections import deque

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

# Representative stations per main line, used by the coverage check.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "天安门东", "国贸"],
    "Line 2": ["西直门", "建国门", "东直门"],
    "Line 4": ["圆明园", "北京大学东门"],
    "Line 5": ["天通苑北", "北新桥"],
    "Line 6": ["金安桥"],
    "Line 8": ["鼓楼大街"],
    "Line 10": ["亮马桥"],
    "Line 13": ["回龙观"],
    "Line 14": ["张郭庄"],
    "Line 15": ["望京西"],
    "Yizhuang Line": ["宋家庄"],
}

# Distances outside this range (meters) are reported as suspicious.
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _validate_distance(distance):
    """Ensure a distance is a positive finite number and return it."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError(f"distance {distance!r} is not a number")
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError(f"distance {distance!r} must be a positive number")
    return distance


def _fold(text):
    """Normalized key for case/space-insensitive station name matching."""
    return "".join(text.split()).casefold()


class SubwayNetwork:
    """Holds the subway graph plus the name <-> number station mapping.

    Attributes:
        graph: the weighted undirected Graph (vertices are station numbers).
        station_to_number: dict station name -> station number.
        number_to_name: list where index is the station number.
        connections: list of connection records (dicts with source, dest,
            distance, line).
    """

    def __init__(self, data=None):
        if data is None:
            data = load_subway_data(DATA_FILE_PATH)
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = []
        self.connections = []
        self.line_stations = {}
        self._declared_stations = set()
        self._declared_lines = {}
        self._undeclared_stations = set()
        self._load_problems = []
        self._folded_index = {}
        self._load(data)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _load(self, data):
        """Populate the network from the parsed JSON dataset."""
        for station in data.get("stations", []):
            try:
                name = station["name"]
                lines = station.get("lines", [])
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("empty station name")
                if not isinstance(lines, list):
                    raise ValueError("'lines' must be a list")
                name = name.strip()
                clean_lines = [str(line).strip() for line in lines if str(line).strip()]
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                self._load_problems.append(f"ERROR: invalid station record {station!r}: {exc}")
                continue
            self._declared_stations.add(name)
            self._declared_lines[name] = list(dict.fromkeys(clean_lines))
            self._ensure_station(name, clean_lines)

        for conn in data.get("connections", []):
            try:
                self._connect(conn["source"], conn["dest"], conn["distance"], conn["line"])
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                self._load_problems.append(f"ERROR: invalid connection {conn!r}: {exc}")

    def _ensure_station(self, name, lines=()):
        """Return the station number for ``name``, creating the station if needed.

        Any lines given are merged into the station's line list.
        """
        if name not in self.station_to_number:
            number = len(self.number_to_name)
            self.station_to_number[name] = number
            self.number_to_name.append(name)
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
            self._folded_index.setdefault(_fold(name), name)
        current = list(self.graph.station_lines.get(name, []))
        for line in lines:
            if line not in current:
                current.append(line)
        self.graph.set_station_lines(name, current)
        return self.station_to_number[name]

    def _connect(self, src, dst, distance, line):
        """Create an undirected connection between two stations on a line."""
        if not all(isinstance(x, str) for x in (src, dst, line)):
            raise ValueError("station and line names must be strings")
        src, dst, line = src.strip(), dst.strip(), line.strip()
        if not src or not dst or not line:
            raise ValueError("empty station or line name")
        if src == dst:
            raise ValueError("connection endpoints must differ")
        _validate_distance(distance)
        for name in (src, dst):
            if name not in self._declared_stations:
                self._undeclared_stations.add(name)
        a = self._ensure_station(src, [line])
        b = self._ensure_station(dst, [line])
        self.graph.add_edge(Edge(a, b, distance, line))
        self.connections.append({"source": src, "dest": dst,
                                 "distance": distance, "line": line})
        self.line_stations.setdefault(line, set()).update((src, dst))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def station_count(self):
        """Return the number of stations in the network."""
        return len(self.station_to_number)

    def station_exists(self, name):
        """Return True if the exact station name exists."""
        return name in self.station_to_number

    def get_number(self, name):
        """Return the station number for an exact station name."""
        return self.station_to_number[name]

    def get_name(self, number):
        """Return the station name for a station number."""
        return self.number_to_name[number]

    def standardize_station_name(self, raw):
        """Map user input to an official station name, or None if unknown.

        Matching ignores surrounding whitespace, letter case, inner spaces and
        a trailing "站" character.
        """
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if not text:
            return None
        candidates = [text]
        if text.endswith("站") and len(text) > 1:
            candidates.append(text[:-1].strip())
        for candidate in candidates:
            if candidate in self.station_to_number:
                return candidate
        for candidate in candidates:
            key = _fold(candidate)
            if key and key in self._folded_index:
                return self._folded_index[key]
        return None

    def lines_of(self, name):
        """Return the list of lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def all_line_names(self):
        """Return the sorted list of all known line names."""
        names = set(self.line_stations.keys())
        for lines in self.graph.station_lines.values():
            names.update(lines)
        return sorted(names)

    def transfer_stations(self):
        """Return names of stations served by two or more lines."""
        return [name for name in self.station_to_number
                if len(self.graph.station_lines.get(name, [])) >= 2]

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def _require_station(self, name):
        std = self.standardize_station_name(name)
        if std is None:
            raise ValueError(f"unknown station '{name}'")
        return std

    def add_line(self, line_name, station_names, distances):
        """Add a new line as an ordered station sequence with distances.

        Args:
            line_name: name of the new line (must not exist yet).
            station_names: ordered list of at least two station names. Unknown
                names create new stations.
            distances: list of distances in meters, one per consecutive pair.

        Raises:
            ValueError: on invalid input (nothing is modified in that case).
        """
        if not isinstance(line_name, str) or not line_name.strip():
            raise ValueError("line name must be a non-empty string")
        line_name = line_name.strip()
        if line_name in self.all_line_names():
            raise ValueError(f"line '{line_name}' already exists")
        names = [s.strip() if isinstance(s, str) else "" for s in station_names]
        if len(names) < 2 or any(not n for n in names):
            raise ValueError("a line needs at least two named stations")
        if len(set(names)) != len(names):
            raise ValueError("station sequence must not repeat a station")
        if len(distances) != len(names) - 1:
            raise ValueError("one distance is required per consecutive station pair")
        for d in distances:
            _validate_distance(d)

        for name in names:
            self._declared_stations.add(name)
            declared = list(self._declared_lines.get(name, []))
            if line_name not in declared:
                declared.append(line_name)
            self._declared_lines[name] = declared
            self._ensure_station(name, [line_name])
        for i, d in enumerate(distances):
            self._connect(names[i], names[i + 1], d, line_name)

    def update_station_lines(self, name, lines):
        """Replace the list of lines serving an existing station."""
        std = self._require_station(name)
        clean = list(dict.fromkeys(str(l).strip() for l in lines if str(l).strip()))
        self.graph.set_station_lines(std, clean)
        self._declared_stations.add(std)
        self._declared_lines[std] = list(clean)
        return clean

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance between two adjacent stations.

        Args:
            station_a, station_b: station names (standardized internally).
            distance: new distance in meters (positive number).
            line: optional line name restricting which connection to update.

        Returns:
            The number of connections updated.

        Raises:
            ValueError: if the distance is invalid or no connection exists.
        """
        _validate_distance(distance)
        na = self._require_station(station_a)
        nb = self._require_station(station_b)
        ia, ib = self.station_to_number[na], self.station_to_number[nb]
        count = 0
        for edge in self.graph.adjacent(ia):
            if edge.other(ia) == ib and (line is None or edge.line == line):
                edge.distance = distance
                count += 1
        for rec in self.connections:
            if {rec["source"], rec["dest"]} == {na, nb} and (line is None or rec["line"] == line):
                rec["distance"] = distance
        if count == 0:
            raise ValueError(f"no connection between '{na}' and '{nb}'")
        return count

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks.

        Returns:
            A list of message strings prefixed with "ERROR:" or "WARNING:".
            An empty list means no problems were detected.
        """
        problems = list(self._load_problems)
        lines = self.all_line_names()

        # 1. Coverage of representative stations on main lines.
        for line, reps in REPRESENTATIVE_STATIONS.items():
            if line not in lines:
                problems.append(f"ERROR: main line '{line}' has no data")
            for rep in reps:
                if rep not in self.station_to_number:
                    problems.append(
                        f"ERROR: representative station '{rep}' of {line} is missing")

        # 2. Connection relationship integrity.
        for name in sorted(self._undeclared_stations):
            problems.append(
                f"WARNING: station '{name}' is used by connections but not declared in stations")
        for rec in self.connections:
            for end in (rec["source"], rec["dest"]):
                if end in self._declared_stations:
                    declared = self._declared_lines.get(end, [])
                    if rec["line"] not in declared:
                        problems.append(
                            f"WARNING: connection {rec['source']}-{rec['dest']} is on "
                            f"'{rec['line']}' but station '{end}' does not list that line")
        seen = set()
        for rec in self.connections:
            key = (tuple(sorted((rec["source"], rec["dest"]))), rec["line"])
            if key in seen:
                problems.append(
                    f"WARNING: duplicate connection {rec['source']}-{rec['dest']} on {rec['line']}")
            seen.add(key)
        for name, number in self.station_to_number.items():
            if not self.graph.adjacent(number):
                problems.append(f"WARNING: station '{name}' has no connections")
        n = len(self.number_to_name)
        visited = set()
        components = 0
        for start in range(n):
            if start in visited:
                continue
            components += 1
            visited.add(start)
            queue = deque([start])
            while queue:
                v = queue.popleft()
                for edge in self.graph.adjacent(v):
                    w = edge.other(v)
                    if w not in visited:
                        visited.add(w)
                        queue.append(w)
        if components > 1:
            problems.append(f"WARNING: network has {components} disconnected components")

        # 3. Distance accuracy.
        for rec in self.connections:
            d = rec["distance"]
            label = f"{rec['source']}-{rec['dest']} ({rec['line']})"
            if not isinstance(d, int):
                problems.append(f"ERROR: distance of {label} is not an integer number of meters")
            if d < MIN_PLAUSIBLE_DISTANCE_M or d > MAX_PLAUSIBLE_DISTANCE_M:
                problems.append(
                    f"WARNING: distance of {label} = {d} m is outside the plausible range")
        return problems
