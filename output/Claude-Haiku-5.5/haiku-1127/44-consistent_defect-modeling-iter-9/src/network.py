"""Subway network construction, station-name resolution and data updates."""

import difflib

from models import DataError, Edge, Graph, Line, Station, StationNotFoundError

# Minimum difflib similarity for an unknown name to be matched to the nearest station.
NAME_MATCH_CUTOFF = 0.6


def normalize_station_name(name):
    """Normalize a station name for lenient comparison (no spaces, lower case)."""
    return "".join(str(name).split()).lower()


class SubwayNetwork:
    """In-memory model of the subway network built from the raw dataset dict.

    Responsibilities:
      * assign numeric identifiers to stations (station_to_number),
      * build the weighted directed Graph,
      * maintain line objects and transfer flags,
      * resolve user-entered station names to official names,
      * support data updates (adding lines, modifying stations, updating distances).
    """

    def __init__(self, data):
        self.data = data
        self._reset()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _reset(self):
        """(Re)build all derived structures from self.data."""
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = {}
        self.stations = {}
        self.lines = {}
        self._normalized = {}
        self._build()

    def _build(self):
        data = self.data
        if not isinstance(data, dict):
            raise DataError("Subway data must be a dictionary")
        try:
            stations_data = data["stations"]
            connections_data = data["connections"]
            for entry in stations_data:
                name = str(entry["name"])
                self._register_station(name)
                for line_name in entry.get("lines", []):
                    self._attach_line(name, str(line_name))

            for conn in connections_data:
                src = str(conn["source"])
                dst = str(conn["dest"])
                line_name = str(conn["line"])
                distance = int(conn["distance"])
                if distance <= 0:
                    raise DataError(f"Non-positive distance between '{src}' and '{dst}'")
                src_no = self._register_station(src)
                dst_no = self._register_station(dst)
                self.graph.add_edge(Edge(src_no, dst_no, distance, line_name))
                self._attach_line(src, line_name)
                self._attach_line(dst, line_name)
        except DataError:
            raise
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise DataError(f"Malformed subway data: {exc}") from exc

        # A station is a transfer station when it is served by more than one line.
        for name, station in self.stations.items():
            station.is_transfer = len(self.graph.station_lines.get(name, [])) > 1

    def _register_station(self, name):
        """Assign a number to a station name if it is new and return its number."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.station_to_number)
        self.station_to_number[name] = number
        self.number_to_name[number] = name
        self.stations[name] = Station(number, name)
        self._normalized.setdefault(normalize_station_name(name), name)
        self.graph.station_lines.setdefault(name, [])
        self.graph.add_node(number)
        return number

    def _attach_line(self, station_name, line_name):
        """Record that a station is served by a line."""
        lines = self.graph.station_lines.setdefault(station_name, [])
        if line_name not in lines:
            lines.append(line_name)
        line = self.lines.setdefault(line_name, Line(line_name))
        line.add_station(station_name)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    def station_number(self, name):
        """Return the numeric identifier of an official station name."""
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{name}' does not exist in the network")
        return self.station_to_number[name]

    def station_name(self, number):
        """Return the official name of a station number."""
        return self.number_to_name[number]

    def line_names(self):
        """Return all line names sorted alphabetically."""
        return sorted(self.lines)

    def resolve_station(self, user_input):
        """Resolve user input to an official station name.

        Resolution order: exact match, whitespace/case-insensitive match,
        then the nearest station by string similarity.

        Raises:
            StationNotFoundError: if no reasonably similar station exists.
        """
        text = (user_input or "").strip()
        if not text:
            raise StationNotFoundError("station name is empty")
        if text in self.station_to_number:
            return text
        key = normalize_station_name(text)
        if key in self._normalized:
            return self._normalized[key]
        matches = difflib.get_close_matches(
            key, list(self._normalized.keys()), n=1, cutoff=NAME_MATCH_CUTOFF
        )
        if not matches:
            raise StationNotFoundError(f"station '{text}' does not exist")
        return self._normalized[matches[0]]

    def _find_entry(self, name):
        """Return the raw station dict for a name, or None."""
        for entry in self.data.get("stations", []):
            if entry.get("name") == name:
                return entry
        return None

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line with an ordered station sequence.

        Args:
            line_name: name of the new line.
            station_names: ordered list of station names (at least two).
            distances: list of distances in meters between consecutive stations.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise DataError("Line name must not be empty")
        if line_name in self.lines:
            raise DataError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise DataError("A new line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise DataError("Number of distances must equal number of stations minus one")
        clean_distances = []
        for distance in distances:
            value = int(distance)
            if value <= 0:
                raise DataError("Distances must be positive")
            clean_distances.append(value)

        for name in station_names:
            entry = self._find_entry(name)
            if entry is None:
                self.data.setdefault("stations", []).append({"name": name, "lines": [line_name]})
            else:
                lines = entry.setdefault("lines", [])
                if line_name not in lines:
                    lines.append(line_name)

        pairs = zip(station_names, station_names[1:], clean_distances)
        for first, second, distance in pairs:
            # A physical line runs both ways, so both directions are added.
            self.data.setdefault("connections", []).append(
                {"source": first, "dest": second, "distance": distance, "line": line_name}
            )
            self.data["connections"].append(
                {"source": second, "dest": first, "distance": distance, "line": line_name}
            )
        self._reset()

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its list of lines."""
        if old_name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{old_name}' does not exist")
        if new_name and new_name != old_name and new_name in self.station_to_number:
            raise DataError(f"Station '{new_name}' already exists")

        entry = self._find_entry(old_name)
        if new_name and new_name != old_name:
            if entry is not None:
                entry["name"] = new_name
            for conn in self.data.get("connections", []):
                if conn.get("source") == old_name:
                    conn["source"] = new_name
                if conn.get("dest") == old_name:
                    conn["dest"] = new_name

        if lines is not None:
            target = new_name or old_name
            if entry is None:
                entry = {"name": target, "lines": []}
                self.data.setdefault("stations", []).append(entry)
            entry["lines"] = [str(item) for item in lines]
        self._reset()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations (both directions).

        Returns:
            int: number of connection records updated.
        """
        value = int(distance)
        if value <= 0:
            raise DataError("Distance must be positive")
        matches = [
            conn
            for conn in self.data.get("connections", [])
            if {conn.get("source"), conn.get("dest")} == {source, dest}
            and (line is None or conn.get("line") == line)
        ]
        if not matches:
            raise DataError(f"No connection between '{source}' and '{dest}'")
        for conn in matches:
            conn["distance"] = value
        self._reset()
        return len(matches)
