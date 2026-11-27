"""Subway network management.

``SubwayNetwork`` builds the weighted directed graph from the dataset, keeps
the station-name <-> station-number registry, performs station name
standardisation and nearest-match lookup, supports data updates (adding lines,
modifying stations, updating distances), and runs data integrity checks.
"""

import difflib
from dataclasses import dataclass, field
from typing import List

from .data_loader import load_subway_data
from .models import DataUpdateError, Edge, Graph, StationNotFoundError

# Main lines that must be represented in the network.
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Distances above this value (meters) are flagged as suspicious.
MAX_REASONABLE_DISTANCE_METERS = 10000
# Minimum similarity ratio for nearest-station matching.
FUZZY_MATCH_CUTOFF = 0.6


def normalize_name(name):
    """Return a canonical form of a station name used for matching.

    Whitespace is removed, case is folded, and a trailing "station" character
    (站) is dropped.
    """
    text = "".join(str(name).split()).casefold()
    if len(text) > 1 and text.endswith("站"):
        text = text[:-1]
    return text


@dataclass
class IntegrityReport:
    """Result of a data integrity check."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors


class SubwayNetwork:
    """The Beijing Subway network: graph, station registry, and lines.

    Attributes:
        graph: ``Graph`` instance keyed by station numbers.
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        lines: dict line name -> set of station names on that line.
    """

    def __init__(self, data=None):
        if data is None:
            data = load_subway_data()
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.lines = {}
        self._normalized = {}   # normalized name -> official name
        self._next_index = 1
        self._build(data)

    # -- construction ---------------------------------------------------------

    def _build(self, data):
        """Populate stations and connections from the dataset dictionary."""
        for item in data.get("stations", []):
            self.add_station(item["name"], item.get("lines", []))
        for conn in data.get("connections", []):
            self._add_connection(
                conn["source"],
                conn["dest"],
                conn["distance"],
                conn["line"],
                bidirectional=bool(conn.get("bidirectional", False)),
            )

    def _new_number(self):
        """Allocate the next station number (e.g. "S001")."""
        number = f"S{self._next_index:03d}"
        self._next_index += 1
        return number

    def add_station(self, name, lines=()):
        """Register a station (or extend an existing station's lines).

        Returns:
            str: The station number.
        """
        name = str(name).strip()
        if not name:
            raise ValueError("station name must not be empty")
        if name not in self.station_to_number:
            number = self._new_number()
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self._normalized.setdefault(normalize_name(name), name)
            self.graph.add_node(number)
            self.graph.set_station_lines(name, [])
        current = list(self.graph.station_lines.get(name, []))
        for line in lines:
            if line not in current:
                current.append(line)
            self.lines.setdefault(line, set()).add(name)
        self.graph.set_station_lines(name, current)
        return self.station_to_number[name]

    def _add_edge_once(self, source_name, dest_name, distance, line):
        """Add a directed edge unless an identical one already exists."""
        src = self.station_to_number[source_name]
        dst = self.station_to_number[dest_name]
        for existing in self.graph.find_edges(src, dst):
            if existing.line == line:
                return
        self.graph.add_edge(Edge(src, dst, distance, line))

    def _add_connection(self, source, dest, distance, line, bidirectional=False):
        """Add a connection between two stations (one or both directions)."""
        self.add_station(source, [line])
        self.add_station(dest, [line])
        self._add_edge_once(source, dest, distance, line)
        if bidirectional:
            self._add_edge_once(dest, source, distance, line)

    # -- lookup -----------------------------------------------------------------

    def station_names(self):
        """Sorted list of all official station names."""
        return sorted(self.station_to_number)

    def has_station(self, name):
        """True if the exact official name exists."""
        return name in self.station_to_number

    def number_of(self, name):
        """Station number for an official name."""
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{name}' does not exist, please check the station name")
        return self.station_to_number[name]

    def name_of(self, number):
        """Official station name for a station number."""
        return self.number_to_station[number]

    def lines_of(self, name):
        """List of lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def line_names(self):
        """Sorted list of all line names."""
        return sorted(self.lines)

    def stations_on_line(self, line):
        """Sorted list of stations on a line."""
        return sorted(self.lines.get(line, set()))

    def transfer_stations(self):
        """Sorted list of stations served by more than one line."""
        return sorted(name for name, lines in self.graph.station_lines.items() if len(lines) > 1)

    def resolve_station(self, name):
        """Standardise a user-supplied station name.

        Returns:
            tuple: ``(official_name, exact_match)`` where ``exact_match`` is
            False if the name was matched to the nearest official station;
            or None if no reasonable match exists.
        """
        text = str(name).strip()
        if text in self.station_to_number:
            return text, True
        normalized = normalize_name(text)
        if normalized in self._normalized:
            return self._normalized[normalized], True
        matches = difflib.get_close_matches(
            normalized, list(self._normalized), n=1, cutoff=FUZZY_MATCH_CUTOFF
        )
        if matches:
            return self._normalized[matches[0]], False
        return None

    # -- data updates -----------------------------------------------------------

    def add_line(self, line_name, stations, distances):
        """Add a new line from an ordered station list and consecutive distances.

        Args:
            line_name: Name of the new line.
            stations: Ordered list of station names.
            distances: Distances in meters between consecutive stations
                (length ``len(stations) - 1``). Connections are bidirectional.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise DataUpdateError("line name must not be empty")
        if line_name in self.lines:
            raise DataUpdateError(f"Line '{line_name}' already exists")
        if len(stations) < 2:
            raise DataUpdateError("a line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise DataUpdateError("distances must have one entry per consecutive station pair")
        for distance in distances:
            if distance <= 0:
                raise DataUpdateError("distances must be positive")
        for name in stations:
            self.add_station(name, [line_name])
        for index, distance in enumerate(distances):
            self._add_connection(stations[index], stations[index + 1], distance,
                                 line_name, bidirectional=True)

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list.

        Returns:
            str: The station's (possibly new) official name.
        """
        if old_name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{old_name}' does not exist")
        number = self.station_to_number[old_name]
        name = old_name

        if new_name and new_name != old_name:
            new_name = str(new_name).strip()
            if new_name in self.station_to_number:
                raise DataUpdateError(f"Station '{new_name}' already exists")
            old_norm = normalize_name(old_name)
            if self._normalized.get(old_norm) == old_name:
                del self._normalized[old_norm]
            self._normalized.setdefault(normalize_name(new_name), new_name)
            del self.station_to_number[old_name]
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            self.graph.station_lines[new_name] = self.graph.station_lines.pop(old_name, [])
            for members in self.lines.values():
                if old_name in members:
                    members.discard(old_name)
                    members.add(new_name)
            name = new_name

        if lines is not None:
            new_lines = list(dict.fromkeys(lines))
            for line in self.graph.station_lines.get(name, []):
                if line not in new_lines and line in self.lines:
                    self.lines[line].discard(name)
                    if not self.lines[line]:
                        del self.lines[line]
            for line in new_lines:
                self.lines.setdefault(line, set()).add(name)
            self.graph.set_station_lines(name, new_lines)
        return name

    def update_distance(self, station_a, station_b, distance):
        """Update the distance of the connection(s) between two adjacent stations.

        Both directions are updated where they exist.

        Returns:
            int: Number of edges updated.
        """
        if distance <= 0:
            raise DataUpdateError("distance must be positive")
        na = self.number_of(station_a)
        nb = self.number_of(station_b)
        updated = 0
        for source, dest in ((na, nb), (nb, na)):
            for edge in self.graph.adj(source):
                if edge.dest == dest:
                    edge.distance = float(distance)
                    updated += 1
        if updated == 0:
            raise DataUpdateError(f"No connection between '{station_a}' and '{station_b}'")
        return updated

    # -- integrity checks -------------------------------------------------------

    def check_integrity(self):
        """Run data coverage, connection, and distance checks.

        Returns:
            IntegrityReport: Errors and warnings found in the network.
        """
        report = IntegrityReport()

        # Coverage of main lines.
        for line in MAIN_LINES:
            if not self.stations_on_line(line):
                report.warnings.append(f"Main line '{line}' has no stations in the network")

        # Every station must belong to at least one line.
        for name in self.station_names():
            if not self.lines_of(name):
                report.errors.append(f"Station '{name}' has no line assignment")

        # Connection and distance checks.
        has_incoming = set()
        has_outgoing = set()
        for edge in self.graph.edges():
            src = self.name_of(edge.source)
            dst = self.name_of(edge.dest)
            has_outgoing.add(edge.source)
            has_incoming.add(edge.dest)
            if edge.distance <= 0:
                report.errors.append(f"Connection {src} -> {dst} has non-positive distance {edge.distance}")
            elif edge.distance > MAX_REASONABLE_DISTANCE_METERS:
                report.warnings.append(
                    f"Connection {src} -> {dst} distance {edge.distance:.0f} m is unusually long"
                )
            if edge.line not in self.lines_of(src) or edge.line not in self.lines_of(dst):
                report.errors.append(
                    f"Connection {src} -> {dst} on '{edge.line}' does not match station line data"
                )
            if not any(back.dest == edge.source for back in self.graph.adj(edge.dest)):
                report.errors.append(f"Connection {src} -> {dst} has no reverse direction")

        for number in self.graph.nodes():
            if number not in has_incoming and number not in has_outgoing:
                report.warnings.append(f"Station '{self.name_of(number)}' is isolated (no connections)")
        return report
