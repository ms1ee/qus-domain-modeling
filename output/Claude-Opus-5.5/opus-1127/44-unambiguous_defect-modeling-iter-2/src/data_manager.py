"""Data management: integrity checks and data update mechanisms."""

import copy
import json
from collections import deque
from dataclasses import dataclass, field
from typing import List

from data_loader import DATA_FILE_PATH, load_subway_data

MAX_REASONABLE_DISTANCE = 50000  # meters between adjacent stations

# Representative stations of main lines (English and Chinese names)
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "西单", "Tiananmen East", "天安门东"],
    "Line 2": ["Jishuitan", "积水潭", "Beijing Railway Station", "北京站"],
    "Line 4": ["Xizhimen", "西直门", "Beijing South Railway Station", "北京南站"],
    "Line 5": ["Dongdan", "东单", "Yonghegong Lama Temple", "雍和宫"],
    "Line 6": ["Chaoyangmen", "朝阳门", "Ping'anli", "平安里"],
    "Line 8": ["Gulou Dajie", "鼓楼大街", "Olympic Green", "奥林匹克公园"],
    "Line 10": ["Guomao", "国贸", "Haidian Huangzhuang", "海淀黄庄"],
    "Line 13": ["Xierqi", "西二旗", "Huilongguan", "回龙观"],
    "Line 14": ["Wangjing", "望京"],
    "Line 15": ["Wangjing East", "望京东"],
    "Changping Line": ["Changping", "昌平"],
    "Yizhuang Line": ["Songjiazhuang", "宋家庄"],
    "Fangshan Line": ["Guogongzhuang", "郭公庄"],
    "Airport Line": ["Sanyuanqiao", "三元桥", "Terminal 3", "3号航站楼"],
}


def _norm(name):
    return "".join(str(name).split()).casefold()


@dataclass
class IntegrityReport:
    station_coverage_valid: bool = True
    connection_integrity_valid: bool = True
    distance_accuracy_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def is_valid(self):
        return (self.station_coverage_valid and self.connection_integrity_valid
                and self.distance_accuracy_valid)

    def to_text(self):
        def mark(ok):
            return "PASS" if ok else "FAIL"
        lines = ["Data integrity check",
                 "  Stations: %(stations)d, Connections: %(connections)d, Lines: %(lines)d" % self.stats,
                 "  Station coverage:      %s" % mark(self.station_coverage_valid),
                 "  Connection integrity:  %s" % mark(self.connection_integrity_valid),
                 "  Distance accuracy:     %s" % mark(self.distance_accuracy_valid)]
        for e in self.errors:
            lines.append("  ERROR: %s" % e)
        for w in self.warnings:
            lines.append("  WARNING: %s" % w)
        lines.append("Result: %s" % ("Data is valid" if self.is_valid else "Data has errors"))
        return "\n".join(lines)


def check_data_integrity(data):
    """Run all integrity checks on raw subway data and return an IntegrityReport."""
    rep = IntegrityReport()
    stations = data.get("stations", []) or []
    connections = data.get("connections", []) or []

    # --- station coverage ---
    names = {}
    all_lines = set()
    if not stations:
        rep.station_coverage_valid = False
        rep.errors.append("No station data found")
    for st in stations:
        name = st.get("name") if isinstance(st, dict) else None
        if not name:
            rep.station_coverage_valid = False
            rep.errors.append("Station entry without a name: %r" % (st,))
            continue
        if name in names:
            rep.warnings.append("Duplicate station entry: %s" % name)
        lines = st.get("lines") or []
        if not lines:
            rep.station_coverage_valid = False
            rep.errors.append("Station '%s' has no line affiliation" % name)
        names[name] = list(lines)
        all_lines.update(lines)
    normalized = {_norm(n) for n in names}
    for line, candidates in REPRESENTATIVE_STATIONS.items():
        if not any(_norm(c) in normalized for c in candidates):
            rep.warnings.append("No representative station found for %s (%s)"
                                % (line, ", ".join(candidates)))

    # --- connection integrity & distance accuracy ---
    adjacency = {n: set() for n in names}
    seen = {}
    for i, c in enumerate(connections):
        if not isinstance(c, dict):
            rep.connection_integrity_valid = False
            rep.errors.append("Connection #%d is not an object" % i)
            continue
        s, d, line, dist = c.get("source"), c.get("dest"), c.get("line"), c.get("distance")
        if not s or not d:
            rep.connection_integrity_valid = False
            rep.errors.append("Connection #%d is missing source/dest" % i)
            continue
        if s == d:
            rep.connection_integrity_valid = False
            rep.errors.append("Connection #%d connects '%s' to itself" % (i, s))
        for n in (s, d):
            if n not in names:
                rep.connection_integrity_valid = False
                rep.errors.append("Connection #%d references unknown station '%s'" % (i, n))
        if line and s in names and line not in names[s]:
            rep.warnings.append("Station '%s' is not listed on %s" % (s, line))
        if line and d in names and line not in names[d]:
            rep.warnings.append("Station '%s' is not listed on %s" % (d, line))
        if isinstance(dist, bool) or not isinstance(dist, (int, float)):
            rep.distance_accuracy_valid = False
            rep.errors.append("Connection %s - %s has invalid distance %r" % (s, d, dist))
        elif dist <= 0 or dist > MAX_REASONABLE_DISTANCE:
            rep.distance_accuracy_valid = False
            rep.errors.append("Connection %s - %s has unreasonable distance %s m" % (s, d, dist))
        else:
            key = (frozenset((s, d)), line)
            if key in seen and seen[key] != dist:
                rep.warnings.append("Inconsistent distances for %s - %s on %s: %s vs %s"
                                    % (s, d, line, seen[key], dist))
            seen.setdefault(key, dist)
        adjacency.setdefault(s, set()).add(d)
        adjacency.setdefault(d, set()).add(s)
        if line:
            all_lines.add(line)

    isolated = [n for n in names if not adjacency.get(n)]
    for n in isolated:
        rep.warnings.append("Station '%s' has no connections" % n)
    if adjacency:
        start = next(iter(adjacency))
        visited = {start}
        dq = deque([start])
        while dq:
            u = dq.popleft()
            for v in adjacency.get(u, ()):
                if v not in visited:
                    visited.add(v)
                    dq.append(v)
        if len(visited) < len(adjacency):
            rep.warnings.append("Network is not fully connected (%d of %d stations reachable)"
                                % (len(visited), len(adjacency)))

    rep.stats = {"stations": len(names), "connections": len(connections), "lines": len(all_lines)}
    return rep


class SubwayDataManager:
    """Maintain subway data: add lines, modify stations, update distances."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = copy.deepcopy(data) if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    def _find_station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_station(self, name, lines):
        st = self._find_station(name)
        if st is None:
            st = {"name": name, "lines": []}
            self.data["stations"].append(st)
        for l in lines:
            if l not in st["lines"]:
                st["lines"].append(l)
        return st

    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be number of stations minus one")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for n in station_names:
            self.add_station(n, [line_name])
        for i, d in enumerate(distances):
            self.data["connections"].append({"source": station_names[i], "dest": station_names[i + 1],
                                             "distance": d, "line": line_name})

    def update_station(self, name, new_name=None, lines=None):
        st = self._find_station(name)
        if st is None:
            raise KeyError("Station '%s' does not exist" % name)
        if new_name and new_name != name:
            if self._find_station(new_name) is not None:
                raise ValueError("Station '%s' already exists" % new_name)
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)
        return st

    def update_distance(self, source, dest, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        count = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError("No connection between '%s' and '%s'" % (source, dest))
        return count

    def check_integrity(self):
        return check_data_integrity(self.data)

    def save(self, path=None):
        with open(path or self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
