"""Subway network model: station numbering, graph construction and data management."""

import copy
import difflib

from data_loader import save_subway_data
from errors import UnknownStationError
from models import Edge, Graph


def normalize_name(name):
    """Normalize a station or line name for case/whitespace-insensitive matching."""
    text = str(name).replace("\u3000", " ")
    return " ".join(text.split()).casefold()


class SubwayNetwork:
    """Holds the raw subway dataset and the derived graph.

    The graph is rebuilt automatically after every data update. Station
    numbers are assigned here (the caller), not by Graph.
    """

    def __init__(self, data):
        self._data = copy.deepcopy(data)
        self._rebuild()

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------
    @property
    def raw_data(self):
        """Read-only view of the internal dataset (do not mutate directly)."""
        return self._data

    @property
    def data(self):
        """Deep copy of the dataset."""
        return copy.deepcopy(self._data)

    def station_names(self):
        """Return all station names in numbering order."""
        return list(self.number_to_name)

    def line_names(self):
        """Return all line names sorted alphabetically."""
        return sorted(self.line_stations.keys())

    def get_number(self, name):
        """Return the station number for an exact canonical station name."""
        try:
            return self.station_to_number[name]
        except KeyError as exc:
            raise UnknownStationError(f"unknown station '{name}'") from exc

    def get_name(self, number):
        """Return the station name for a station number."""
        return self.number_to_name[number]

    def resolve_station(self, raw):
        """Resolve user input to an official station name.

        Returns:
            (name, exact) where exact is False if the name was matched by
            similarity to the nearest station.

        Raises:
            UnknownStationError: if no station is similar enough.
        """
        key = normalize_name(raw)
        if not key:
            raise UnknownStationError(str(raw))
        if key in self._normalized:
            return self._normalized[key], True
        if key.endswith("站") and key[:-1] in self._normalized:
            return self._normalized[key[:-1]], True
        matches = difflib.get_close_matches(key, list(self._normalized.keys()), n=1, cutoff=0.6)
        if matches:
            return self._normalized[matches[0]], False
        raise UnknownStationError(str(raw))

    def resolve_line(self, raw):
        """Return the canonical line name matching user input, or None."""
        key = normalize_name(raw)
        if key.isdigit():
            key = f"line {key}"
        for line in self.line_stations:
            if normalize_name(line) == key:
                return line
        return None

    # ------------------------------------------------------------------
    # Data management
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line with consecutive stations and distances (meters).

        Connections are created in both directions. Unknown stations are added.

        Raises:
            ValueError: on duplicate line, too few stations, or invalid distances.
        """
        if self.resolve_line(line_name) is not None:
            raise ValueError(f"line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("number of distances must be one less than number of stations")
        for dist in distances:
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                raise ValueError(f"invalid distance: {dist!r}")

        stations = self._data["stations"]
        entries = {st["name"]: st for st in stations}
        for name in station_names:
            if name not in entries:
                entry = {"name": name, "lines": [line_name]}
                stations.append(entry)
                entries[name] = entry
            elif line_name not in entries[name].setdefault("lines", []):
                entries[name]["lines"].append(line_name)

        connections = self._data["connections"]
        for i, dist in enumerate(distances):
            a, b = station_names[i], station_names[i + 1]
            connections.append({"source": a, "dest": b, "distance": int(dist), "line": line_name})
            connections.append({"source": b, "dest": a, "distance": int(dist), "line": line_name})
        self._rebuild()

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list.

        Raises:
            UnknownStationError: if the station does not exist.
            ValueError: if the new name is already used.
        """
        canonical, _ = self.resolve_station(name)
        entry = self._find_station_entry(canonical)
        if lines is not None:
            entry["lines"] = list(lines)
        if new_name and new_name != canonical:
            if self._find_station_entry(new_name) is not None and new_name != canonical:
                raise ValueError(f"station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in self._data["connections"]:
                if conn["source"] == canonical:
                    conn["source"] = new_name
                if conn["dest"] == canonical:
                    conn["dest"] = new_name
        self._rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations (both directions).

        Raises:
            ValueError: if the distance is invalid or no connection exists.
        """
        src, _ = self.resolve_station(source)
        dst, _ = self.resolve_station(dest)
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"invalid distance: {distance!r}")
        changed = 0
        for conn in self._data["connections"]:
            if line is not None and conn["line"] != line:
                continue
            if (conn["source"], conn["dest"]) in ((src, dst), (dst, src)):
                conn["distance"] = int(distance)
                changed += 1
        if changed == 0:
            raise ValueError(f"no connection found between '{src}' and '{dst}'")
        self._rebuild()

    def save(self, path=None):
        """Persist the current dataset to JSON."""
        if path is None:
            save_subway_data(self._data)
        else:
            save_subway_data(self._data, path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _find_station_entry(self, name):
        for entry in self._data["stations"]:
            if entry["name"] == name:
                return entry
        # Station exists only via connections: create an explicit entry.
        entry = {"name": name, "lines": []}
        if any(c["source"] == name or c["dest"] == name for c in self._data["connections"]):
            self._data["stations"].append(entry)
            return entry
        return None

    def _rebuild(self):
        """Rebuild station numbering, graph and line tables from the dataset."""
        names = []
        number = {}
        lines_of = {}

        def ensure(name):
            if name not in number:
                number[name] = len(names)
                names.append(name)
                lines_of[name] = []
            return number[name]

        def add_lines(name, line_list):
            for line in line_list:
                if line not in lines_of[name]:
                    lines_of[name].append(line)

        for st in self._data["stations"]:
            name = str(st["name"])
            ensure(name)
            add_lines(name, st.get("lines", []))
        for conn in self._data["connections"]:
            s, d = str(conn["source"]), str(conn["dest"])
            ensure(s)
            ensure(d)
            add_lines(s, [conn["line"]])
            add_lines(d, [conn["line"]])

        graph = Graph()
        for name in names:
            graph.set_station_lines(name, lines_of[name])
        for conn in self._data["connections"]:
            graph.add_edge(Edge(number[str(conn["source"])], number[str(conn["dest"])],
                                conn["distance"], conn["line"]))

        line_stations = {}
        for name in names:
            for line in lines_of[name]:
                line_stations.setdefault(line, []).append(name)

        self.station_to_number = number
        self.number_to_name = names
        self.graph = graph
        self.line_stations = line_stations
        self._normalized = {}
        for name in names:
            self._normalized.setdefault(normalize_name(name), name)
