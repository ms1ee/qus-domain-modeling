"""Subway network management: station registry, lines, route queries,
data integrity checks and data update operations.
"""
import difflib
import unicodedata
from collections import deque
from dataclasses import dataclass, field

from errors import DataLoadError, InvalidQueryError, PathNotFoundError, StationNotFoundError
from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath

# Main lines that must be present in the dataset for the coverage check.
REPRESENTATIVE_LINES = (
    "Line 1",
    "Line 2",
    "Line 4",
    "Line 5",
    "Line 6",
    "Line 8",
    "Line 10",
    "Line 13",
    "Line 14",
    "Line 15",
    "Changping Line",
    "Yizhuang Line",
    "Fangshan Line",
    "Airport Line",
)

# Distances above this threshold between two adjacent stations are suspicious.
MAX_REASONABLE_DISTANCE_M = 10000.0

_IGNORED_CHARACTERS = frozenset("-_·•'’.")


def normalize_station_name(name):
    """Return a canonical comparison key for a station or line name.

    The key ignores case, whitespace, Unicode compatibility differences and a
    few punctuation characters, so user input such as 'xi zhi men' matches
    the official name.
    """
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    return "".join(ch for ch in text if not ch.isspace() and ch not in _IGNORED_CHARACTERS)


@dataclass
class RouteSegment:
    """A contiguous ride on one line.

    Attributes:
        line: line name.
        stations: station names ridden on this line, in order.
    """

    line: str
    stations: list


@dataclass
class TransferInfo:
    """A transfer event at a station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class RouteResult:
    """Complete answer to a path query."""

    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    station_names: list
    edge_lines: list
    segments: list = field(default_factory=list)
    transfers: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    distance_m: float = 0.0
    transfer_count: int = 0
    fare: int = 0
    estimated_time_min: float = 0.0

    @property
    def distance_km(self):
        """Total distance in kilometers."""
        return self.distance_m / 1000.0


class SubwayNetwork:
    """The Beijing Subway network model.

    Stations are assigned numeric identifiers in the order they appear in the
    dataset. Internally, per-station information is keyed by these numbers so
    that renaming a station does not invalidate references.
    """

    def __init__(self, data, name="Beijing Subway", data_source="subway_data.json"):
        self.name = name
        self.data_source = data_source
        self.version = str(data.get("version", "1.0"))
        self.graph = Graph()
        self.station_to_number = {}       # station name -> number
        self.lines = {}                   # line name -> ordered list of station names
        self._number_to_name = {}         # number -> station name
        self._normalized_index = {}       # normalized name -> canonical name
        self._declared_lines = {}         # number -> lines declared in station data
        self._connection_lines = {}       # number -> lines seen in connections
        self._line_edges = {}             # line -> list of (number, number)
        self._next_number = 0
        self._build(data)

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    def _build(self, data):
        """Populate the graph and lookup tables from the raw dataset."""
        for entry in data.get("stations", []):
            name = entry["name"].strip()
            if name in self.station_to_number:
                raise DataLoadError("Duplicate station name in data: '{}'".format(name))
            number = self._register_station(name)
            declared = []
            for line in entry.get("lines", []):
                line = line.strip()
                if line and line not in declared:
                    declared.append(line)
            self._declared_lines[number] = declared

        for conn in data.get("connections", []):
            source = conn["source"].strip()
            dest = conn["dest"].strip()
            line = conn["line"].strip()
            distance = conn["distance"]
            if self.resolve_station(source) is not None and self.resolve_station(source) == self.resolve_station(dest):
                raise DataLoadError("Connection from a station to itself: '{}'".format(source))
            if distance <= 0:
                raise DataLoadError(
                    "Connection '{}' - '{}' has non-positive distance".format(source, dest)
                )
            a_number = self._ensure_station(source)
            b_number = self._ensure_station(dest)
            if a_number == b_number:
                raise DataLoadError("Connection from a station to itself: '{}'".format(source))
            self._link(a_number, b_number, distance, line)

        for line, pairs in self._line_edges.items():
            self.lines[line] = self._order_line(pairs)

        # Make line membership lists complete (declared-only stations are appended).
        for number, name in self._number_to_name.items():
            for line in self._all_lines_of(number):
                members = self.lines.setdefault(line, [])
                if name not in members:
                    members.append(name)
            self._refresh_station_lines(number)

    def _register_station(self, name):
        """Create a new station with the next free number and return it."""
        number = self._next_number
        self._next_number += 1
        self.station_to_number[name] = number
        self._number_to_name[number] = name
        self._normalized_index.setdefault(normalize_station_name(name), name)
        self._declared_lines.setdefault(number, [])
        self._connection_lines.setdefault(number, [])
        self.graph.add_node(number)
        return number

    def _ensure_station(self, name):
        """Return the number of a station, registering it if unknown."""
        canonical = self.resolve_station(name)
        if canonical is not None:
            return self.station_to_number[canonical]
        return self._register_station(name.strip())

    def _link(self, a_number, b_number, distance, line):
        """Create an undirected edge and record line membership."""
        edge = Edge(a_number, b_number, distance, line)
        self.graph.add_edge(edge)
        self._line_edges.setdefault(line, []).append((a_number, b_number))
        for number in (a_number, b_number):
            conn = self._connection_lines.setdefault(number, [])
            if line not in conn:
                conn.append(line)
        return edge

    def _order_line(self, pairs):
        """Return station names of a line in travel order (walk from an end)."""
        adjacency = {}
        for a_number, b_number in pairs:
            adjacency.setdefault(a_number, []).append(b_number)
            adjacency.setdefault(b_number, []).append(a_number)
        if not adjacency:
            return []
        start = next(
            (node for node, nbrs in adjacency.items() if len(set(nbrs)) == 1),
            next(iter(adjacency)),
        )
        visited = {start}
        order = [start]
        current = start
        while True:
            nxt = next((n for n in adjacency[current] if n not in visited), None)
            if nxt is None:
                break
            visited.add(nxt)
            order.append(nxt)
            current = nxt
        # Append any station not reached by the walk (branching data).
        for node in adjacency:
            if node not in visited:
                visited.add(node)
                order.append(node)
        return [self._number_to_name[n] for n in order]

    def _all_lines_of(self, number):
        """Return all lines (declared or connected) of a station number."""
        lines = list(self._declared_lines.get(number, []))
        for line in self._connection_lines.get(number, []):
            if line not in lines:
                lines.append(line)
        return lines

    def _refresh_station_lines(self, number):
        """Synchronise the graph's station_lines mapping for one station."""
        name = self._number_to_name[number]
        self.graph.set_station_lines(name, self._all_lines_of(number))

    # ------------------------------------------------------------------ #
    # Lookup API
    # ------------------------------------------------------------------ #
    def resolve_station(self, name):
        """Return the official station name matching user input, or None."""
        if not isinstance(name, str):
            return None
        return self._normalized_index.get(normalize_station_name(name))

    def station_exists(self, name):
        """Return True if the name matches a station in the network."""
        return self.resolve_station(name) is not None

    def suggest_stations(self, name, limit=3):
        """Return up to ``limit`` official station names similar to ``name``."""
        key = normalize_station_name(name)
        if not key:
            return []
        matches = difflib.get_close_matches(key, list(self._normalized_index), n=limit, cutoff=0.6)
        return [self._normalized_index[m] for m in matches]

    def station_number(self, name):
        """Return the number of an official station name."""
        canonical = self.resolve_station(name)
        if canonical is None:
            raise StationNotFoundError("station '{}' does not exist".format(name))
        return self.station_to_number[canonical]

    def station_name(self, number):
        """Return the official name of a station number."""
        return self._number_to_name[number]

    def station_lines(self, name):
        """Return the lines serving an official station name."""
        canonical = self.resolve_station(name)
        if canonical is None:
            raise StationNotFoundError("station '{}' does not exist".format(name))
        return self.graph.get_station_lines(canonical)

    def is_transfer_station(self, name):
        """Return True if the station is served by more than one line."""
        return len(self.station_lines(name)) > 1

    def transfer_stations(self):
        """Return sorted names of all multi-line interchange stations."""
        return sorted(
            name for name in self.station_to_number if len(self.graph.get_station_lines(name)) > 1
        )

    def line_names(self):
        """Return sorted names of all lines in the network."""
        return sorted(self.lines)

    def stations_on_line(self, line):
        """Return the ordered station names of a line (empty if unknown)."""
        return list(self.lines.get(line, []))

    def _resolve_or_raise(self, name, role):
        """Resolve a station name or raise StationNotFoundError with hints."""
        canonical = self.resolve_station(name)
        if canonical is None:
            message = "{} station '{}' does not exist, please check the station name".format(
                role, name
            )
            hints = self.suggest_stations(name)
            if hints:
                message += " (did you mean: {}?)".format(", ".join(hints))
            raise StationNotFoundError(message)
        return canonical

    # ------------------------------------------------------------------ #
    # Route query
    # ------------------------------------------------------------------ #
    def find_route(self, start_name, end_name, config=None):
        """Compute the route, fare and summary between two stations.

        Raises:
            StationNotFoundError: if a station name is unknown.
            InvalidQueryError: if start and end are the same station.
            PathNotFoundError: if no route satisfies the constraints.
        """
        config = config if config is not None else PathfindingConfig()
        start = self._resolve_or_raise(start_name, "Starting")
        end = self._resolve_or_raise(end_name, "Ending")
        if start == end:
            raise InvalidQueryError("Starting station cannot be the same as the ending station")

        source_number = self.station_to_number[start]
        target_number = self.station_to_number[end]
        searcher = ShortestPath(self.graph, source_number, config)
        if not searcher.has_path_to(target_number):
            if config.max_transfers is not None:
                raise PathNotFoundError(
                    "No route found from '{}' to '{}' within the transfer limit of {}".format(
                        start, end, config.max_transfers
                    )
                )
            raise PathNotFoundError("No route found from '{}' to '{}'".format(start, end))

        numbers, edges = searcher.path_with_edges(target_number)
        names = [self._number_to_name[n] for n in numbers]
        transfer_count = searcher.get_transfer_count(target_number)
        segments, transfers, lines = self._summarize(names, edges)
        distance = sum(edge.distance for edge in edges)
        fare = Sum_money(distance)
        estimated = calculate_estimated_time(distance, transfer_count)

        return RouteResult(
            start=start,
            end=end,
            mode=config.mode,
            max_transfers=config.max_transfers,
            preferred_lines=list(config.preferred_lines),
            station_names=names,
            edge_lines=[edge.line for edge in edges],
            segments=segments,
            transfers=transfers,
            lines=lines,
            distance_m=distance,
            transfer_count=transfer_count,
            fare=fare,
            estimated_time_min=estimated,
        )

    @staticmethod
    def _summarize(names, edges):
        """Split a path into line segments, transfers and involved lines."""
        if not edges:
            return [], [], []
        segments = []
        transfers = []
        lines = []
        current_line = edges[0].line
        segment_stations = [names[0]]
        for index, edge in enumerate(edges):
            if edge.line not in lines:
                lines.append(edge.line)
            if edge.line != current_line:
                segments.append(RouteSegment(current_line, segment_stations))
                transfers.append(TransferInfo(names[index], current_line, edge.line))
                current_line = edge.line
                segment_stations = [names[index]]
            segment_stations.append(names[index + 1])
        segments.append(RouteSegment(current_line, segment_stations))
        return segments, transfers, lines

    # ------------------------------------------------------------------ #
    # Data update operations
    # ------------------------------------------------------------------ #
    def add_line(self, line_name, station_names, distances):
        """Add a new line from an ordered station sequence and segment distances.

        Unknown stations are created; known stations gain the new line.

        Args:
            line_name: name of the new line.
            station_names: ordered list of station names (at least two).
            distances: list of distances in meters, one per consecutive pair.

        Raises:
            InvalidQueryError: on invalid or conflicting input.
        """
        line = str(line_name).strip()
        if not line:
            raise InvalidQueryError("line name must not be empty")
        if line in self.lines:
            raise InvalidQueryError("line '{}' already exists".format(line))
        names = [str(n).strip() for n in station_names]
        if len(names) < 2:
            raise InvalidQueryError("a line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise InvalidQueryError("expected {} distances".format(len(names) - 1))
        keys = [normalize_station_name(n) for n in names]
        if len(set(keys)) != len(keys):
            raise InvalidQueryError("a line cannot contain the same station twice")
        for distance in distances:
            if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
                raise InvalidQueryError("distances must be positive numbers")

        numbers = [self._ensure_station(n) for n in names]
        for index, distance in enumerate(distances):
            self._link(numbers[index], numbers[index + 1], distance, line)
        self.lines[line] = [self._number_to_name[n] for n in numbers]
        for number in numbers:
            self._refresh_station_lines(number)

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its declared line list.

        Returns:
            The (possibly new) official name of the station.
        """
        canonical = self._resolve_or_raise(old_name, "Target")
        number = self.station_to_number[canonical]
        current = canonical

        if new_name is not None:
            new = str(new_name).strip()
            if not new:
                raise InvalidQueryError("new station name must not be empty")
            existing = self.resolve_station(new)
            if existing is not None and existing != canonical:
                raise InvalidQueryError("station '{}' already exists".format(existing))
            self._normalized_index.pop(normalize_station_name(canonical), None)
            del self.station_to_number[canonical]
            self.station_to_number[new] = number
            self._number_to_name[number] = new
            self._normalized_index[normalize_station_name(new)] = new
            self.graph.station_lines.pop(canonical, None)
            for line, members in self.lines.items():
                self.lines[line] = [new if s == canonical else s for s in members]
            current = new

        if lines is not None:
            cleaned = []
            for line in lines:
                line = str(line).strip()
                if line and line not in cleaned:
                    cleaned.append(line)
            self._declared_lines[number] = cleaned

        self._refresh_station_lines(number)
        return current

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance of the direct connection(s) between two stations.

        Returns:
            Number of edges updated.

        Raises:
            InvalidQueryError: if the distance is invalid or no connection exists.
        """
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise InvalidQueryError("distance must be a positive number of meters")
        a_name = self._resolve_or_raise(station_a, "First")
        b_name = self._resolve_or_raise(station_b, "Second")
        a_number = self.station_to_number[a_name]
        b_number = self.station_to_number[b_name]
        edges = [
            edge for edge in self.graph.edges_between(a_number, b_number)
            if line is None or edge.line == line
        ]
        if not edges:
            raise InvalidQueryError(
                "no direct connection between '{}' and '{}'".format(a_name, b_name)
            )
        for edge in edges:
            edge.distance = float(distance)
        return len(edges)

    # ------------------------------------------------------------------ #
    # Data integrity
    # ------------------------------------------------------------------ #
    def check_integrity(self):
        """Run data integrity checks.

        Returns:
            list of human-readable issue strings (empty when the data is clean).
        """
        issues = []
        if not self.station_to_number:
            return ["Coverage: no stations are loaded"]

        # Coverage of main lines.
        for line in REPRESENTATIVE_LINES:
            if line not in self.lines and not any(
                line in self._declared_lines.get(n, []) for n in self._number_to_name
            ):
                issues.append("Coverage: representative main line '{}' is missing".format(line))
            elif not self.lines.get(line):
                issues.append("Coverage: line '{}' has no stations".format(line))

        # Station-level checks: naming, connection membership and isolation.
        seen_keys = {}
        for number, name in self._number_to_name.items():
            key = normalize_station_name(name)
            if key in seen_keys:
                issues.append(
                    "Naming: stations '{}' and '{}' are ambiguous".format(seen_keys[key], name)
                )
            else:
                seen_keys[key] = name
            declared = set(self._declared_lines.get(number, []))
            connected = set(self._connection_lines.get(number, []))
            if declared - connected:
                issues.append(
                    "Connection: station '{}' lists line(s) {} without any connection".format(
                        name, sorted(declared - connected)
                    )
                )
            if connected - declared:
                issues.append(
                    "Connection: station '{}' is connected on line(s) {} but they are not in its line list".format(
                        name, sorted(connected - declared)
                    )
                )
            if not self.graph.adjacent(number):
                issues.append("Connection: station '{}' is isolated".format(name))

        # Connectivity of the whole network.
        nodes = self.graph.nodes()
        if nodes:
            reached = {nodes[0]}
            queue = deque([nodes[0]])
            while queue:
                node = queue.popleft()
                for edge in self.graph.adjacent(node):
                    nxt = edge.other(node)
                    if nxt not in reached:
                        reached.add(nxt)
                        queue.append(nxt)
            unreachable = [n for n in nodes if n not in reached]
            if unreachable:
                issues.append(
                    "Connection: {} station(s) are unreachable from '{}'".format(
                        len(unreachable), self._number_to_name[nodes[0]]
                    )
                )

        # Distance accuracy and duplicate connections.
        seen_pairs = set()
        for edge in self.graph.edges():
            a_name = self._number_to_name[edge.source]
            b_name = self._number_to_name[edge.dest]
            if edge.distance <= 0:
                issues.append(
                    "Distance: connection '{}' - '{}' ({}) has a non-positive distance".format(
                        a_name, b_name, edge.line
                    )
                )
            elif edge.distance > MAX_REASONABLE_DISTANCE_M:
                issues.append(
                    "Distance: connection '{}' - '{}' ({}) is suspiciously long: {} m".format(
                        a_name, b_name, edge.line, edge.distance
                    )
                )
            key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
            if key in seen_pairs:
                issues.append(
                    "Connection: duplicate connection '{}' - '{}' on {}".format(
                        a_name, b_name, edge.line
                    )
                )
            seen_pairs.add(key)

        # Line data completeness.
        for line, members in self.lines.items():
            if not members:
                issues.append("Line data: line '{}' has no stations".format(line))

        return issues
