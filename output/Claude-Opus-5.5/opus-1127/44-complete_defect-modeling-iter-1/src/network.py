"""
Subway network model and data management (loading, integrity checks and
data updates).
"""

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph
from pathfinding import ShortestPath, PathfindingConfig

MAIN_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
              "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
              "Fangshan Line", "Airport Line"]

LINE_ALIASES = {
    "Changping Line": ["昌平线"],
    "Yizhuang Line": ["亦庄线"],
    "Fangshan Line": ["房山线"],
    "Airport Line": ["首都机场线", "机场线", "Capital Airport Express", "Airport Express"],
}

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "Wangfujing", "Guomao"],
    "Line 2": ["Xizhimen", "Dongzhimen", "Beijing Railway Station"],
    "Line 4": ["Zhongguancun", "Xuanwumen"],
    "Line 5": ["Dongdan", "Songjiazhuang"],
    "Line 10": ["Sanyuanqiao", "Haidian Huangzhuang"],
    "Line 13": ["Xi'erqi", "Huilongguan"],
}

MIN_REASONABLE_DISTANCE = 200
MAX_REASONABLE_DISTANCE = 30000


def _norm_line(name):
    return re.sub(r"\s+", "", str(name)).lower()


def _norm_station(name):
    s = " ".join(str(name).split()).lower()
    return s


def _norm_station_loose(name):
    s = _norm_station(name).replace("’", "'")
    if s.endswith("站") and len(s) > 1:
        s = s[:-1]
    if s.endswith(" station") and len(s) > len(" station"):
        s = s[: -len(" station")]
    return s.replace(" ", "")


@dataclass
class Station:
    name: str
    number: int
    lines: list = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    name: str
    station_sequence: list = field(default_factory=list)


@dataclass
class DataIntegrityCheck:
    station_coverage_valid: bool = True
    connection_integrity_valid: bool = True
    distance_accuracy_valid: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def is_valid(self):
        return self.station_coverage_valid and self.connection_integrity_valid and self.distance_accuracy_valid

    def summary(self):
        ok = lambda b: "PASS" if b else "FAIL"
        lines = ["Data Integrity Check Report", "=" * 40]
        for k, v in self.stats.items():
            lines.append(f"{k}: {v}")
        lines.append("-" * 40)
        lines.append(f"Station coverage:      {ok(self.station_coverage_valid)}")
        lines.append(f"Connection integrity:  {ok(self.connection_integrity_valid)}")
        lines.append(f"Distance accuracy:     {ok(self.distance_accuracy_valid)}")
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        lines.append("-" * 40)
        lines.append("Overall: " + ("PASS" if self.is_valid else "FAIL"))
        return "\n".join(lines)


class SubwayNetwork:
    """The Beijing Subway network: stations, lines, connections and graph."""

    def __init__(self, data=None, data_source=DATA_FILE_PATH):
        self.data_source = data_source
        if data is None:
            data = load_subway_data(data_source)
        self.station_to_number = {}
        self.number_to_station = {}
        self.stations = {}
        self.connections = []
        self.graph = Graph()
        self.load_warnings = []
        self._exact_index = {}
        self._loose_index = {}
        self._build(data)

    # ------------------------------------------------------------- building
    def _add_station(self, name, lines=()):
        name = str(name).strip()
        if name in self.stations:
            st = self.stations[name]
            for ln in lines:
                if ln not in st.lines:
                    st.lines.append(ln)
        else:
            number = len(self.station_to_number)
            while number in self.number_to_station:
                number += 1
            st = Station(name=name, number=number, lines=list(dict.fromkeys(lines)))
            self.stations[name] = st
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
        self.graph.set_station_lines(name, st.lines)
        self._index_station(name)
        return st

    def _index_station(self, name):
        self._exact_index[_norm_station(name)] = name
        self._loose_index[_norm_station_loose(name)] = name

    def _rebuild_index(self):
        self._exact_index.clear()
        self._loose_index.clear()
        for name in self.stations:
            self._index_station(name)

    def _build(self, data):
        for s in data.get("stations", []):
            if not isinstance(s, dict) or not s.get("name"):
                self.load_warnings.append(f"Invalid station entry skipped: {s!r}")
                continue
            self._add_station(s["name"], s.get("lines", []) or [])
        for c in data.get("connections", []):
            try:
                self._add_connection(c["source"], c["dest"], c["distance"], c.get("line"))
            except (KeyError, TypeError, ValueError) as exc:
                self.load_warnings.append(f"Invalid connection skipped: {c!r} ({exc})")

    def _add_connection(self, source, dest, distance, line):
        source, dest = str(source).strip(), str(dest).strip()
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError("distance must be numeric")
        for n in (source, dest):
            if n not in self.stations:
                self.load_warnings.append(f"Station '{n}' referenced by a connection but not defined; added")
            self._add_station(n, [line] if line else [])
        self.connections.append({"source": source, "dest": dest, "distance": distance, "line": line})
        self.graph.add_edge(Edge(self.station_to_number[source], self.station_to_number[dest], distance, line))

    # --------------------------------------------------------------- lookups
    def resolve_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name is None:
            return None
        raw = str(name).strip().strip("'\"")
        if not raw:
            return None
        if raw in self.stations:
            return raw
        found = self._exact_index.get(_norm_station(raw))
        if found:
            return found
        return self._loose_index.get(_norm_station_loose(raw))

    def station_name(self, number):
        return self.number_to_station.get(number)

    @property
    def line_names(self):
        names = []
        for st in self.stations.values():
            names.extend(st.lines)
        for c in self.connections:
            if c["line"]:
                names.append(c["line"])
        return list(dict.fromkeys(names))

    def resolve_line(self, name):
        key = _norm_line(name)
        for ln in self.line_names:
            if _norm_line(ln) == key:
                return ln
        return None

    def line_sequence(self, line):
        adj = defaultdict(list)
        for c in self.connections:
            if c["line"] == line:
                adj[c["source"]].append(c["dest"])
                adj[c["dest"]].append(c["source"])
        if not adj:
            return [n for n, st in self.stations.items() if line in st.lines]
        ends = [n for n in adj if len(set(adj[n])) == 1]
        start = ends[0] if ends else next(iter(adj))
        seq, visited, stack = [], set(), [start]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            seq.append(n)
            for nb in reversed(adj[n]):
                if nb not in visited:
                    stack.append(nb)
        return seq

    @property
    def lines(self):
        return {ln: Line(ln, self.line_sequence(ln)) for ln in self.line_names}

    def transfer_stations(self):
        return [n for n, st in self.stations.items() if st.is_transfer_station]

    # ----------------------------------------------------------- pathfinding
    def find_route(self, start_name, end_name, config=None):
        """Return (ShortestPath, target number) for a query."""
        s = self.resolve_station(start_name)
        e = self.resolve_station(end_name)
        if s is None:
            raise KeyError(f"Starting station '{start_name}' does not exist")
        if e is None:
            raise KeyError(f"Ending station '{end_name}' does not exist")
        sp = ShortestPath(self.graph, self.station_to_number[s], config or PathfindingConfig())
        return sp, self.station_to_number[e]

    # ---------------------------------------------------------- data update
    def add_line(self, line_name, station_sequence, distances):
        """Add a new line given ordered station names and the distances
        (meters) between consecutive stations."""
        if len(station_sequence) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance {d!r}")
        for name in station_sequence:
            self._add_station(name, [line_name])
        for a, b, d in zip(station_sequence, station_sequence[1:], distances):
            self._add_connection(a, b, d, line_name)

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        official = self.resolve_station(name)
        if official is None:
            raise KeyError(f"Station '{name}' does not exist")
        st = self.stations[official]
        if lines is not None:
            st.lines = list(dict.fromkeys(lines))
        if new_name and new_name != official:
            if new_name in self.stations:
                raise ValueError(f"Station '{new_name}' already exists")
            number = st.number
            del self.stations[official]
            del self.station_to_number[official]
            self.graph.station_lines.pop(official, None)
            st.name = new_name
            self.stations[new_name] = st
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            for c in self.connections:
                if c["source"] == official:
                    c["source"] = new_name
                if c["dest"] == official:
                    c["dest"] = new_name
            self._rebuild_index()
        self.graph.set_station_lines(st.name, st.lines)
        return st

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance between two adjacent stations."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        a, b = self.resolve_station(station_a), self.resolve_station(station_b)
        if a is None or b is None:
            raise KeyError("Station does not exist")
        updated = 0
        for c in self.connections:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        self.graph.update_edge_weight(self.station_to_number[a], self.station_to_number[b], distance, line)
        return updated

    def to_dict(self):
        return {
            "stations": [{"name": st.name, "lines": list(st.lines)} for st in self.stations.values()],
            "connections": [dict(c) for c in self.connections],
        }

    def save(self, path=None):
        save_subway_data(self.to_dict(), path or self.data_source)

    # ------------------------------------------------------ integrity check
    def check_integrity(self):
        result = DataIntegrityCheck()
        result.stats = {
            "Stations": len(self.stations),
            "Connections": len(self.connections),
            "Lines": len(self.line_names),
            "Transfer stations": len(self.transfer_stations()),
        }
        for w in self.load_warnings:
            result.warnings.append(w)

        # --- station coverage
        line_keys = {_norm_line(ln): ln for ln in self.line_names}
        for main in MAIN_LINES:
            candidates = [_norm_line(main)] + [_norm_line(a) for a in LINE_ALIASES.get(main, [])]
            m = re.match(r"line(\d+)$", _norm_line(main))
            if m:
                candidates.append(f"{m.group(1)}号线")
            matched = None
            for key, ln in line_keys.items():
                for cand in candidates:
                    if key == cand or (key.startswith(cand) and not key[len(cand):len(cand) + 1].isdigit()):
                        matched = ln
                        break
                if matched:
                    break
            if matched is None:
                result.station_coverage_valid = False
                result.errors.append(f"Main line '{main}' is missing from the data")
            elif len(self.line_sequence(matched)) < 2:
                result.station_coverage_valid = False
                result.errors.append(f"Main line '{main}' has fewer than two stations")
        for main, names in REPRESENTATIVE_STATIONS.items():
            for n in names:
                if self.resolve_station(n) is None:
                    result.warnings.append(f"Representative station '{n}' of {main} not found")

        # --- connection integrity
        connected_stations = set()
        for c in self.connections:
            connected_stations.update((c["source"], c["dest"]))
            if c["source"] == c["dest"]:
                result.connection_integrity_valid = False
                result.errors.append(f"Self-loop connection at '{c['source']}'")
            if not c["line"]:
                result.warnings.append(f"Connection {c['source']} - {c['dest']} has no line")
            else:
                for n in (c["source"], c["dest"]):
                    if c["line"] not in self.stations[n].lines:
                        result.warnings.append(f"Station '{n}' is not declared on line '{c['line']}'")
        for n in self.stations:
            if n not in connected_stations:
                result.connection_integrity_valid = False
                result.errors.append(f"Station '{n}' has no connections")
        if self.stations:
            start = next(iter(self.station_to_number.values()))
            seen = {start}
            dq = deque([start])
            while dq:
                v = dq.popleft()
                for e in self.graph.adjacent(v):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        dq.append(e.dest)
            if len(seen) != len(self.stations):
                result.connection_integrity_valid = False
                result.errors.append(
                    f"Network is not connected: {len(self.stations) - len(seen)} station(s) unreachable")

        # --- distance accuracy
        pair_distances = {}
        for c in self.connections:
            d = c["distance"]
            label = f"{c['source']} - {c['dest']} ({c['line']})"
            if d <= 0:
                result.distance_accuracy_valid = False
                result.errors.append(f"Non-positive distance {d} for {label}")
                continue
            if d < MIN_REASONABLE_DISTANCE or d > MAX_REASONABLE_DISTANCE:
                result.warnings.append(f"Unusual distance {d} m for {label}")
            key = (frozenset((c["source"], c["dest"])), c["line"])
            if key in pair_distances and pair_distances[key] != d:
                result.distance_accuracy_valid = False
                result.errors.append(
                    f"Conflicting distances for {label}: {pair_distances[key]} vs {d}")
            pair_distances.setdefault(key, d)
        return result
