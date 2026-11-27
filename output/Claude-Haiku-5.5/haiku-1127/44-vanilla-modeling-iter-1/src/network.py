"""Subway network: station registry, graph construction, queries and updates."""

import re
from collections import deque

from src.fare_calculator import Sum_money, calculate_estimated_time
from src.models import Edge, FareResult, Graph, PathSegment, Route, Transfer
from src.pathfinding import PathfindingConfig, ShortestPath


class QueryError(Exception):
    """Raised when a query or update on the network cannot be completed."""


def _normalize(text: str) -> str:
    """Key used for case-insensitive, whitespace-insensitive name matching."""
    return re.sub(r"\s+", "", str(text)).casefold()


def _as_int_if_whole(value):
    """Return int for whole-number floats (keeps JSON output clean)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


class SubwayNetwork:
    """Weighted undirected model of the Beijing Subway network.

    Station numbers (0..N-1) are assigned here in order of first appearance.

    Attributes:
        station_to_number: station name -> station number.
        number_to_station: station number -> station name.
        lines: line name -> list of station names on that line.
        graph: the underlying ``Graph``.
    """

    def __init__(self, data: dict = None):
        self.station_to_number: dict[str, int] = {}
        self.number_to_station: list[str] = []
        self.lines: dict[str, list[str]] = {}
        self.graph = Graph()
        self._index: dict[str, str] = {}  # normalized name -> official name
        self._build(data or {})

    # ----- construction -----------------------------------------------------
    def _build(self, data: dict) -> None:
        for item in data.get("stations", []):
            name = str(item["name"]).strip()
            lines = [str(line) for line in item.get("lines", [])]
            self._add_station(name)
            self.graph.set_station_lines(name, lines)
            for line in lines:
                self._register_line_station(line, name)

        for conn in data.get("connections", []):
            src = str(conn["source"]).strip()
            dst = str(conn["dest"]).strip()
            line = str(conn["line"])
            distance = conn["distance"]
            self._add_station(src)
            self._add_station(dst)
            self._register_line_station(line, src)
            self._register_line_station(line, dst)
            self.graph.add_edge(
                Edge(self.station_to_number[src], self.station_to_number[dst], distance, line)
            )

    def _add_station(self, name: str) -> int:
        """Register a station (if new) and return its number."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.number_to_station)
        self.station_to_number[name] = number
        self.number_to_station.append(name)
        self._index[_normalize(name)] = name
        self.graph.add_node(number)
        self.graph.station_lines.setdefault(name, [])
        return number

    def _register_line_station(self, line: str, name: str) -> None:
        members = self.lines.setdefault(line, [])
        if name not in members:
            members.append(name)

    def _attach_line_to_station(self, name: str, line: str) -> None:
        lines = self.graph.station_lines.setdefault(name, [])
        if line not in lines:
            lines.append(line)
        self._register_line_station(line, name)

    def _reindex(self) -> None:
        self._index = {_normalize(name): name for name in self.station_to_number}

    # ----- lookups ----------------------------------------------------------
    def station_exists(self, name: str) -> bool:
        return name in self.station_to_number

    def station_names(self) -> list[str]:
        return sorted(self.station_to_number)

    def line_names(self) -> list[str]:
        return sorted(self.lines)

    def stations_on_line(self, line: str) -> list[str]:
        return list(self.lines.get(line, []))

    def resolve_line(self, text: str):
        """Return the official line name matching ``text`` (or None)."""
        key = _normalize(text)
        for line in self.lines:
            if _normalize(line) == key:
                return line
        return None

    def standardize_station_name(self, raw: str):
        """Map a user-entered station name to its official name (or None).

        Matching ignores case, whitespace and a trailing "站" / "Station".
        """
        text = " ".join(str(raw).split())
        if not text:
            return None
        if text in self.station_to_number:
            return text
        key = _normalize(text)
        if key in self._index:
            return self._index[key]
        for suffix in ("站", "station"):
            if key.endswith(suffix) and key[: -len(suffix)] in self._index:
                return self._index[key[: -len(suffix)]]
        return None

    # ----- queries ----------------------------------------------------------
    def query(self, start: str, end: str, config: PathfindingConfig = None) -> Route:
        """Compute the route, transfers, fare and estimated time between two stations.

        Raises:
            QueryError: on unknown stations, identical endpoints, unreachable
                targets, or path/fare calculation failures.
        """
        config = config or PathfindingConfig()
        if not self.station_exists(start):
            raise QueryError(f"Starting station '{start}' does not exist, please check the station name")
        if not self.station_exists(end):
            raise QueryError(f"Ending station '{end}' does not exist, please check the station name")
        if start == end:
            raise QueryError("Starting station cannot be the same as the ending station")

        try:
            search = ShortestPath(self.graph, self.station_to_number[start], config)
            target = self.station_to_number[end]
            if not search.has_path(target):
                raise QueryError(
                    f"No route found between '{start}' and '{end}' under the given constraints"
                )
            numbers, edges = search.path_with_edges(target)
        except QueryError:
            raise
        except Exception as exc:  # defensive: surface unexpected algorithm failures
            raise QueryError(f"Path calculation failed: {exc}") from exc

        if not edges:
            raise QueryError(f"No route found between '{start}' and '{end}'")

        stations = [self.number_to_station[n] for n in numbers]
        total_distance = float(sum(e.distance for e in edges))
        segments, transfers, lines = self._summarize_path(stations, edges)
        transfer_count = len(transfers)

        try:
            fare_amount = Sum_money(total_distance)
        except (TypeError, ValueError) as exc:
            raise QueryError(f"Fare calculation failed: {exc}") from exc

        estimated = calculate_estimated_time(total_distance, transfer_count)
        return Route(
            start=start,
            end=end,
            mode=config.mode,
            stations=stations,
            edges=edges,
            total_distance=total_distance,
            transfer_count=transfer_count,
            estimated_time=estimated,
            fare=FareResult(amount=fare_amount, currency="yuan"),
            segments=segments,
            transfers=transfers,
            lines=lines,
        )

    @staticmethod
    def _summarize_path(stations, edges):
        """Build line segments, transfer list and involved-line list for a path."""
        segments: list[PathSegment] = []
        transfers: list[Transfer] = []
        lines: list[str] = []
        for i, edge in enumerate(edges):
            if edge.line not in lines:
                lines.append(edge.line)
            if i == 0 or edges[i - 1].line != edge.line:
                if i > 0:
                    transfers.append(Transfer(stations[i], edges[i - 1].line, edge.line))
                segments.append(
                    PathSegment(
                        line_name=edge.line,
                        start_station=stations[i],
                        end_station=stations[i + 1],
                        distance=edge.distance,
                        station_count=2,
                    )
                )
            else:
                seg = segments[-1]
                seg.end_station = stations[i + 1]
                seg.distance += edge.distance
                seg.station_count += 1
        return segments, transfers, lines

    # ----- data updates -----------------------------------------------------
    def add_line(self, line_name: str, station_names: list[str], distances: list) -> None:
        """Add a new line through an ordered list of stations.

        Args:
            line_name: name of the new line (must not exist yet).
            station_names: ordered station names; unknown names create new stations.
            distances: distance in meters between consecutive stations
                (len = len(station_names) - 1).
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise QueryError("Line name cannot be empty")
        if self.resolve_line(line_name) is not None:
            raise QueryError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise QueryError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise QueryError("Number of distances must equal number of stations minus one")
        if len(set(station_names)) != len(station_names):
            raise QueryError("Station names on a line must be unique")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise QueryError(f"Invalid distance {d!r}: must be a positive number of meters")

        numbers = [self._add_station(name) for name in station_names]
        for name in station_names:
            self._attach_line_to_station(name, line_name)
        for i, distance in enumerate(distances):
            self.graph.add_edge(Edge(numbers[i], numbers[i + 1], distance, line_name))

    def modify_station(self, name: str, new_name: str = None, lines: list[str] = None) -> None:
        """Rename a station and/or replace its line affiliations."""
        if not self.station_exists(name):
            raise QueryError(f"Station '{name}' does not exist")
        current = name

        if new_name is not None and new_name.strip() and new_name.strip() != name:
            new_name = " ".join(new_name.split())
            if self.station_exists(new_name):
                raise QueryError(f"Station '{new_name}' already exists")
            number = self.station_to_number.pop(name)
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            self.graph.station_lines[new_name] = self.graph.station_lines.pop(name, [])
            for members in self.lines.values():
                for idx, member in enumerate(members):
                    if member == name:
                        members[idx] = new_name
            self._reindex()
            current = new_name

        if lines is not None:
            new_lines = [str(x) for x in lines]
            old_lines = list(self.graph.station_lines.get(current, []))
            for line in old_lines:
                if line not in new_lines and current in self.lines.get(line, []):
                    self.lines[line].remove(current)
            self.graph.set_station_lines(current, new_lines)
            for line in new_lines:
                self._register_line_station(line, current)

    def update_distance(self, a: str, b: str, distance, line: str = None) -> int:
        """Update the distance between two adjacent stations.

        Returns the number of connections updated.
        """
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise QueryError("Distance must be a positive number of meters")
        if not self.station_exists(a) or not self.station_exists(b):
            raise QueryError("Both stations must exist to update their distance")
        ua, ub = self.station_to_number[a], self.station_to_number[b]
        matches = [
            e for e in self.graph.find_edges(ua, ub)
            if line is None or e.line == line
        ]
        if not matches:
            raise QueryError(f"No connection between '{a}' and '{b}'")
        for edge in matches:
            edge.distance = distance
        return len(matches)

    # ----- export -----------------------------------------------------------
    def to_data(self) -> dict:
        """Export the network in the subway_data.json structure."""
        stations = [
            {"name": name, "lines": list(self.graph.station_lines.get(name, []))}
            for name in self.number_to_station
        ]
        connections = [
            {
                "source": self.number_to_station[e.source],
                "dest": self.number_to_station[e.dest],
                "distance": _as_int_if_whole(e.distance),
                "line": e.line,
            }
            for e in self.graph.edges()
        ]
        return {"stations": stations, "connections": connections}

    # ----- analysis helpers -------------------------------------------------
    def connected_component_size(self, start_number: int = 0) -> int:
        """Number of stations reachable from ``start_number`` (BFS)."""
        if not self.graph.has_node(start_number):
            return 0
        seen = {start_number}
        queue = deque([start_number])
        while queue:
            v = queue.popleft()
            for edge in self.graph.adjacent(v):
                w = edge.other(v)
                if w not in seen:
                    seen.add(w)
                    queue.append(w)
        return len(seen)
