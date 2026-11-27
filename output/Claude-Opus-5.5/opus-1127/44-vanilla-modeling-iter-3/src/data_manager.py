"""Data management: network model, updates and integrity checks."""

import copy
import json
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data
from models import Station, Line, Connection


def normalize_name(name):
    """Normalise a station name for lenient matching."""
    if name is None:
        return ""
    text = str(name).strip().casefold()
    for suffix in (" station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    for ch in " '’‘`-_·.":
        text = text.replace(ch, "")
    return text


class SubwayNetwork:
    """The Beijing Subway network: stations, lines, connections and graph."""

    def __init__(self, data_source_file=DATA_FILE_PATH, data=None):
        self.data_source_file = data_source_file
        if data is None:
            data = load_subway_data(data_source_file)
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.rebuild()

    # ----- building -------------------------------------------------------
    def rebuild(self):
        self.graph, self.station_to_number, self.number_to_station = build_graph(self.data)
        self._lookup = {}
        for name in self.station_to_number:
            key = normalize_name(name)
            self._lookup.setdefault(key, name)

    # ----- queries --------------------------------------------------------
    @property
    def stations(self):
        return [Station(name, num, self.graph.get_station_lines(name))
                for name, num in self.station_to_number.items()]

    @property
    def connections(self):
        return [Connection(c["source"], c["dest"], c["distance"], c.get("line", ""))
                for c in self.data["connections"]]

    def station_exists(self, name):
        return name in self.station_to_number

    def resolve_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name is None:
            return None
        stripped = str(name).strip()
        if stripped in self.station_to_number:
            return stripped
        return self._lookup.get(normalize_name(stripped))

    def get_station_lines(self, name):
        return self.graph.get_station_lines(name)

    def is_transfer_station(self, name):
        return self.graph.is_transfer_station(name)

    def line_names(self):
        names = []
        for lines in self.graph.station_lines.values():
            for line in lines:
                if line not in names:
                    names.append(line)
        for c in self.data["connections"]:
            line = c.get("line")
            if line and line not in names:
                names.append(line)
        return names

    def resolve_line(self, name):
        target = normalize_name(name)
        for line in self.line_names():
            if line == name or normalize_name(line) == target:
                return line
        return None

    def line_stations(self, line):
        """Ordered station sequence of a line, derived from connections."""
        adj = defaultdict(list)
        for c in self.data["connections"]:
            if c.get("line") == line:
                adj[c["source"]].append(c["dest"])
                adj[c["dest"]].append(c["source"])
        if not adj:
            return [n for n, ls in self.graph.station_lines.items() if line in ls]
        ends = [s for s in adj if len(set(adj[s])) == 1]
        start = ends[0] if ends else next(iter(adj))
        order, visited, stack = [], set(), [start]
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            order.append(v)
            for n in reversed(adj[v]):
                if n not in visited:
                    stack.append(n)
        return order

    @property
    def lines(self):
        return [Line(name, self.line_stations(name)) for name in self.line_names()]

    def transfer_stations(self):
        return [n for n in self.station_to_number if self.graph.is_transfer_station(n)]

    # ----- updates --------------------------------------------------------
    def _station_record(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def _ensure_station(self, name, line=None):
        rec = self._station_record(name)
        if rec is None:
            rec = {"name": name, "lines": []}
            self.data["stations"].append(rec)
        rec.setdefault("lines", [])
        if line and line not in rec["lines"]:
            rec["lines"].append(line)
        return rec

    def add_line(self, line_name, stations, distances):
        """Add a new line given its ordered stations and segment distances."""
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must equal number of stations - 1")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in stations:
            self._ensure_station(name, line_name)
        for i, d in enumerate(distances):
            self.data["connections"].append({
                "source": stations[i], "dest": stations[i + 1],
                "distance": int(d), "line": line_name})
        self.rebuild()

    def add_connection(self, source, dest, distance, line):
        if distance <= 0:
            raise ValueError("Distance must be positive")
        self._ensure_station(source, line)
        self._ensure_station(dest, line)
        self.data["connections"].append(
            {"source": source, "dest": dest, "distance": int(distance), "line": line})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        rec = self._station_record(name)
        if rec is None:
            raise KeyError("Station '{}' does not exist".format(name))
        if new_name and new_name != name:
            if self._station_record(new_name) is not None:
                raise ValueError("Station '{}' already exists".format(new_name))
            rec["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            rec["lines"] = list(lines)
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two stations."""
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        updated = 0
        for c in self.data["connections"]:
            pair = {c.get("source"), c.get("dest")}
            if pair == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                updated += 1
        if not updated:
            raise KeyError("No connection between '{}' and '{}'".format(source, dest))
        self.rebuild()
        return updated

    def save(self, path=None):
        target = path or self.data_source_file
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)


# Main lines with name aliases and a representative station (with aliases).
MAIN_LINES = {
    "Line 1": (["Line 1", "1号线", "Line 1 (Batong)", "1号线八通线"], ["Xidan", "西单"]),
    "Line 2": (["Line 2", "2号线"], ["Xizhimen", "西直门"]),
    "Line 4": (["Line 4", "4号线", "Line 4 Daxing", "4号线大兴线"], ["Zhongguancun", "中关村"]),
    "Line 5": (["Line 5", "5号线"], ["Dongdan", "东单"]),
    "Line 6": (["Line 6", "6号线"], ["Chegongzhuang", "车公庄"]),
    "Line 8": (["Line 8", "8号线"], ["Gulou Dajie", "鼓楼大街"]),
    "Line 10": (["Line 10", "10号线"], ["Guomao", "国贸"]),
    "Line 13": (["Line 13", "13号线"], ["Xierqi", "西二旗"]),
    "Line 14": (["Line 14", "14号线"], ["Jintailu", "金台路"]),
    "Line 15": (["Line 15", "15号线"], ["Wangjing", "望京"]),
    "Changping Line": (["Changping Line", "Changping", "昌平线"], ["Xierqi", "西二旗"]),
    "Yizhuang Line": (["Yizhuang Line", "Yizhuang", "亦庄线"], ["Songjiazhuang", "宋家庄"]),
    "Fangshan Line": (["Fangshan Line", "Fangshan", "房山线"], ["Guogongzhuang", "郭公庄"]),
    "Airport Line": (["Airport Line", "Capital Airport Express", "Airport Express",
                      "首都机场线", "机场线"], ["Sanyuanqiao", "三元桥"]),
}

MIN_PLAUSIBLE_DISTANCE = 100      # meters
MAX_PLAUSIBLE_DISTANCE = 30000    # meters


class DataIntegrityChecker:
    """Checks station coverage, connection integrity and distance accuracy."""

    def __init__(self, network):
        self.network = network
        self.station_coverage_valid = False
        self.connection_integrity_valid = False
        self.distance_accuracy_valid = False
        self.errors = []
        self.warnings = []
        self.info = []

    def check_station_coverage(self):
        net = self.network
        line_keys = {normalize_name(l): l for l in net.line_names()}
        missing_lines = []
        for main, (aliases, rep_aliases) in MAIN_LINES.items():
            found = None
            for alias in aliases:
                if normalize_name(alias) in line_keys:
                    found = line_keys[normalize_name(alias)]
                    break
            if found is None:
                missing_lines.append(main)
                continue
            count = len(net.line_stations(found))
            self.info.append("{}: {} stations".format(found, count))
            if not any(net.resolve_station(a) for a in rep_aliases):
                self.warnings.append("Representative station '{}' of {} not found".format(
                    rep_aliases[0], main))
        if missing_lines:
            self.errors.append("Main lines missing: " + ", ".join(missing_lines))
        if not net.station_to_number:
            self.errors.append("No stations in data")
        self.station_coverage_valid = not missing_lines and bool(net.station_to_number)
        return self.station_coverage_valid

    def check_connection_integrity(self):
        net = self.network
        valid = True
        declared = {st.get("name") for st in net.data["stations"]}
        connected = set()
        for i, c in enumerate(net.data["connections"]):
            s, d, line = c.get("source"), c.get("dest"), c.get("line")
            if not s or not d:
                self.errors.append("Connection #{} lacks source/dest".format(i))
                valid = False
                continue
            for name in (s, d):
                if name not in declared:
                    self.errors.append("Connection #{} references undeclared station '{}'"
                                       .format(i, name))
                    valid = False
                elif line and line not in (net._station_record(name) or {}).get("lines", []):
                    self.warnings.append("Station '{}' not listed on line '{}'".format(name, line))
            if s == d:
                self.errors.append("Connection #{} is a self-loop at '{}'".format(i, s))
                valid = False
            connected.update((s, d))
        for name in declared:
            if name not in connected:
                self.warnings.append("Station '{}' has no connections".format(name))
        # connectivity
        graph = net.graph
        verts = graph.vertices()
        if verts:
            seen = {verts[0]}
            queue = deque([verts[0]])
            while queue:
                v = queue.popleft()
                for e in graph.adj.get(v, ()):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        queue.append(e.dest)
            unreachable = [net.number_to_station[v] for v in verts if v not in seen]
            if unreachable:
                self.warnings.append("{} station(s) unreachable from '{}'".format(
                    len(unreachable), net.number_to_station[verts[0]]))
        self.connection_integrity_valid = valid
        return valid

    def check_distance_accuracy(self):
        valid = True
        seen = {}
        for i, c in enumerate(self.network.data["connections"]):
            dist = c.get("distance")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                self.errors.append("Connection #{} has invalid distance {!r}".format(i, dist))
                valid = False
                continue
            if not MIN_PLAUSIBLE_DISTANCE <= dist <= MAX_PLAUSIBLE_DISTANCE:
                self.warnings.append("Connection {} - {} distance {} m looks implausible"
                                     .format(c.get("source"), c.get("dest"), dist))
            key = (frozenset((c.get("source"), c.get("dest"))), c.get("line"))
            if key in seen and seen[key] != dist:
                self.errors.append("Inconsistent distances for {} - {} on {}: {} vs {}".format(
                    c.get("source"), c.get("dest"), c.get("line"), seen[key], dist))
                valid = False
            seen.setdefault(key, dist)
        self.distance_accuracy_valid = valid
        return valid

    def run(self):
        self.errors, self.warnings, self.info = [], [], []
        self.check_station_coverage()
        self.check_connection_integrity()
        self.check_distance_accuracy()
        return {
            "station_coverage_valid": self.station_coverage_valid,
            "connection_integrity_valid": self.connection_integrity_valid,
            "distance_accuracy_valid": self.distance_accuracy_valid,
            "valid": self.is_valid(),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "info": list(self.info),
        }

    def is_valid(self):
        return (self.station_coverage_valid and self.connection_integrity_valid
                and self.distance_accuracy_valid)

    def format_report(self):
        net = self.network
        ok = lambda b: "PASS" if b else "FAIL"
        lines = [
            "===== Data Integrity Check =====",
            "Stations: {}  Connections: {}  Lines: {}".format(
                len(net.station_to_number), len(net.data["connections"]),
                len(net.line_names())),
            "Station coverage:      " + ok(self.station_coverage_valid),
            "Connection integrity:  " + ok(self.connection_integrity_valid),
            "Distance accuracy:     " + ok(self.distance_accuracy_valid),
        ]
        for msg in self.info:
            lines.append("  [INFO] " + msg)
        for msg in self.errors:
            lines.append("  [ERROR] " + msg)
        for msg in self.warnings:
            lines.append("  [WARNING] " + msg)
        lines.append("Overall: " + ("Data integrity check passed"
                                    if self.is_valid() else "Data integrity check found problems"))
        return "\n".join(lines)
