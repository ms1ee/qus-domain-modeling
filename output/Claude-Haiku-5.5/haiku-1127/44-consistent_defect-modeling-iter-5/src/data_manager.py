"""Subway network data management.

Builds the weighted directed graph from subway_data.json, performs data
integrity checks, supports data updates (adding lines, modifying stations,
updating distances) and resolves user-entered station names.
"""

import difflib
from collections import deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph
from subway_errors import DataError, DataUpdateError, StationNotFoundError

# Main lines that must be represented in the dataset (PRD 4.1).
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000
FUZZY_MATCH_CUTOFF = 0.5


def clean_name(name):
    """Normalise whitespace of a name and convert None to an empty string."""
    if name is None:
        return ""
    return " ".join(str(name).split())


def normalize_name(name):
    """Normalise a name for case-insensitive comparison."""
    return clean_name(name).casefold()


def resolve_station_name(query, station_names):
    """Resolve a user-entered station name to an official station name.

    Matching order: exact (case-insensitive, whitespace-normalised), then the
    nearest name by sequence similarity.

    Returns:
        tuple: (official station name, True if matched exactly, False if fuzzy-matched).

    Raises:
        StationNotFoundError: If no station is similar enough to the query.
    """
    q = normalize_name(query)
    lookup = {}
    for name in station_names:
        lookup.setdefault(normalize_name(name), name)
    if not q or not lookup:
        raise StationNotFoundError(query)
    if q in lookup:
        return lookup[q], True
    matches = difflib.get_close_matches(q, list(lookup.keys()), n=1, cutoff=FUZZY_MATCH_CUTOFF)
    if matches:
        return lookup[matches[0]], False
    raise StationNotFoundError(query)


class SubwayNetwork:
    """In-memory subway network: raw dataset plus the derived graph.

    Args:
        data_path: Path of the dataset file (used for loading and saving).
        data: Optional already-loaded dataset dictionary. If given, no file is read.
    """

    def __init__(self, data_path=DATA_FILE_PATH, data=None):
        self.data_path = data_path
        self.data = data if data is not None else load_subway_data(data_path)
        self.graph = Graph()
        self.build_graph()

    # ----- graph construction -------------------------------------------------
    def build_graph(self):
        """(Re)build the weighted directed graph from the raw dataset.

        Station numbers are assigned here (the Graph does not assign them).
        Every connection is added in its listed direction only.

        Returns:
            Graph: The newly built graph (also stored in self.graph).

        Raises:
            DataError: If a connection has an invalid distance.
        """
        stations_data = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        station_lines = {}
        order = []

        def ensure(name):
            if name not in station_lines:
                station_lines[name] = []
                order.append(name)
            return station_lines[name]

        def attach(name, line):
            lines = ensure(name)
            if line and line not in lines:
                lines.append(line)

        for rec in stations_data:
            name = clean_name(rec.get("name"))
            if not name:
                continue
            ensure(name)
            for line in rec.get("lines", []) or []:
                attach(name, clean_name(line))

        for conn in connections:
            src = clean_name(conn.get("source"))
            dst = clean_name(conn.get("dest"))
            line = clean_name(conn.get("line"))
            if not src or not dst:
                continue
            attach(src, line)
            attach(dst, line)

        graph = Graph()
        for number, name in enumerate(order):
            graph.add_station(name, number)
            graph.set_station_lines(name, station_lines[name])

        for conn in connections:
            src = clean_name(conn.get("source"))
            dst = clean_name(conn.get("dest"))
            line = clean_name(conn.get("line"))
            if not src or not dst or src == dst:
                continue
            try:
                distance = float(conn["distance"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DataError(f"Invalid distance in connection {src} -> {dst}") from exc
            graph.add_edge(Edge(graph.number_of(src), graph.number_of(dst), distance, line))

        self.graph = graph
        return graph

    # ----- queries ------------------------------------------------------------
    def station_names(self):
        """Return all official station names."""
        return list(self.graph.station_to_number.keys())

    def line_names(self):
        """Return all line names present in the network (sorted)."""
        names = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        return sorted(names)

    # ----- integrity checks ---------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks.

        Checks station coverage of the main lines, connection consistency
        (endpoints, lines, direction pairs, duplicates) and distance accuracy
        (plausible range), plus basic graph connectivity.

        Returns:
            dict: {"errors": [str, ...], "warnings": [str, ...]}
        """
        errors = []
        warnings = []
        stations_data = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        # Station records
        station_record_names = set()
        for rec in stations_data:
            name = clean_name(rec.get("name"))
            if not name:
                errors.append("Station record without a name found")
                continue
            if name in station_record_names:
                errors.append(f"Duplicate station name: '{name}'")
            station_record_names.add(name)
            if not rec.get("lines"):
                warnings.append(f"Station '{name}' has no line information")

        # Coverage of main lines
        line_stations = {}
        for name, lines in self.graph.station_lines.items():
            for line in lines:
                line_stations.setdefault(line, set()).add(name)
        for line in MAIN_LINES:
            count = len(line_stations.get(line, ()))
            if count == 0:
                errors.append(f"Main line '{line}' has no stations in the dataset")
            elif count < 2:
                warnings.append(f"Main line '{line}' has only {count} station(s)")

        # Connection integrity and distance accuracy
        seen = set()
        for idx, conn in enumerate(connections):
            label = f"connection #{idx}"
            if not isinstance(conn, dict):
                errors.append(f"{label}: not an object")
                continue
            missing = [k for k in ("source", "dest", "distance", "line") if k not in conn]
            if missing:
                errors.append(f"{label}: missing fields {missing}")
                continue
            src = clean_name(conn["source"])
            dst = clean_name(conn["dest"])
            line = clean_name(conn["line"])
            label = f"connection {src} -> {dst} ({line})"

            if src not in station_record_names:
                errors.append(f"{label}: source station is not in the station list")
            if dst not in station_record_names:
                errors.append(f"{label}: destination station is not in the station list")
            if src == dst:
                errors.append(f"{label}: self-loop is not allowed")

            dist = conn["distance"]
            if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
                errors.append(f"{label}: distance must be a positive number, got {dist!r}")
            elif dist < MIN_PLAUSIBLE_DISTANCE_M or dist > MAX_PLAUSIBLE_DISTANCE_M:
                warnings.append(f"{label}: distance {dist} m is outside the plausible range "
                                f"({MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m)")

            for endpoint in (src, dst):
                if line not in self.graph.station_lines.get(endpoint, []):
                    warnings.append(f"{label}: station '{endpoint}' is not listed as served by '{line}'")

            key = (src, dst, line)
            if key in seen:
                warnings.append(f"{label}: duplicate connection")
            seen.add(key)

        for (src, dst, line) in seen:
            if (dst, src, line) not in seen and src != dst:
                warnings.append(f"connection {src} -> {dst} ({line}): reverse direction is not listed")

        # Stations without connections
        connected = set()
        for conn in connections:
            if isinstance(conn, dict):
                connected.add(clean_name(conn.get("source")))
                connected.add(clean_name(conn.get("dest")))
        for name in sorted(station_record_names):
            if name not in connected:
                warnings.append(f"Station '{name}' has no connections")

        # Connectivity (undirected view of the directed graph)
        undirected = {n: set() for n in self.graph.adjacency}
        for number, edge_list in self.graph.adjacency.items():
            for edge in edge_list:
                undirected[edge.source].add(edge.dest)
                undirected[edge.dest].add(edge.source)
        visited = set()
        components = 0
        for start in undirected:
            if start in visited:
                continue
            components += 1
            queue = deque([start])
            visited.add(start)
            while queue:
                node = queue.popleft()
                for nxt in undirected[node]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
        if components > 1:
            warnings.append(f"Network is split into {components} disconnected components")

        return {"errors": errors, "warnings": warnings}

    # ----- data updates -------------------------------------------------------
    def _find_station_record(self, name):
        for rec in self.data.setdefault("stations", []):
            if clean_name(rec.get("name")) == name:
                return rec
        return None

    def add_line(self, line_name, station_names, distances_m):
        """Add a new line with its ordered station sequence and bidirectional connections.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line.
            distances_m: List of distances (meters) between consecutive stations.

        Raises:
            DataUpdateError: If the input is invalid or the line already exists.
        """
        line = clean_name(line_name)
        names = [clean_name(n) for n in station_names]
        if not line:
            raise DataUpdateError("Line name must not be empty")
        if line in self.line_names():
            raise DataUpdateError(f"Line '{line}' already exists")
        if len(names) < 2:
            raise DataUpdateError("A line needs at least two stations")
        if len(set(names)) != len(names):
            raise DataUpdateError("Station sequence contains duplicates")
        if len(distances_m) != len(names) - 1:
            raise DataUpdateError("Number of distances must equal number of stations minus one")
        for dist in distances_m:
            if not isinstance(dist, (int, float)) or dist <= 0:
                raise DataUpdateError(f"Invalid distance: {dist!r}")

        stations = self.data.setdefault("stations", [])
        by_name = {clean_name(rec.get("name")): rec for rec in stations}
        for name in names:
            rec = by_name.get(name)
            if rec is None:
                rec = {"name": name, "lines": [line]}
                stations.append(rec)
                by_name[name] = rec
            else:
                rec.setdefault("lines", [])
                if line not in rec["lines"]:
                    rec["lines"].append(line)

        connections = self.data.setdefault("connections", [])
        for i, dist in enumerate(distances_m):
            a, b = names[i], names[i + 1]
            connections.append({"source": a, "dest": b, "distance": int(dist), "line": line})
            connections.append({"source": b, "dest": a, "distance": int(dist), "line": line})
        self.build_graph()

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list.

        Raises:
            StationNotFoundError: If the station does not exist.
            DataUpdateError: If the new name already exists.
        """
        old = clean_name(old_name)
        if not self.graph.has_station(old):
            raise StationNotFoundError(old)
        rec = self._find_station_record(old)
        if rec is None:
            rec = {"name": old, "lines": []}
            self.data["stations"].append(rec)

        if new_name is not None:
            new = clean_name(new_name)
            if not new:
                raise DataUpdateError("New station name must not be empty")
            if new != old and self.graph.has_station(new):
                raise DataUpdateError(f"Station '{new}' already exists")
            rec["name"] = new
            for conn in self.data.get("connections", []):
                if clean_name(conn.get("source")) == old:
                    conn["source"] = new
                if clean_name(conn.get("dest")) == old:
                    conn["dest"] = new

        if lines is not None:
            unique = []
            for line in lines:
                cleaned = clean_name(line)
                if cleaned and cleaned not in unique:
                    unique.append(cleaned)
            rec["lines"] = unique
        self.build_graph()

    def update_distance(self, a, b, distance_m):
        """Update the distance of the connection(s) between two adjacent stations (both directions).

        Raises:
            DataUpdateError: If the distance is invalid or no connection exists.
        """
        if not isinstance(distance_m, (int, float)) or distance_m <= 0:
            raise DataUpdateError(f"Invalid distance: {distance_m!r}")
        a_name = clean_name(a)
        b_name = clean_name(b)
        changed = 0
        for conn in self.data.get("connections", []):
            src = clean_name(conn.get("source"))
            dst = clean_name(conn.get("dest"))
            if (src == a_name and dst == b_name) or (src == b_name and dst == a_name):
                conn["distance"] = int(distance_m)
                changed += 1
        if changed == 0:
            raise DataUpdateError(f"No connection found between '{a_name}' and '{b_name}'")
        self.build_graph()

    def save(self, path=None):
        """Persist the dataset to a JSON file (defaults to the loaded path)."""
        save_subway_data(self.data, path or self.data_path)
