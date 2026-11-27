"""
Subway network data management: modelling, integrity checks and updates.
"""

import json
import re
from dataclasses import dataclass, field

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

MIN_REASONABLE_DISTANCE = 100      # meters
MAX_REASONABLE_DISTANCE = 30000    # meters

# Main lines (with naming aliases) required by the PRD.
MAIN_LINES = {
    "Line 1": ["Line 1", "1号线", "地铁1号线"],
    "Line 2": ["Line 2", "2号线", "地铁2号线"],
    "Line 4": ["Line 4", "4号线", "地铁4号线"],
    "Line 5": ["Line 5", "5号线", "地铁5号线"],
    "Line 6": ["Line 6", "6号线", "地铁6号线"],
    "Line 8": ["Line 8", "8号线", "地铁8号线"],
    "Line 10": ["Line 10", "10号线", "地铁10号线"],
    "Line 13": ["Line 13", "13号线", "地铁13号线"],
    "Line 14": ["Line 14", "14号线", "地铁14号线"],
    "Line 15": ["Line 15", "15号线", "地铁15号线"],
    "Changping Line": ["Changping Line", "Changping", "昌平线"],
    "Yizhuang Line": ["Yizhuang Line", "Yizhuang", "亦庄线"],
    "Fangshan Line": ["Fangshan Line", "Fangshan", "房山线"],
    "Airport Line": ["Airport Line", "Airport Express", "Capital Airport Express",
                     "Capital Airport Line", "首都机场线", "机场线"],
}

# Representative stations (aliases) of main lines.
REPRESENTATIVE_STATIONS = {
    "Line 1": [("Xidan", "西单"), ("Guomao", "国贸")],
    "Line 2": [("Xizhimen", "西直门"), ("Dongzhimen", "东直门")],
    "Line 4": [("Beijing South Railway Station", "Beijingnan Railway Station", "北京南站"),
               ("Zhongguancun", "中关村")],
    "Line 5": [("Dongdan", "东单"), ("Yonghegong Lama Temple", "Yonghegong", "雍和宫")],
    "Line 10": [("Sanyuanqiao", "三元桥"), ("Zhichunlu", "知春路")],
    "Line 13": [("Huilongguan", "回龙观"), ("Wangjing West", "望京西")],
    "Airport Line": [("Terminal 3", "T3", "3号航站楼"), ("Terminal 2", "T2", "2号航站楼")],
}


def _norm(text):
    return re.sub(r"[\s\-_'’.,()（）]", "", str(text)).casefold()


def _line_matches(data_line, alias):
    d, a = _norm(data_line), _norm(alias)
    if d == a:
        return True
    return d.startswith(a) and not d[len(a)].isdigit()


@dataclass
class IntegrityReport:
    """Result of a data integrity check."""
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

    def to_text(self):
        def flag(ok):
            return "PASS" if ok else "FAIL"
        lines = ["Data integrity check report", "=" * 40]
        for k, v in self.stats.items():
            lines.append(f"{k}: {v}")
        lines.append("-" * 40)
        lines.append(f"Station data coverage: {flag(self.station_coverage_valid)}")
        lines.append(f"Connection integrity: {flag(self.connection_integrity_valid)}")
        lines.append(f"Distance data accuracy: {flag(self.distance_accuracy_valid)}")
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        lines.append("Overall result: " + ("PASS" if self.is_valid else "FAIL"))
        return "\n".join(lines)


class SubwayNetwork:
    """Beijing Subway network: stations, lines, connections and graph model."""

    def __init__(self, data=None, data_file=DATA_FILE_PATH):
        self.data_source_file = data_file
        if data is None:
            data = load_subway_data(data_file)
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a JSON object")
        self.station_order = []
        self.stations = {}           # name -> list of lines
        for st in data.get("stations", []) or []:
            name = str(st.get("name", "")).strip()
            if not name:
                continue
            if name not in self.stations:
                self.station_order.append(name)
                self.stations[name] = []
            for line in st.get("lines", []) or []:
                if line not in self.stations[name]:
                    self.stations[name].append(line)
        self.connections = []
        for c in data.get("connections", []) or []:
            self.connections.append({
                "source": str(c.get("source", "")).strip(),
                "dest": str(c.get("dest", "")).strip(),
                "distance": c.get("distance"),
                "line": c.get("line"),
            })
        self.rebuild()

    # ----- model building ---------------------------------------------------
    def rebuild(self):
        """(Re)build station numbering, the Graph and the adjacency dictionary."""
        self.station_to_number = {}
        self.number_to_station = {}
        for name in self.station_order:
            self._assign_number(name)
        for c in self.connections:
            for name in (c["source"], c["dest"]):
                if name and name not in self.station_to_number:
                    self._assign_number(name)

        self.graph = Graph()
        for name, num in self.station_to_number.items():
            self.graph.add_vertex(num)
            self.graph.set_station_lines(name, self.stations.get(name, []))

        self.adjacency = {name: [] for name in self.station_to_number}
        self.lines = {}
        for c in self.connections:
            s, d, dist, line = c["source"], c["dest"], c["distance"], c["line"]
            if not s or not d or not isinstance(dist, (int, float)) or dist < 0:
                continue
            self.graph.add_edge(Edge(self.station_to_number[s], self.station_to_number[d], dist, line))
            self.adjacency[s].append({"station": d, "distance": dist, "line": line})
            self.adjacency[d].append({"station": s, "distance": dist, "line": line})
            seq = self.lines.setdefault(line, [])
            for n in (s, d):
                if n not in seq:
                    seq.append(n)
        # also register lines that only appear on stations
        for name, lines in self.stations.items():
            for line in lines:
                self.lines.setdefault(line, [])
                if name not in self.lines[line]:
                    self.lines[line].append(name)
        self._lookup = {}
        for name in self.station_to_number:
            for key in self._lookup_keys(name):
                self._lookup.setdefault(key, name)

    def _assign_number(self, name):
        num = len(self.station_to_number)
        self.station_to_number[name] = num
        self.number_to_station[num] = name

    @staticmethod
    def _lookup_keys(name):
        n = _norm(name)
        keys = [n]
        for suffix in ("station", "站"):
            if n.endswith(suffix) and len(n) > len(suffix):
                keys.append(n[: -len(suffix)])
        return keys

    @property
    def graph_dict(self):
        return self.adjacency

    # ----- lookup -------------------------------------------------------------
    def find_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        name = str(name).strip()
        if name in self.station_to_number:
            return name
        for key in self._lookup_keys(name):
            if key in self._lookup:
                return self._lookup[key]
        return None

    def station_exists(self, name):
        return self.find_station(name) is not None

    def get_station_lines(self, name):
        return list(self.stations.get(name, []))

    def is_transfer_station(self, name):
        return len(self.stations.get(name, [])) > 1

    def transfer_stations(self):
        return [n for n in self.station_order if self.is_transfer_station(n)]

    def all_line_names(self):
        return sorted(l for l in self.lines if l)

    def find_line(self, name):
        for line in self.lines:
            if line and _line_matches(line, name):
                return line
        return None

    # ----- data updates ------------------------------------------------------
    def add_station(self, name, lines=None):
        name = name.strip()
        if not name:
            raise ValueError("Station name cannot be empty")
        if name not in self.stations:
            self.station_order.append(name)
            self.stations[name] = []
        for line in lines or []:
            if line not in self.stations[name]:
                self.stations[name].append(line)
        self.rebuild()

    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance {d!r}")
        for name in station_names:
            if name not in self.stations:
                self.station_order.append(name)
                self.stations[name] = []
            if line_name not in self.stations[name]:
                self.stations[name].append(line_name)
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.connections.append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        if name not in self.stations:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if new_name in self.stations:
                raise ValueError(f"Station '{new_name}' already exists")
            self.stations[new_name] = self.stations.pop(name)
            self.station_order[self.station_order.index(name)] = new_name
            for c in self.connections:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name
            name = new_name
        if lines is not None:
            self.stations[name] = list(dict.fromkeys(lines))
        self.rebuild()

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance between two adjacent stations; returns count updated."""
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        count = 0
        for c in self.connections:
            if {c["source"], c["dest"]} == {station_a, station_b} and (line is None or c["line"] == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{station_a}' and '{station_b}'")
        self.rebuild()
        return count

    def to_dict(self):
        return {
            "stations": [{"name": n, "lines": list(self.stations[n])} for n in self.station_order],
            "connections": [dict(c) for c in self.connections],
        }

    def save(self, path=None):
        path = path or self.data_source_file
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)

    # ----- integrity check --------------------------------------------------
    def check_integrity(self):
        rep = IntegrityReport()
        rep.stats = {
            "Stations": len(self.station_to_number),
            "Connections": len(self.connections),
            "Lines": len([l for l in self.lines if l]),
            "Transfer stations": len(self.transfer_stations()),
        }
        if not self.station_order:
            rep.station_coverage_valid = False
            rep.errors.append("No station data found")

        # coverage of main lines
        data_lines = [l for l in self.lines if l]
        for main, aliases in MAIN_LINES.items():
            if not any(_line_matches(dl, a) for dl in data_lines for a in aliases):
                rep.warnings.append(f"Main line '{main}' not found in data")
        for main, reps in REPRESENTATIVE_STATIONS.items():
            for aliases in reps:
                if not any(self.find_station(a) for a in aliases):
                    rep.warnings.append(
                        f"Representative station '{aliases[0]}' of {main} not found")

        # connection integrity
        seen = {}
        for i, c in enumerate(self.connections):
            s, d, line = c["source"], c["dest"], c["line"]
            label = f"connection #{i + 1} ({s} - {d})"
            if not s or not d:
                rep.connection_integrity_valid = False
                rep.errors.append(f"{label}: missing endpoint")
                continue
            if s == d:
                rep.connection_integrity_valid = False
                rep.errors.append(f"{label}: connects a station to itself")
            for n in (s, d):
                if n not in self.stations:
                    rep.connection_integrity_valid = False
                    rep.errors.append(f"{label}: station '{n}' not in station list")
                elif line and self.stations[n] and line not in self.stations[n]:
                    rep.warnings.append(f"{label}: station '{n}' is not listed on line '{line}'")
            if not line:
                rep.warnings.append(f"{label}: missing line name")
            dist = c["distance"]
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                rep.distance_accuracy_valid = False
                rep.errors.append(f"{label}: invalid distance {dist!r}")
            else:
                if not (MIN_REASONABLE_DISTANCE <= dist <= MAX_REASONABLE_DISTANCE):
                    rep.warnings.append(f"{label}: unusual distance {dist} m")
                key = (frozenset((s, d)), line)
                if key in seen and seen[key] != dist:
                    rep.distance_accuracy_valid = False
                    rep.errors.append(f"{label}: inconsistent duplicate distance "
                                      f"({seen[key]} vs {dist})")
                seen.setdefault(key, dist)

        isolated = [n for n in self.station_order if not self.adjacency.get(n)]
        for n in isolated:
            rep.connection_integrity_valid = False
            rep.errors.append(f"Station '{n}' has no connections")

        # connectivity
        if self.station_to_number:
            start = next(iter(self.station_to_number))
            visited = {start}
            stack = [start]
            while stack:
                v = stack.pop()
                for nb in self.adjacency.get(v, []):
                    if nb["station"] not in visited:
                        visited.add(nb["station"])
                        stack.append(nb["station"])
            unreachable = len(self.station_to_number) - len(visited)
            if unreachable:
                rep.warnings.append(f"{unreachable} station(s) are not reachable from '{start}'")
        return rep
