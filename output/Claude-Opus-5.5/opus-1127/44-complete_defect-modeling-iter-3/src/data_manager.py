"""Subway network data management and integrity checking."""

import difflib
import json
import re
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Connection, Edge, Graph, Line, Station

# Main lines required by the PRD with known aliases (English and Chinese).
MAIN_LINES = {
    "Line 1": ["Line 1", "1号线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线", "Line 4 Daxing", "4号线大兴线"],
    "Line 5": ["Line 5", "5号线"],
    "Line 6": ["Line 6", "6号线"],
    "Line 8": ["Line 8", "8号线"],
    "Line 10": ["Line 10", "10号线"],
    "Line 13": ["Line 13", "13号线"],
    "Line 14": ["Line 14", "14号线"],
    "Line 15": ["Line 15", "15号线"],
    "Changping Line": ["Changping Line", "昌平线"],
    "Yizhuang Line": ["Yizhuang Line", "亦庄线"],
    "Fangshan Line": ["Fangshan Line", "房山线"],
    "Airport Line": ["Airport Line", "Airport Express", "Capital Airport Express", "首都机场线", "机场线"],
}

# Representative stations of main lines (any alias counts).
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Tian'anmen East", "Tiananmen East", "天安门东"],
    "Line 2": ["Xizhimen", "西直门"],
    "Line 4": ["Beijing South Railway Station", "Beijing South Station", "Beijingnanzhan", "北京南站"],
    "Line 5": ["Dongdan", "东单"],
    "Line 6": ["Chaoyangmen", "朝阳门"],
    "Line 10": ["Guomao", "国贸"],
    "Line 13": ["Xierqi", "西二旗"],
    "Line 14": ["Wangjing", "望京"],
    "Airport Line": ["Sanyuanqiao", "三元桥"],
}

MIN_VALID_DISTANCE = 1          # meters (strictly positive)
MAX_VALID_DISTANCE = 30000      # meters
SUSPICIOUS_SHORT_DISTANCE = 300
SUSPICIOUS_LONG_DISTANCE = 20000


class DataError(Exception):
    """Raised for invalid network data or invalid update operations."""


def normalize_station_key(name):
    """Normalized key for tolerant station name comparison."""
    return re.sub(r"[\s'’`\-_.]", "", str(name)).lower()


def normalize_line_key(name):
    """Normalized key for tolerant line name comparison ('Line 1' == '1号线')."""
    key = re.sub(r"[\s_\-]", "", str(name)).lower()
    for token in ("subway", "地铁", "号线", "line", "线"):
        key = key.replace(token, "")
    if key.isdigit():
        key = str(int(key))
    return key


class SubwayNetwork:
    """In-memory model of the Beijing Subway network."""

    def __init__(self, data=None, data_source=None):
        self.data_source = data_source or DATA_FILE_PATH
        if data is None:
            data = load_subway_data(self.data_source)
        if not isinstance(data, dict):
            raise DataError("Network data must be a dictionary")
        self.stations = {}            # name -> Station
        self.station_to_number = {}   # name -> number
        self.number_to_station = {}   # number -> name
        self.connections = []         # list[Connection]
        self.graph = Graph()
        self._next_number = 0
        self._load(data)
        self.rebuild_graph()

    # ----------------------------------------------------------- loading
    def _register_station(self, name, lines=None):
        name = str(name).strip()
        if not name:
            raise DataError("Station name cannot be empty")
        if name in self.stations:
            station = self.stations[name]
            for line in lines or []:
                if line not in station.lines:
                    station.lines.append(line)
            return station
        number = self._next_number
        self._next_number += 1
        station = Station(name=name, number=number, lines=list(lines or []))
        self.stations[name] = station
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        return station

    def _load(self, data):
        for item in data.get("stations", []):
            if not isinstance(item, dict) or "name" not in item:
                raise DataError(f"Invalid station entry: {item!r}")
            self._register_station(item["name"], item.get("lines", []))
        for item in data.get("connections", []):
            try:
                src = str(item["source"]).strip()
                dst = str(item["dest"]).strip()
                dist = item["distance"]
            except (KeyError, TypeError) as exc:
                raise DataError(f"Invalid connection entry: {item!r}") from exc
            line = item.get("line", "") or ""
            for name in (src, dst):
                if name not in self.stations:
                    self._register_station(name, [line] if line else [])
            self.connections.append(Connection(src, dst, dist, line))

    def rebuild_graph(self):
        """(Re)build the weighted graph from stations and connections."""
        graph = Graph()
        for name, station in self.stations.items():
            graph.add_vertex(station.number)
            graph.set_station_lines(name, station.lines)
        for conn in self.connections:
            if conn.source not in self.station_to_number or conn.dest not in self.station_to_number:
                continue
            if not isinstance(conn.distance, (int, float)) or conn.distance < 0:
                continue
            graph.add_edge(Edge(self.station_to_number[conn.source],
                                self.station_to_number[conn.dest], conn.distance, conn.line))
        self.graph = graph
        return graph

    # ----------------------------------------------------------- queries
    def adjacency_dict(self):
        """Weighted undirected graph as ``{station: [(neighbour, distance, line)]}``."""
        result = {name: [] for name in self.stations}
        for v, edges in self.graph.adj.items():
            name = self.number_to_station[v]
            result[name] = [(self.number_to_station[e.dest], e.weight, e.line) for e in edges]
        return result

    def get_station_number(self, name):
        return self.station_to_number.get(name)

    def get_station_name(self, number):
        return self.number_to_station.get(number)

    def is_transfer_station(self, name):
        station = self.stations.get(name)
        if station is None:
            return False
        lines = set(station.lines)
        lines.update(c.line for c in self.connections if name in (c.source, c.dest) and c.line)
        return len(lines) > 1

    def resolve_station_name(self, raw):
        """Return the official station name matching ``raw`` or None."""
        if raw is None:
            return None
        cleaned = re.sub(r"\s+", " ", str(raw)).strip()
        if cleaned in self.stations:
            return cleaned
        key = normalize_station_key(cleaned)
        if not key:
            return None
        for name in self.stations:
            if normalize_station_key(name) == key:
                return name
        return None

    def suggest_stations(self, raw, n=3):
        return difflib.get_close_matches(str(raw).strip(), list(self.stations), n=n, cutoff=0.6)

    def all_line_names(self):
        names = set()
        for station in self.stations.values():
            names.update(l for l in station.lines if l)
        names.update(c.line for c in self.connections if c.line)
        return sorted(names)

    def resolve_line_names(self, raw):
        """Return the data line names matching the user supplied ``raw`` name."""
        if raw is None:
            return []
        raw = str(raw).strip()
        lines = self.all_line_names()
        if raw in lines:
            return [raw]
        lowered = [l for l in lines if l.lower() == raw.lower()]
        if lowered:
            return lowered
        key = normalize_line_key(raw)
        return [l for l in lines if normalize_line_key(l) == key]

    def _derive_line_sequence(self, line):
        adj = defaultdict(list)
        order = []
        for conn in self.connections:
            if conn.line != line:
                continue
            for a, b in ((conn.source, conn.dest), (conn.dest, conn.source)):
                if b not in adj[a]:
                    adj[a].append(b)
            for s in (conn.source, conn.dest):
                if s not in order:
                    order.append(s)
        if not adj:
            return [n for n, s in self.stations.items() if line in s.lines]
        ends = [s for s in order if len(adj[s]) == 1]
        sequence, visited = [], set()
        for start in ends + order:
            if start in visited:
                continue
            stack = [start]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                sequence.append(node)
                for nxt in reversed(adj[node]):
                    if nxt not in visited:
                        stack.append(nxt)
        return sequence

    @property
    def lines(self):
        """Dictionary ``line name -> Line`` (station sequence and transfers)."""
        result = {}
        for line in self.all_line_names():
            seq = self._derive_line_sequence(line)
            transfers = [s for s in seq if self.is_transfer_station(s)]
            result[line] = Line(name=line, station_sequence=seq, transfer_stations=transfers)
        return result

    # ----------------------------------------------------------- updates
    def add_station(self, name, lines=None):
        station = self._register_station(name, lines)
        self.rebuild_graph()
        return station

    def add_connection(self, source, dest, distance, line):
        if source == dest:
            raise DataError("A connection must link two different stations")
        if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance <= 0:
            raise DataError("Distance must be a positive number of meters")
        self._register_station(source, [line] if line else [])
        self._register_station(dest, [line] if line else [])
        self.connections.append(Connection(source, dest, distance, line))
        self.rebuild_graph()

    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if not line_name:
            raise DataError("Line name cannot be empty")
        if len(station_names) < 2:
            raise DataError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise DataError("Number of distances must equal number of stations minus one")
        for d in distances:
            if not isinstance(d, (int, float)) or isinstance(d, bool) or d <= 0:
                raise DataError("Distances must be positive numbers of meters")
        for name in station_names:
            self._register_station(name, [line_name])
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.connections.append(Connection(a, b, d, line_name))
        self.rebuild_graph()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        if name not in self.stations:
            raise DataError(f"Station '{name}' does not exist")
        station = self.stations[name]
        if new_name is not None and new_name != name:
            new_name = new_name.strip()
            if not new_name:
                raise DataError("New station name cannot be empty")
            if new_name in self.stations:
                raise DataError(f"Station '{new_name}' already exists")
            del self.stations[name]
            del self.station_to_number[name]
            station.name = new_name
            self.stations[new_name] = station
            self.station_to_number[new_name] = station.number
            self.number_to_station[station.number] = new_name
            for conn in self.connections:
                if conn.source == name:
                    conn.source = new_name
                if conn.dest == name:
                    conn.dest = new_name
        if lines is not None:
            station.lines = list(lines)
        self.rebuild_graph()
        return station

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two stations."""
        if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance <= 0:
            raise DataError("Distance must be a positive number of meters")
        updated = 0
        for conn in self.connections:
            if {conn.source, conn.dest} == {source, dest} and (line is None or conn.line == line):
                conn.distance = distance
                updated += 1
        if not updated:
            raise DataError(f"No connection between '{source}' and '{dest}'")
        self.rebuild_graph()
        return updated

    def to_dict(self):
        return {
            "stations": [{"name": s.name, "lines": list(s.lines)}
                         for s in sorted(self.stations.values(), key=lambda s: s.number)],
            "connections": [{"source": c.source, "dest": c.dest, "distance": c.distance, "line": c.line}
                            for c in self.connections],
        }

    def save(self, path=None):
        with open(path or self.data_source, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)


class DataIntegrityChecker:
    """Checks coverage, connection integrity and distance accuracy."""

    def __init__(self, network):
        self.network = network
        self.coverage_valid = None
        self.connection_valid = None
        self.distance_valid = None
        self.errors = []
        self.warnings = []
        self.info = []

    def check_coverage(self):
        net = self.network
        lines = net.all_line_names()
        line_keys = {normalize_line_key(l): l for l in lines}
        line_stations = net.lines
        ok = True
        for main, aliases in MAIN_LINES.items():
            found = next((line_keys[normalize_line_key(a)] for a in aliases
                          if normalize_line_key(a) in line_keys), None)
            if found is None:
                ok = False
                self.errors.append(f"Main line missing: {main}")
            else:
                count = len(line_stations[found].station_sequence)
                if count < 2:
                    ok = False
                    self.errors.append(f"Line '{found}' has fewer than 2 stations")
                else:
                    self.info.append(f"Line '{found}': {count} stations")
        station_keys = {normalize_station_key(s) for s in net.stations}
        for line, aliases in REPRESENTATIVE_STATIONS.items():
            if not any(normalize_station_key(a) in station_keys for a in aliases):
                ok = False
                self.errors.append(f"Representative station of {line} missing: {aliases[0]}")
        self.coverage_valid = ok
        return ok

    def check_connections(self):
        net = self.network
        ok = True
        seen = {}
        connected = set()
        for conn in net.connections:
            if conn.source not in net.stations or conn.dest not in net.stations:
                ok = False
                self.errors.append(f"Connection references unknown station: {conn.source} - {conn.dest}")
                continue
            if conn.source == conn.dest:
                ok = False
                self.errors.append(f"Self-loop connection at station '{conn.source}'")
                continue
            if not conn.line:
                self.warnings.append(f"Connection {conn.source} - {conn.dest} has no line")
            else:
                for s in (conn.source, conn.dest):
                    if net.stations[s].lines and conn.line not in net.stations[s].lines:
                        self.warnings.append(f"Station '{s}' is not listed on line '{conn.line}'")
            key = (frozenset((conn.source, conn.dest)), conn.line)
            if key in seen:
                self.warnings.append(f"Duplicate connection {conn.source} - {conn.dest} ({conn.line})")
            seen[key] = conn
            connected.update((conn.source, conn.dest))
        for name in net.stations:
            if name not in connected:
                self.warnings.append(f"Station '{name}' has no connections")
        # Connectivity of the whole network
        vertices = net.graph.vertices()
        if vertices:
            start = vertices[0]
            visited = {start}
            queue = deque([start])
            while queue:
                v = queue.popleft()
                for e in net.graph.adjacent(v):
                    if e.dest not in visited:
                        visited.add(e.dest)
                        queue.append(e.dest)
            unreachable = len(vertices) - len(visited)
            if unreachable:
                self.warnings.append(f"Network is not fully connected: {unreachable} stations unreachable "
                                     f"from '{net.number_to_station[start]}'")
        self.connection_valid = ok
        return ok

    def check_distances(self):
        ok = True
        pair_distances = defaultdict(set)
        for conn in self.network.connections:
            d = conn.distance
            if isinstance(d, bool) or not isinstance(d, (int, float)):
                ok = False
                self.errors.append(f"Non-numeric distance {conn.source} - {conn.dest}: {d!r}")
                continue
            if d < MIN_VALID_DISTANCE or d > MAX_VALID_DISTANCE:
                ok = False
                self.errors.append(f"Distance out of range {conn.source} - {conn.dest}: {d} m")
                continue
            if d < SUSPICIOUS_SHORT_DISTANCE:
                self.warnings.append(f"Unusually short distance {conn.source} - {conn.dest}: {d} m")
            elif d > SUSPICIOUS_LONG_DISTANCE:
                self.warnings.append(f"Unusually long distance {conn.source} - {conn.dest}: {d} m")
            pair_distances[(frozenset((conn.source, conn.dest)), conn.line)].add(d)
        for (pair, line), values in pair_distances.items():
            if len(values) > 1:
                self.warnings.append(f"Inconsistent distances for {' - '.join(sorted(pair))} ({line}): "
                                     f"{sorted(values)}")
        self.distance_valid = ok
        return ok

    def run_all(self):
        self.errors, self.warnings, self.info = [], [], []
        self.check_coverage()
        self.check_connections()
        self.check_distances()
        return {
            "coverage_valid": self.coverage_valid,
            "connection_valid": self.connection_valid,
            "distance_valid": self.distance_valid,
            "valid": bool(self.coverage_valid and self.connection_valid and self.distance_valid),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "station_count": len(self.network.stations),
            "connection_count": len(self.network.connections),
            "line_count": len(self.network.all_line_names()),
        }

    def format_report(self, result=None):
        result = result or self.run_all()
        status = lambda ok: "PASS" if ok else "FAIL"
        lines = [
            "Data Integrity Check Report",
            "=" * 40,
            f"Stations: {result['station_count']}, Connections: {result['connection_count']}, "
            f"Lines: {result['line_count']}",
            f"Station coverage check:   {status(result['coverage_valid'])}",
            f"Connection integrity:     {status(result['connection_valid'])}",
            f"Distance accuracy check:  {status(result['distance_valid'])}",
        ]
        if result["errors"]:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in result["errors"])
        if result["warnings"]:
            lines.append(f"Warnings ({len(result['warnings'])}):")
            lines.extend(f"  - {w}" for w in result["warnings"][:50])
            if len(result["warnings"]) > 50:
                lines.append(f"  ... {len(result['warnings']) - 50} more")
        lines.append(f"Overall result: {status(result['valid'])}")
        return "\n".join(lines)
