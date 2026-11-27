"""Subway network modeling and data management.

This module builds the weighted graph from the dataset, assigns integer
station numbers, resolves user-supplied station names, supports data updates
(adding lines, modifying stations, updating distances), persists changes, and
runs data integrity checks.
"""

import difflib
import re
import unicodedata

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

# Main lines that must be present in the dataset.
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations used for coverage checks (warnings only).
REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "西单", "国贸"],
    "Line 2": ["西直门", "东直门"],
    "Line 4": ["圆明园"],
    "Line 5": ["宋家庄"],
    "Line 6": ["南锣鼓巷"],
    "Line 8": ["鼓楼大街"],
    "Line 10": ["国贸"],
    "Line 13": ["大钟寺"],
}

MAX_REASONABLE_DISTANCE_M = 5000
MIN_REASONABLE_DISTANCE_M = 100
_NAME_SUFFIXES = ("station", "站")


class StationNotFoundError(ValueError):
    """Raised when a station name does not match any official station."""

    def __init__(self, name, suggestions=None):
        super().__init__(f"Station '{name}' does not exist")
        self.name = name
        self.suggestions = list(suggestions or [])


def _clean(value):
    """Return a stripped string, or an empty string for non-string values."""
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_station_name(name):
    """Return a canonical lookup key for a station name.

    The key ignores case, whitespace, hyphens/underscores, full-width variants
    and a trailing "station" or "站" suffix.
    """
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    text = re.sub(r"[\s_\-]+", "", text)
    for suffix in _NAME_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    return text


def _validate_distance(value):
    """Convert a distance value to a positive integer number of meters."""
    if isinstance(value, bool):
        raise ValueError(f"Invalid distance: {value!r}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid distance: {value!r}") from exc
    if number <= 0 or (isinstance(value, float) and value != number):
        raise ValueError(f"Distance must be a positive integer number of meters, got {value!r}")
    return number


class SubwayNetwork:
    """Subway network model built from the dataset.

    Attributes:
        data: The raw dataset dict (source of truth for updates).
        data_path: File path used when saving.
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
        graph: The Graph instance built from the dataset.
    """

    def __init__(self, data=None, data_path=DATA_FILE_PATH):
        if data is None:
            data = load_subway_data(data_path)
        self.data = data
        self.data_path = data_path
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self._name_index = {}
        self.rebuild()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def rebuild(self):
        """(Re)build the graph and lookup tables from ``self.data``."""
        station_lines = {}

        # Stations declared in the station list (order preserved).
        for entry in self.data.get("stations", []):
            if not isinstance(entry, dict):
                continue
            name = _clean(entry.get("name"))
            if not name:
                continue
            lines = station_lines.setdefault(name, [])
            for line in entry.get("lines") or []:
                line = _clean(line)
                if line and line not in lines:
                    lines.append(line)

        # Stations that appear only in connections are added with their connection line.
        connections = [c for c in self.data.get("connections", []) if isinstance(c, dict)]
        for conn in connections:
            line = _clean(conn.get("line"))
            for key in ("source", "dest"):
                name = _clean(conn.get(key))
                if name and name not in station_lines:
                    station_lines[name] = [line] if line else []

        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for number, (name, lines) in enumerate(station_lines.items()):
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, lines)

        for conn in connections:
            src = self.station_to_number.get(_clean(conn.get("source")))
            dst = self.station_to_number.get(_clean(conn.get("dest")))
            if src is None or dst is None or src == dst:
                continue
            try:
                distance = int(conn.get("distance"))
            except (TypeError, ValueError):
                continue
            if distance < 0:
                continue
            self.graph.add_edge(Edge(src, dst, distance, _clean(conn.get("line"))))

        self._name_index = {}
        for name in self.station_to_number:
            self._name_index.setdefault(normalize_station_name(name), name)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def station_names(self):
        """Return all official station names."""
        return list(self.station_to_number.keys())

    def resolve_station(self, name):
        """Map a user-supplied name to the official station name.

        Raises:
            StationNotFoundError: If no station matches; includes suggestions.
        """
        if not isinstance(name, str):
            raise StationNotFoundError(str(name))
        stripped = name.strip()
        if stripped in self.station_to_number:
            return stripped
        key = normalize_station_name(stripped)
        if key in self._name_index:
            return self._name_index[key]
        raise StationNotFoundError(stripped, self.suggest(stripped))

    def suggest(self, name, limit=3):
        """Return up to ``limit`` official station names similar to ``name``."""
        key = normalize_station_name(name)
        matches = difflib.get_close_matches(key, list(self._name_index.keys()), n=limit, cutoff=0.6)
        return [self._name_index[m] for m in matches]

    def station_number(self, name):
        """Return the station number for an official or user-supplied name."""
        return self.station_to_number[self.resolve_station(name)]

    def station_name(self, number):
        """Return the official station name for a station number."""
        return self.number_to_station[number]

    def station_lines(self, name):
        """Return the lines serving a station."""
        return self.graph.get_station_lines(self.resolve_station(name))

    def line_stations(self):
        """Return a dict mapping line name -> sorted list of station names."""
        result = {}
        for name, lines in self.graph.station_lines.items():
            for line in lines:
                result.setdefault(line, set()).add(name)
        for conn in self.data.get("connections", []):
            if not isinstance(conn, dict):
                continue
            line = _clean(conn.get("line"))
            if not line:
                continue
            for key in ("source", "dest"):
                name = _clean(conn.get(key))
                if name in self.station_to_number:
                    result.setdefault(line, set()).add(name)
        return {line: sorted(names) for line, names in result.items()}

    def line_names(self):
        """Return the sorted list of all line names."""
        return sorted(self.line_stations().keys())

    def transfer_stations(self):
        """Return a dict of interchange stations (name -> lines) serving more than one line."""
        return {
            name: list(lines)
            for name, lines in self.graph.station_lines.items()
            if len(lines) > 1
        }

    # ------------------------------------------------------------------
    # Data updates
    # ------------------------------------------------------------------
    def _find_station_entry(self, name):
        """Return the station record dict for ``name`` or None."""
        for entry in self.data.get("stations", []):
            if isinstance(entry, dict) and _clean(entry.get("name")) == name:
                return entry
        return None

    def add_line(self, line_name, station_names, distances):
        """Add a new line described by an ordered station list and segment distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line.
            distances: Distances in meters between consecutive stations
                (length must be len(station_names) - 1).

        Returns:
            The canonical ordered list of station names on the new line.

        Raises:
            ValueError: On invalid or conflicting input.
        """
        line_name = _clean(line_name)
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")

        names = []
        for raw in station_names:
            name = _clean(raw)
            if not name:
                raise ValueError("Station names must not be empty")
            try:
                canonical = self.resolve_station(name)
            except StationNotFoundError:
                canonical = name
            if canonical in names:
                raise ValueError(f"Station '{canonical}' appears more than once on the line")
            names.append(canonical)

        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        distances = list(distances)
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        parsed = [_validate_distance(d) for d in distances]

        stations = self.data.setdefault("stations", [])
        connections = self.data.setdefault("connections", [])
        for name in names:
            entry = self._find_station_entry(name)
            if entry is None:
                stations.append({"name": name, "lines": [line_name]})
            else:
                lines = entry.setdefault("lines", [])
                if line_name not in lines:
                    lines.append(line_name)

        for index, distance in enumerate(parsed):
            connections.append({
                "source": names[index],
                "dest": names[index + 1],
                "distance": distance,
                "line": line_name,
            })

        self.rebuild()
        return names

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or line affiliations.

        Args:
            name: Existing station name (user input is resolved).
            new_name: Optional new official name.
            lines: Optional new list of line names.

        Returns:
            The final station name.
        """
        canonical = self.resolve_station(name)
        stations = self.data.setdefault("stations", [])
        entry = self._find_station_entry(canonical)
        if entry is None:
            entry = {"name": canonical, "lines": []}
            stations.append(entry)

        if lines is not None:
            cleaned = []
            for line in lines:
                value = _clean(line)
                if value and value not in cleaned:
                    cleaned.append(value)
            entry["lines"] = cleaned

        target = canonical
        if new_name is not None:
            target = _clean(new_name)
            if not target:
                raise ValueError("New station name must not be empty")
            if target != canonical:
                key = normalize_station_name(target)
                if key in self._name_index and self._name_index[key] != canonical:
                    raise ValueError(f"Station name '{target}' already exists")
                entry["name"] = target
                for conn in self.data.get("connections", []):
                    if not isinstance(conn, dict):
                        continue
                    if _clean(conn.get("source")) == canonical:
                        conn["source"] = target
                    if _clean(conn.get("dest")) == canonical:
                        conn["dest"] = target

        self.rebuild()
        return target

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        Args:
            source: One station name.
            dest: The adjacent station name.
            distance: New distance in meters (positive integer).
            line: Optional line name to restrict the update.

        Returns:
            The number of connection records updated.

        Raises:
            ValueError: If no matching connection exists or distance is invalid.
        """
        src = self.resolve_station(source)
        dst = self.resolve_station(dest)
        value = _validate_distance(distance)
        count = 0
        for conn in self.data.get("connections", []):
            if not isinstance(conn, dict):
                continue
            pair = (_clean(conn.get("source")), _clean(conn.get("dest")))
            if set(pair) != {src, dst}:
                continue
            if line is not None and _clean(conn.get("line")) != _clean(line):
                continue
            conn["distance"] = value
            count += 1
        if count == 0:
            raise ValueError(f"No connection found between '{src}' and '{dst}'")
        self.rebuild()
        return count

    def save(self, path=None):
        """Persist the current dataset to ``path`` (defaults to the loaded file)."""
        save_subway_data(self.data, path or self.data_path)

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks.

        Checks performed:
            * Coverage: main lines exist and representative stations are present.
            * Records: station names are unique and well formed.
            * Connections: endpoints exist, lines are valid, distances are sane.
            * Connectivity: each line forms a connected chain; no isolated stations.

        Returns:
            dict with keys "ok" (bool), "errors" (list[str]), "warnings" (list[str]),
            "station_count", "connection_count" and "line_count".
        """
        errors = []
        warnings = []

        stations_data = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        declared = set()
        record_lines = {}
        for index, entry in enumerate(stations_data):
            if not isinstance(entry, dict):
                errors.append(f"Station record #{index} is not an object")
                continue
            raw_name = entry.get("name")
            name = _clean(raw_name)
            if not name:
                errors.append(f"Station record #{index} has no name")
                continue
            if raw_name != name:
                warnings.append(f"Station name '{raw_name}' has leading or trailing whitespace")
            if name in declared:
                errors.append(f"Duplicate station record for '{name}'")
            declared.add(name)
            lines = entry.get("lines")
            if not isinstance(lines, list) or not lines:
                warnings.append(f"Station '{name}' has no line affiliation")
                lines = []
            record_lines[name] = {_clean(l) for l in lines}

        # Coverage checks.
        lines_map = self.line_stations()
        for line in MAIN_LINES:
            if not lines_map.get(line):
                errors.append(f"Main line '{line}' is missing from the dataset")
        normalized_present = {normalize_station_name(n) for n in declared}
        for line, reps in REPRESENTATIVE_STATIONS.items():
            for rep in reps:
                if normalize_station_name(rep) not in normalized_present:
                    warnings.append(f"Representative station '{rep}' of {line} is not in the dataset")

        # Connection checks.
        pair_counts = {}
        valid_adjacency = {}
        for index, conn in enumerate(connections):
            label = f"Connection #{index}"
            if not isinstance(conn, dict):
                errors.append(f"{label} is not an object")
                continue
            src = _clean(conn.get("source"))
            dst = _clean(conn.get("dest"))
            line = _clean(conn.get("line"))
            if not src or not dst:
                errors.append(f"{label} is missing its source or dest station")
                continue
            if src == dst:
                errors.append(f"{label} connects station '{src}' to itself")
            if src not in declared:
                errors.append(f"{label}: station '{src}' is not in the station list")
            if dst not in declared:
                errors.append(f"{label}: station '{dst}' is not in the station list")
            if not line:
                errors.append(f"{label} ({src} - {dst}) has no line")

            distance = conn.get("distance")
            distance_ok = False
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                errors.append(f"{label} ({src} - {dst}) has a non-numeric distance {distance!r}")
            elif distance <= 0:
                errors.append(f"{label} ({src} - {dst}) has a non-positive distance {distance}")
            else:
                distance_ok = True
                if isinstance(distance, float) and distance != int(distance):
                    warnings.append(f"{label} ({src} - {dst}) has a fractional distance {distance}")
                if distance > MAX_REASONABLE_DISTANCE_M:
                    warnings.append(f"{label} ({src} - {dst}) distance {distance} m seems too large")
                elif distance < MIN_REASONABLE_DISTANCE_M:
                    warnings.append(f"{label} ({src} - {dst}) distance {distance} m seems too small")

            for name in (src, dst):
                if line and name in record_lines and line not in record_lines[name]:
                    warnings.append(f"Station '{name}' does not list line '{line}' in its line affiliations")

            key = (frozenset((src, dst)), line)
            pair_counts[key] = pair_counts.get(key, 0) + 1

            if distance_ok and src != dst and src in declared and dst in declared and line:
                valid_adjacency.setdefault(line, {}).setdefault(src, set()).add(dst)
                valid_adjacency[line].setdefault(dst, set()).add(src)

        for (pair, line), count in pair_counts.items():
            if count > 1:
                names = " - ".join(sorted(pair))
                warnings.append(f"Duplicate connection {names} on line '{line}' ({count} records)")

        # Connectivity checks per line.
        for line, names in lines_map.items():
            adjacency = valid_adjacency.get(line, {})
            visited = set()
            components = 0
            for start in names:
                if start in visited:
                    continue
                components += 1
                queue = [start]
                visited.add(start)
                while queue:
                    current = queue.pop()
                    for neighbor in adjacency.get(current, ()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
            if components > 1:
                warnings.append(f"Line '{line}' is split into {components} disconnected segments")

        for name, number in self.station_to_number.items():
            if not self.graph.adjacent(number):
                warnings.append(f"Station '{name}' has no connections")

        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "station_count": len(self.station_to_number),
            "connection_count": self.graph.edge_count(),
            "line_count": len(lines_map),
        }
