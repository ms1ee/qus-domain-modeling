"""Subway network model.

``SubwayNetwork`` builds the weighted undirected ``Graph`` from the dataset,
assigns station numbers, keeps the station-name/number mappings and the
ordered station sequence of every line, and offers data update operations
(adding lines, modifying stations, updating distances).
"""

from data_loader import load_subway_data
from models import Edge, Graph


def _clean_name(value):
    """Collapse whitespace and convert the value to a clean string."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _unique_clean(values):
    """Clean a list of strings and drop empty and duplicate entries."""
    result = []
    for value in values:
        cleaned = _clean_name(value)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _normalize_key(name):
    """Normalization used for station name matching (case/space insensitive)."""
    return "".join(str(name).split()).lower()


class SubwayNetwork:
    """Graph-based model of the Beijing Subway network.

    Attributes:
        graph: the ``Graph`` instance (vertices are station numbers).
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        line_stations: dict line name -> ordered list of station names.
        build_warnings: list of non-fatal problems found while loading data.
    """

    def __init__(self, data=None):
        if data is None:
            data = load_subway_data()
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.line_stations = {}
        self.build_warnings = []
        self._next_number = 0
        self._build(data)

    # ----- construction -------------------------------------------------
    def _build(self, data):
        """Populate stations, lines and edges from the raw dataset dict."""
        for record in data.get("stations") or []:
            if not isinstance(record, dict):
                self.build_warnings.append(f"malformed station record skipped: {record!r}")
                continue
            name = _clean_name(record.get("name"))
            if not name:
                self.build_warnings.append("station record without a name was skipped")
                continue
            lines = _unique_clean(record.get("lines") or [])
            if name in self.station_to_number:
                existing = self.graph.get_station_lines(name)
                self.build_warnings.append(
                    f"duplicate station record '{name}', line lists were merged"
                )
                lines = existing + [line for line in lines if line not in existing]
            self._ensure_station(name)
            self.graph.set_station_lines(name, lines)

        for conn in data.get("connections") or []:
            try:
                src = _clean_name(conn["source"])
                dst = _clean_name(conn["dest"])
                line = _clean_name(conn["line"])
                distance = int(conn["distance"])
            except (KeyError, TypeError, ValueError):
                self.build_warnings.append(f"malformed connection skipped: {conn!r}")
                continue
            if not src or not dst or src == dst:
                self.build_warnings.append(f"invalid connection skipped: {conn!r}")
                continue

            for name in (src, dst):
                if name not in self.station_to_number:
                    self.build_warnings.append(
                        f"connection references unlisted station '{name}'; "
                        "it was added without line information"
                    )
                    self._ensure_station(name)

            src_num = self.station_to_number[src]
            dst_num = self.station_to_number[dst]
            self.graph.add_edge(Edge(src_num, dst_num, distance, line))
            self._register_line_station(line, src)
            self._register_line_station(line, dst)

    def _ensure_station(self, name):
        """Return the number of a station, creating it when needed."""
        number = self.station_to_number.get(name)
        if number is not None:
            return number
        number = self._next_number
        self._next_number += 1
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.graph.add_node(number)
        self.graph.set_station_lines(name, [])
        return number

    def _register_line_station(self, line, name):
        """Record that a station is served by a line, in line order of appearance."""
        members = self.line_stations.setdefault(line, [])
        if name not in members:
            members.append(name)
        if line not in self.graph.get_station_lines(name):
            self.build_warnings.append(
                f"station '{name}' is on line '{line}' in connections but its "
                "line list did not include it; it was added"
            )
            current = self.graph.get_station_lines(name)
            current.append(line)
            self.graph.set_station_lines(name, current)

    # ----- lookup helpers -----------------------------------------------
    def resolve_station(self, query):
        """Standardize a user-supplied station name.

        Matching ignores case and whitespace, and accepts names with or
        without the trailing '站' (station) character. Returns the official
        station name, or None if no station matches.
        """
        if query is None:
            return None
        key = _normalize_key(query)
        if not key:
            return None

        index = {}
        for name in self.station_to_number:
            index.setdefault(_normalize_key(name), name)

        if key in index:
            return index[key]
        if key.endswith("站"):
            alternative = key[:-1]
        else:
            alternative = key + "站"
        if alternative in index:
            return index[alternative]
        return None

    def get_station_number(self, name):
        """Return the station number of an official station name."""
        if name not in self.station_to_number:
            raise ValueError(f"unknown station '{name}'")
        return self.station_to_number[name]

    def get_station_name(self, number):
        """Return the official station name of a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def line_names(self):
        """Return all known line names sorted alphabetically."""
        names = set(self.line_stations)
        for lines in self.graph.station_lines.values():
            names.update(lines)
        return sorted(names)

    def get_line_stations(self, line):
        """Return the ordered list of station names served by a line."""
        return list(self.line_stations.get(line, []))

    def transfer_stations(self):
        """Return sorted names of multi-line interchange stations."""
        return sorted(
            name for name, lines in self.graph.station_lines.items() if len(lines) > 1
        )

    # ----- data update operations --------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line.

        Args:
            line_name: name of the new line; must not already exist.
            station_names: ordered list of station names on the line.
            distances: distances in meters between consecutive stations
                (length must be ``len(station_names) - 1``).
        Unknown stations are created; existing stations keep their numbers.
        """
        line = _clean_name(line_name)
        if not line:
            raise ValueError("line name must not be empty")
        if line in self.line_stations:
            raise ValueError(f"line '{line}' already exists")
        names = [_clean_name(name) for name in station_names]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if any(not name for name in names):
            raise ValueError("station names must not be empty")
        if len(set(names)) != len(names):
            raise ValueError("station names on a line must be unique")
        if len(distances) != len(names) - 1:
            raise ValueError("expected one distance per pair of consecutive stations")
        dists = []
        for value in distances:
            distance = int(value)
            if distance <= 0:
                raise ValueError("distances must be positive")
            dists.append(distance)

        numbers = [self._ensure_station(name) for name in names]
        for name in names:
            current = self.graph.get_station_lines(name)
            if line not in current:
                current.append(line)
                self.graph.set_station_lines(name, current)
        for i, distance in enumerate(dists):
            self.graph.add_edge(Edge(numbers[i], numbers[i + 1], distance, line))
        self.line_stations[line] = list(names)

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its list of lines.

        Returns the (possibly new) official name of the station.
        """
        canonical = self.resolve_station(name)
        if canonical is None:
            raise ValueError(f"unknown station '{name}'")
        number = self.station_to_number[canonical]
        target = canonical

        if new_name is not None:
            target = _clean_name(new_name)
            if not target:
                raise ValueError("new station name must not be empty")
            if target != canonical:
                if target in self.station_to_number:
                    raise ValueError(f"station '{target}' already exists")
                del self.station_to_number[canonical]
                self.station_to_number[target] = number
                self.number_to_station[number] = target
                self.graph.station_lines[target] = self.graph.station_lines.pop(canonical)
                for line, members in self.line_stations.items():
                    self.line_stations[line] = [
                        target if member == canonical else member for member in members
                    ]

        if lines is not None:
            self.graph.set_station_lines(target, _unique_clean(lines))
        return target

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance between two adjacent stations.

        Args:
            station_a, station_b: official station names.
            distance: new distance in meters (positive integer).
            line: optionally restrict the update to connections of one line.
        Returns the number of edges updated.
        """
        name_a = self.resolve_station(station_a)
        name_b = self.resolve_station(station_b)
        if name_a is None or name_b is None:
            raise ValueError("both stations must exist")
        value = int(distance)
        if value <= 0:
            raise ValueError("distance must be a positive number of meters")
        edges = self.graph.edges_between(
            self.station_to_number[name_a], self.station_to_number[name_b]
        )
        if line:
            edges = [edge for edge in edges if edge.line == line]
        if not edges:
            raise ValueError(f"no connection between '{name_a}' and '{name_b}'")
        for edge in edges:
            edge.distance = value
        return len(edges)
