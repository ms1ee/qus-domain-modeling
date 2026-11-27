"""Subway network data management: modelling, station lookup, integrity
checks and data updates."""

import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# (English name, Chinese name) of representative stations of main lines.
REPRESENTATIVE_STATIONS = [
    ("Xidan", "西单"),
    ("Xizhimen", "西直门"),
    ("Dongzhimen", "东直门"),
    ("Jianguomen", "建国门"),
    ("Dongdan", "东单"),
    ("Guomao", "国贸"),
    ("Zhichunlu", "知春路"),
    ("Huilongguan", "回龙观"),
    ("Sanyuanqiao", "三元桥"),
]

_ZH_LINE_KEYS = {
    "昌平": "changpingline",
    "亦庄": "yizhuangline",
    "房山": "fangshanline",
    "机场": "airportline",
    "八通": "batongline",
    "大兴": "daxingline",
}


def line_keys(name):
    """Return normalized identifiers of a line name for fuzzy matching."""
    keys = set()
    if not isinstance(name, str):
        return keys
    raw = name.strip()
    low = re.sub(r"[\s_\-]+", "", raw.lower())
    keys.add(low)
    m = re.match(r"^line(\d+)", low) or re.match(r"^(\d+)号线", low) or re.match(r"^(\d+)$", low)
    if m:
        keys.add(f"line{int(m.group(1))}")
    for zh, key in _ZH_LINE_KEYS.items():
        if raw.startswith(zh):
            keys.add(key)
    for en in ("changping", "yizhuang", "fangshan", "batong", "daxing"):
        if low.startswith(en):
            keys.add(f"{en}line")
    if "airport" in low:
        keys.add("airportline")
    return keys


def _station_key(name):
    s = name.strip().lower()
    s = re.sub(r"(\s+station|站)$", "", s)
    return re.sub(r"[\s\-'’.·]+", "", s)


@dataclass
class Station:
    name: str
    number: int
    lines: list = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


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
        return (self.station_coverage_valid and self.connection_integrity_valid
                and self.distance_accuracy_valid)

    def format_report(self):
        def flag(ok):
            return "PASS" if ok else "FAIL"
        lines = ["Data integrity check report", "=" * 30]
        for key, value in self.stats.items():
            lines.append(f"{key}: {value}")
        lines.append(f"Station coverage:      {flag(self.station_coverage_valid)}")
        lines.append(f"Connection integrity:  {flag(self.connection_integrity_valid)}")
        lines.append(f"Distance accuracy:     {flag(self.distance_accuracy_valid)}")
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        lines.append("Overall result: " + ("PASS" if self.is_valid else "FAIL"))
        return "\n".join(lines)


class SubwayNetwork:
    """The Beijing Subway network built from ``subway_data.json``."""

    def __init__(self, data=None, data_file=None):
        self.data_source_file = data_file or DATA_FILE_PATH
        if data is None:
            data = load_subway_data(self.data_source_file)
        self._load(data)

    # ----- construction -----------------------------------------------
    def _load(self, data):
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a dictionary")
        self.station_records = OrderedDict()
        for item in data.get("stations", []) or []:
            if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                continue
            name = str(item["name"]).strip()
            lines = item.get("lines", []) or []
            if isinstance(lines, str):
                lines = [lines]
            existing = self.station_records.setdefault(name, [])
            for line in lines:
                if line not in existing:
                    existing.append(line)
        self.connection_records = []
        for item in data.get("connections", []) or []:
            if isinstance(item, dict):
                self.connection_records.append({
                    "source": str(item.get("source", "")).strip(),
                    "dest": str(item.get("dest", "")).strip(),
                    "distance": item.get("distance"),
                    "line": item.get("line"),
                })
        self.rebuild()

    @staticmethod
    def _valid_distance(value):
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and value == value and value >= 0)

    def _valid_connections(self):
        for c in self.connection_records:
            if (c["source"] in self.station_records and c["dest"] in self.station_records
                    and c["source"] != c["dest"] and self._valid_distance(c["distance"])):
                yield c

    def rebuild(self):
        """(Re)build station numbering, the graph and line sequences."""
        self.station_to_number = {}
        self.number_to_station = {}
        for idx, name in enumerate(self.station_records):
            self.station_to_number[name] = idx
            self.number_to_station[idx] = name

        merged_lines = {name: list(lines) for name, lines in self.station_records.items()}
        for c in self._valid_connections():
            for end in (c["source"], c["dest"]):
                if c["line"] and c["line"] not in merged_lines[end]:
                    merged_lines[end].append(c["line"])

        self.graph = Graph()
        self.stations = OrderedDict()
        for name, num in self.station_to_number.items():
            self.graph.add_vertex(num)
            self.graph.set_station_lines(name, merged_lines[name])
            self.stations[name] = Station(name, num, list(merged_lines[name]))

        seen = set()
        for c in self._valid_connections():
            key = (frozenset((c["source"], c["dest"])), c["line"])
            if key in seen:
                continue
            seen.add(key)
            self.graph.add_edge(Edge(self.station_to_number[c["source"]],
                                     self.station_to_number[c["dest"]],
                                     c["distance"], c["line"]))

        self.lines = self._build_line_sequences(merged_lines)
        self._name_index = {}
        for name in self.station_records:
            self._name_index.setdefault(_station_key(name), name)

    def _build_line_sequences(self, merged_lines):
        per_line = OrderedDict()
        for c in self._valid_connections():
            adj = per_line.setdefault(c["line"], OrderedDict())
            adj.setdefault(c["source"], OrderedDict())[c["dest"]] = True
            adj.setdefault(c["dest"], OrderedDict())[c["source"]] = True
        result = OrderedDict()
        for line, adj in per_line.items():
            nodes = list(adj)
            starts = [n for n in nodes if len(adj[n]) == 1] + nodes
            ordered, visited = [], set()
            for st in starts:
                if st in visited:
                    continue
                stack = [st]
                while stack:
                    n = stack.pop()
                    if n in visited:
                        continue
                    visited.add(n)
                    ordered.append(n)
                    stack.extend(reversed([x for x in adj[n] if x not in visited]))
            result[line] = ordered
        for name, lines in merged_lines.items():
            for line in lines:
                seq = result.setdefault(line, [])
                if name not in seq:
                    seq.append(name)
        return result

    # ----- lookups --------------------------------------------------------
    def resolve_station(self, raw):
        """Map user input to an official station name (or None)."""
        if not isinstance(raw, str):
            return None
        s = raw.strip().strip("\"'“”「」『』")
        s = re.sub(r"\s+", " ", s)
        if not s:
            return None
        if s in self.station_to_number:
            return s
        return self._name_index.get(_station_key(s))

    def resolve_line(self, raw):
        """Map a line name (e.g. 'Line 1' or '1号线') to a line in the data."""
        if not isinstance(raw, str) or not raw.strip():
            return None
        raw = raw.strip()
        if raw in self.lines:
            return raw
        wanted = line_keys(raw)
        for line in self.lines:
            if wanted & line_keys(line):
                return line
        return None

    def get_station(self, name):
        return self.stations.get(name)

    def transfer_stations(self):
        return [s.name for s in self.stations.values() if s.is_transfer_station]

    # ----- updates --------------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line given its station sequence and inter-station distances."""
        if not line_name or not isinstance(line_name, str):
            raise ValueError("Line name must be a non-empty string")
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if not self._valid_distance(d) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in stations:
            lines = self.station_records.setdefault(name.strip(), [])
            if line_name not in lines:
                lines.append(line_name)
        for a, b, d in zip(stations, stations[1:], distances):
            self.connection_records.append(
                {"source": a.strip(), "dest": b.strip(), "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        if name not in self.station_records:
            raise KeyError(f"Station '{name}' does not exist")
        if lines is not None:
            self.station_records[name] = list(dict.fromkeys(lines))
        if new_name and new_name != name:
            if new_name in self.station_records:
                raise ValueError(f"Station '{new_name}' already exists")
            self.station_records = OrderedDict(
                (new_name if k == name else k, v) for k, v in self.station_records.items())
            for c in self.connection_records:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations.

        If no connection exists and ``line`` is given, a new one is added.
        """
        if not self._valid_distance(distance) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        found = False
        for c in self.connection_records:
            if {c["source"], c["dest"]} == {source, dest} and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if not found:
            if line is None:
                raise KeyError(f"No connection between '{source}' and '{dest}'")
            for s in (source, dest):
                if s not in self.station_records:
                    raise KeyError(f"Station '{s}' does not exist")
            self.connection_records.append(
                {"source": source, "dest": dest, "distance": distance, "line": line})
        self.rebuild()

    def to_dict(self):
        return {
            "stations": [{"name": n, "lines": list(l)} for n, l in self.station_records.items()],
            "connections": [dict(c) for c in self.connection_records],
        }

    def save(self, path=None):
        with open(path or self.data_source_file, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)

    # ----- integrity --------------------------------------------------------
    def check_integrity(self):
        return check_data_integrity(self)


def check_data_integrity(network):
    """Run coverage, connection and distance checks on a network."""
    report = DataIntegrityCheck()
    records = network.station_records
    conns = network.connection_records
    report.stats = {
        "Stations": len(records),
        "Connections": len(conns),
        "Lines": len(network.lines),
        "Transfer stations": len(network.transfer_stations()),
    }

    # --- station coverage ---
    if not records:
        report.station_coverage_valid = False
        report.errors.append("No station data found")
    for main in MAIN_LINES:
        actual = network.resolve_line(main)
        if actual is None:
            report.station_coverage_valid = False
            report.errors.append(f"Main line '{main}' is missing from the data")
        elif len(network.lines.get(actual, [])) < 2:
            report.station_coverage_valid = False
            report.errors.append(f"Main line '{main}' has fewer than two stations")
    for en, zh in REPRESENTATIVE_STATIONS:
        if network.resolve_station(en) is None and network.resolve_station(zh) is None:
            report.warnings.append(f"Representative station '{en}' ({zh}) not found")
    for name, lines in records.items():
        if not lines:
            report.warnings.append(f"Station '{name}' has no line affiliation")

    # --- connection integrity ---
    connected = set()
    for i, c in enumerate(conns):
        label = f"Connection #{i + 1} ({c['source']} - {c['dest']})"
        ok = True
        for end in ("source", "dest"):
            if c[end] not in records:
                report.connection_integrity_valid = False
                report.errors.append(f"{label}: station '{c[end]}' is not defined")
                ok = False
        if c["source"] == c["dest"]:
            report.connection_integrity_valid = False
            report.errors.append(f"{label}: connects a station to itself")
            ok = False
        if not c.get("line"):
            report.connection_integrity_valid = False
            report.errors.append(f"{label}: missing line")
        elif ok:
            for end in ("source", "dest"):
                if c["line"] not in records[c[end]]:
                    report.warnings.append(
                        f"{label}: station '{c[end]}' does not list line '{c['line']}'")
        if ok:
            connected.update((c["source"], c["dest"]))
    for name in records:
        if name not in connected:
            report.connection_integrity_valid = False
            report.errors.append(f"Station '{name}' has no connections")
    # connectivity
    graph = network.graph
    if graph.vertex_count:
        start = next(iter(graph.graph))
        seen, stack = {start}, [start]
        while stack:
            v = stack.pop()
            for e in graph.adj(v):
                if e.dest not in seen:
                    seen.add(e.dest)
                    stack.append(e.dest)
        if len(seen) != graph.vertex_count:
            report.connection_integrity_valid = False
            report.errors.append(
                f"Network is not fully connected: {graph.vertex_count - len(seen)} "
                "station(s) unreachable")

    # --- distance accuracy ---
    pair_dist = {}
    for i, c in enumerate(conns):
        label = f"Connection #{i + 1} ({c['source']} - {c['dest']})"
        d = c["distance"]
        if isinstance(d, bool) or not isinstance(d, (int, float)) or d != d:
            report.distance_accuracy_valid = False
            report.errors.append(f"{label}: distance is not a number")
            continue
        if d <= 0:
            report.distance_accuracy_valid = False
            report.errors.append(f"{label}: distance must be positive (got {d})")
            continue
        if d < 200 or d > 30000:
            report.warnings.append(f"{label}: unusual distance {d} m")
        key = (frozenset((c["source"], c["dest"])), c.get("line"))
        if key in pair_dist and pair_dist[key] != d:
            report.distance_accuracy_valid = False
            report.errors.append(
                f"{label}: conflicting distances {pair_dist[key]} m and {d} m")
        pair_dist.setdefault(key, d)
    return report
