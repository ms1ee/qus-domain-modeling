"""
Subway network data management: station numbering, graph construction,
data integrity checks and data update mechanisms.
"""

import difflib
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List

try:
    from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
    from models import Edge, Graph, Station, Line
except ImportError:  # pragma: no cover
    from .data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
    from .models import Edge, Graph, Station, Line


MAIN_LINES = {
    "Line 1": ["line1", "1号线", "line1batong", "1号线八通线"],
    "Line 2": ["line2", "2号线"],
    "Line 4": ["line4", "4号线", "line4daxing", "4号线大兴线"],
    "Line 5": ["line5", "5号线"],
    "Line 6": ["line6", "6号线"],
    "Line 8": ["line8", "8号线"],
    "Line 10": ["line10", "10号线"],
    "Line 13": ["line13", "13号线"],
    "Line 14": ["line14", "14号线"],
    "Line 15": ["line15", "15号线"],
    "Changping Line": ["changpingline", "changping", "昌平线"],
    "Yizhuang Line": ["yizhuangline", "yizhuang", "亦庄线"],
    "Fangshan Line": ["fangshanline", "fangshan", "房山线"],
    "Airport Line": ["airportline", "airportexpress", "capitalairportexpress", "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = [
    ("Xidan", "西单"), ("Dongdan", "东单"), ("Xizhimen", "西直门"), ("Dongzhimen", "东直门"),
    ("Jianguomen", "建国门"), ("Fuxingmen", "复兴门"), ("Guomao", "国贸"), ("Xuanwumen", "宣武门"),
    ("Chongwenmen", "崇文门"), ("Haidian Huangzhuang", "海淀黄庄"),
]

MIN_PLAUSIBLE_DISTANCE = 100
MAX_PLAUSIBLE_DISTANCE = 30000


def normalize_name(name):
    """Normalization used for tolerant name matching."""
    return re.sub(r"[\s'’`\-_·.]", "", str(name)).lower()


def build_station_to_number(data):
    """Map station names to numbers (order of appearance, starting at 0)."""
    station_to_number = {}
    for st in data.get("stations", []):
        name = st.get("name") if isinstance(st, dict) else None
        if name and name not in station_to_number:
            station_to_number[name] = len(station_to_number)
    for conn in data.get("connections", []):
        for key in ("source", "dest"):
            name = conn.get(key)
            if name and name not in station_to_number:
                station_to_number[name] = len(station_to_number)
    return station_to_number


def build_graph_dict(data, station_to_number):
    """Adjacency-list dict: number -> list of (neighbor number, distance, line)."""
    graph = {n: [] for n in station_to_number.values()}
    for conn in data.get("connections", []):
        s, d = conn.get("source"), conn.get("dest")
        dist = conn.get("distance")
        if s not in station_to_number or d not in station_to_number:
            continue
        if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
            continue
        a, b = station_to_number[s], station_to_number[d]
        graph[a].append((b, dist, conn.get("line")))
        graph[b].append((a, dist, conn.get("line")))
    return graph


@dataclass
class DataIntegrityReport:
    station_coverage_valid: bool = True
    connection_integrity_valid: bool = True
    distance_accuracy_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def is_valid(self):
        return self.station_coverage_valid and self.connection_integrity_valid and self.distance_accuracy_valid

    def format_text(self):
        def ok(flag):
            return "PASS" if flag else "FAIL"
        lines = ["Data Integrity Check", "=" * 40]
        for k, v in self.stats.items():
            lines.append(f"{k}: {v}")
        lines.append(f"Station coverage:        {ok(self.station_coverage_valid)}")
        lines.append(f"Connection integrity:    {ok(self.connection_integrity_valid)}")
        lines.append(f"Distance accuracy:       {ok(self.distance_accuracy_valid)}")
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings[:50])
            if len(self.warnings) > 50:
                lines.append(f"  ... and {len(self.warnings) - 50} more warnings")
        lines.append("Result: " + ("Data is valid" if self.is_valid else "Data has problems"))
        return "\n".join(lines)


class SubwayNetwork:
    """The Beijing Subway network built from subway_data.json."""

    def __init__(self, data=None, data_file=None):
        self.data_file = data_file or DATA_FILE_PATH
        self.data = data if data is not None else load_subway_data(self.data_file)
        self.rebuild()

    # ---- construction ------------------------------------------------------
    def rebuild(self):
        """(Re)build station numbering and graph structures from self.data."""
        data = self.data
        self.station_to_number = build_station_to_number(data)
        self.number_to_station = {n: s for s, n in self.station_to_number.items()}
        lines_of = defaultdict(list)
        for st in data.get("stations", []):
            if isinstance(st, dict) and st.get("name"):
                for ln in st.get("lines") or []:
                    if ln not in lines_of[st["name"]]:
                        lines_of[st["name"]].append(ln)
        for conn in data.get("connections", []):
            ln = conn.get("line")
            for key in ("source", "dest"):
                name = conn.get(key)
                if name and ln and ln not in lines_of[name]:
                    lines_of[name].append(ln)
        self.station_lines = {name: list(lines_of.get(name, [])) for name in self.station_to_number}

        g = Graph()
        for name, num in self.station_to_number.items():
            g.add_vertex(num)
            g.set_station_lines(name, self.station_lines[name])
        for conn in data.get("connections", []):
            s, d, dist = conn.get("source"), conn.get("dest"), conn.get("distance")
            if s not in self.station_to_number or d not in self.station_to_number or s == d:
                continue
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                continue
            g.add_edge(Edge(self.station_to_number[s], self.station_to_number[d], dist, conn.get("line")))
        self.graph_obj = g
        self.graph = build_graph_dict(data, self.station_to_number)
        self._norm_index = {normalize_name(n): n for n in self.station_to_number}
        self._line_norm_index = {normalize_name(l): l for l in self.all_lines()}

    # ---- lookup ----------------------------------------------------------
    def all_lines(self):
        lines = []
        for ls in self.station_lines.values():
            for l in ls:
                if l not in lines:
                    lines.append(l)
        return lines

    def get_station(self, name):
        if name not in self.station_to_number:
            return None
        return Station(name, self.station_to_number[name], list(self.station_lines.get(name, [])))

    def is_transfer_station(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def transfer_stations(self):
        return [n for n in self.station_to_number if self.is_transfer_station(n)]

    def resolve_station(self, raw):
        """Standardize a user-entered station name; return canonical name or None."""
        if raw is None:
            return None
        name = " ".join(str(raw).strip().split())
        if not name:
            return None
        if name in self.station_to_number:
            return name
        n = normalize_name(name)
        if n in self._norm_index:
            return self._norm_index[n]
        for suffix in ("站", "station", "subwaystation"):
            if n.endswith(suffix) and n[: -len(suffix)] in self._norm_index:
                return self._norm_index[n[: -len(suffix)]]
        return None

    def suggest_stations(self, raw, n=3):
        return difflib.get_close_matches(str(raw).strip(), list(self.station_to_number), n=n, cutoff=0.6)

    def resolve_line(self, raw):
        if raw is None:
            return None
        n = normalize_name(raw)
        if n in self._line_norm_index:
            return self._line_norm_index[n]
        if n.isdigit() and normalize_name(f"Line {n}") in self._line_norm_index:
            return self._line_norm_index[normalize_name(f"Line {n}")]
        return None

    def get_line_stations(self, line):
        """Return the ordered station sequence of a line (derived from connections)."""
        adj = defaultdict(list)
        for conn in self.data.get("connections", []):
            if conn.get("line") == line:
                s, d = conn.get("source"), conn.get("dest")
                if d not in adj[s]:
                    adj[s].append(d)
                if s not in adj[d]:
                    adj[d].append(s)
        if not adj:
            return [s for s, ls in self.station_lines.items() if line in ls]
        ends = [s for s, nb in adj.items() if len(nb) == 1]
        start = ends[0] if ends else next(iter(adj))
        seq, seen = [], set()
        stack = [start]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            seq.append(cur)
            for nb in reversed(adj[cur]):
                if nb not in seen:
                    stack.append(nb)
        return seq

    def get_lines(self):
        return [Line(l, self.get_line_stations(l)) for l in self.all_lines()]

    # ---- integrity check -------------------------------------------------
    def check_data(self):
        r = DataIntegrityReport()
        data = self.data
        stations = data.get("stations", [])
        conns = data.get("connections", [])
        declared = set()
        r.stats = {
            "Stations": len(self.station_to_number),
            "Connections": len(conns),
            "Lines": len(self.all_lines()),
            "Transfer stations": len(self.transfer_stations()),
        }

        # Station coverage
        if not stations:
            r.station_coverage_valid = False
            r.errors.append("No station data found")
        for st in stations:
            if not isinstance(st, dict) or not st.get("name"):
                r.station_coverage_valid = False
                r.errors.append(f"Invalid station entry: {st!r}")
                continue
            if st["name"] in declared:
                r.warnings.append(f"Duplicate station entry '{st['name']}'")
            declared.add(st["name"])
            if not st.get("lines"):
                r.warnings.append(f"Station '{st['name']}' has no line information")
        line_counts = defaultdict(int)
        for ls in self.station_lines.values():
            for l in ls:
                line_counts[normalize_name(l)] += 1
        for main, aliases in MAIN_LINES.items():
            found = 0
            for norm_line, cnt in line_counts.items():
                for a in [normalize_name(main)] + [normalize_name(x) for x in aliases]:
                    if norm_line == a or (norm_line.startswith(a) and not norm_line[len(a):len(a) + 1].isdigit()):
                        found = max(found, cnt)
            if found < 2:
                r.station_coverage_valid = False
                r.errors.append(f"Main line '{main}' is missing or has fewer than 2 stations")
        norm_names = set(self._norm_index)
        for en, zh in REPRESENTATIVE_STATIONS:
            if normalize_name(en) not in norm_names and normalize_name(zh) not in norm_names:
                r.warnings.append(f"Representative station '{en}' ({zh}) not found")

        # Connection integrity
        seen_pairs = {}
        for i, c in enumerate(conns):
            s, d, line = c.get("source"), c.get("dest"), c.get("line")
            if not s or not d:
                r.connection_integrity_valid = False
                r.errors.append(f"Connection #{i} missing source/dest")
                continue
            for name in (s, d):
                if name not in declared:
                    r.connection_integrity_valid = False
                    r.errors.append(f"Connection #{i} references unknown station '{name}'")
            if s == d:
                r.connection_integrity_valid = False
                r.errors.append(f"Connection #{i} is a self-loop at '{s}'")
            if not line:
                r.connection_integrity_valid = False
                r.errors.append(f"Connection #{i} ({s} - {d}) has no line")
            else:
                for st in stations:
                    if isinstance(st, dict) and st.get("name") in (s, d) and line not in (st.get("lines") or []):
                        r.warnings.append(f"Station '{st['name']}' does not list line '{line}'")
            key = (frozenset((s, d)), line)
            dist = c.get("distance")
            if key in seen_pairs:
                if seen_pairs[key] != dist:
                    r.distance_accuracy_valid = False
                    r.errors.append(f"Inconsistent distances for {s} - {d} on {line}: {seen_pairs[key]} vs {dist}")
                else:
                    r.warnings.append(f"Duplicate connection {s} - {d} on {line}")
            else:
                seen_pairs[key] = dist

            # Distance accuracy
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                r.distance_accuracy_valid = False
                r.errors.append(f"Connection {s} - {d} has non-numeric distance {dist!r}")
            elif dist <= 0:
                r.distance_accuracy_valid = False
                r.errors.append(f"Connection {s} - {d} has non-positive distance {dist}")
            elif not (MIN_PLAUSIBLE_DISTANCE <= dist <= MAX_PLAUSIBLE_DISTANCE):
                r.warnings.append(f"Connection {s} - {d} has unusual distance {dist} m")

        # Isolated stations / connectivity
        g = self.graph_obj
        isolated = [self.number_to_station[v] for v in g.vertices if g.degree(v) == 0]
        if isolated:
            r.connection_integrity_valid = False
            r.errors.append(f"Stations without connections: {', '.join(isolated[:20])}")
        if g.vertices:
            start = g.vertices[0]
            seen = {start}
            q = deque([start])
            while q:
                v = q.popleft()
                for e in g.adj(v):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        q.append(e.dest)
            unreached = len(g.vertices) - len(seen)
            if unreached and not isolated:
                r.connection_integrity_valid = False
                r.errors.append(f"Network is not connected: {unreached} stations unreachable")
        return r

    # ---- data updates ------------------------------------------------------
    def _station_entry(self, name):
        for st in self.data["stations"]:
            if isinstance(st, dict) and st.get("name") == name:
                return st
        return None

    def add_station(self, name, lines=None):
        entry = self._station_entry(name)
        if entry is None:
            self.data["stations"].append({"name": name, "lines": list(lines or [])})
        else:
            for l in lines or []:
                entry.setdefault("lines", [])
                if l not in entry["lines"]:
                    entry["lines"].append(l)
        self.rebuild()

    def add_line(self, line_name, stations, distances):
        """Add a new line given its ordered stations and inter-station distances (m)."""
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have exactly len(stations) - 1 entries")
        for dist in distances:
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                raise ValueError(f"Invalid distance {dist!r}")
        for name in stations:
            entry = self._station_entry(name)
            if entry is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            else:
                entry.setdefault("lines", [])
                if line_name not in entry["lines"]:
                    entry["lines"].append(line_name)
        for a, b, dist in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": dist, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        entry = self._station_entry(name)
        if entry is None:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self._station_entry(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            entry["lines"] = list(lines)
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Invalid distance {distance!r}")
        updated = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        self.rebuild()
        return updated

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_file)
