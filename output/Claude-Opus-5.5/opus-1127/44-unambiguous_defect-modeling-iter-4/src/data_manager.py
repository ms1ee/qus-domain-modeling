"""
Subway network data management: building the graph from the JSON data,
station name lookup, line information, data updates and integrity checks.
"""

import difflib
import json
import re
import unicodedata
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph
from pathfinding import ShortestPath, PathfindingConfig


def normalize_name(name):
    """Normalise a station/line name for tolerant matching."""
    s = unicodedata.normalize("NFKC", str(name)).strip().lower()
    s = re.sub(r"[\s'’`\-_.·]", "", s)
    for suffix in ("station", "站"):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
    return s


def normalize_line(name):
    s = unicodedata.normalize("NFKC", str(name)).strip().lower()
    return re.sub(r"[\s'’`\-_.]", "", s)


class SubwayNetwork:
    """The Beijing Subway network.

    Attributes:
        data_source_file:  path of the data file
        stations:          dict[name, {"name", "number", "lines"}]
        station_to_number: dict[name, int]
        number_to_station: dict[int, name]
        connections:       list of {"source", "dest", "distance", "line"}
        graph:             dict[number, list[(neighbor, distance, line)]]
        graph_obj:         ``models.Graph`` instance used for path finding
    """

    def __init__(self, data=None, data_source_file=DATA_FILE_PATH):
        self.data_source_file = data_source_file
        if data is None:
            data = load_subway_data(data_source_file)
        self.stations = {}
        self.connections = []
        self.load_issues = []
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = {}
        self.graph_obj = Graph()
        self._lookup = {}
        self._next_number = 0
        self._load(data)

    # ------------------------------------------------------------ loading
    def _register_station(self, name, lines):
        if name in self.stations:
            for ln in lines:
                if ln not in self.stations[name]["lines"]:
                    self.stations[name]["lines"].append(ln)
            return
        self.stations[name] = {"name": name, "number": self._next_number,
                               "lines": list(lines)}
        self._next_number += 1

    def _load(self, data):
        for st in data.get("stations", []) or []:
            if not isinstance(st, dict) or not st.get("name"):
                self.load_issues.append(f"Invalid station record: {st!r}")
                continue
            name = str(st["name"]).strip()
            lines = [str(x) for x in (st.get("lines") or [])]
            if name in self.stations:
                self.load_issues.append(f"Duplicate station record: '{name}'")
            self._register_station(name, lines)

        for c in data.get("connections", []) or []:
            if not isinstance(c, dict):
                self.load_issues.append(f"Invalid connection record: {c!r}")
                continue
            src, dst = c.get("source"), c.get("dest")
            if not src or not dst:
                self.load_issues.append(f"Connection missing endpoint: {c!r}")
                continue
            src, dst = str(src).strip(), str(dst).strip()
            line = c.get("line")
            for endpoint in (src, dst):
                if endpoint not in self.stations:
                    self.load_issues.append(
                        f"Connection references unknown station '{endpoint}'")
                    self._register_station(endpoint, [line] if line else [])
            self.connections.append({"source": src, "dest": dst,
                                     "distance": c.get("distance"), "line": line})
        self.rebuild()

    @staticmethod
    def _valid_distance(d):
        return (isinstance(d, (int, float)) and not isinstance(d, bool)
                and d == d and d >= 0 and d != float("inf"))

    def rebuild(self):
        """(Re)build the station mapping, adjacency dict and Graph object."""
        self.station_to_number = {n: s["number"] for n, s in self.stations.items()}
        self.number_to_station = {num: n for n, num in self.station_to_number.items()}
        self.graph = {num: [] for num in self.number_to_station}
        self.graph_obj = Graph()
        for num in self.number_to_station:
            self.graph_obj.add_vertex(num)

        extra_lines = defaultdict(list)
        for c in self.connections:
            if not self._valid_distance(c["distance"]):
                continue
            if c["source"] not in self.station_to_number or \
                    c["dest"] not in self.station_to_number:
                continue
            u = self.station_to_number[c["source"]]
            v = self.station_to_number[c["dest"]]
            self.graph_obj.add_edge(Edge(u, v, c["distance"], c["line"]))
            self.graph[u].append((v, c["distance"], c["line"]))
            if u != v:
                self.graph[v].append((u, c["distance"], c["line"]))
            for name in (c["source"], c["dest"]):
                if c["line"] and c["line"] not in extra_lines[name]:
                    extra_lines[name].append(c["line"])

        for name, st in self.stations.items():
            lines = list(st["lines"])
            for ln in extra_lines.get(name, []):
                if ln not in lines:
                    lines.append(ln)
            self.graph_obj.set_station_lines(name, lines)

        self._lookup = {}
        for name in self.stations:
            self._lookup.setdefault(normalize_name(name), name)

    # ------------------------------------------------------------ lookups
    def find_station(self, name):
        """Return the official station name matching ``name`` or ``None``."""
        if name is None:
            return None
        raw = str(name).strip()
        if raw in self.stations:
            return raw
        return self._lookup.get(normalize_name(raw))

    def suggest_stations(self, name, n=3):
        keys = list(self._lookup.keys())
        matches = difflib.get_close_matches(normalize_name(name), keys, n=n, cutoff=0.6)
        return [self._lookup[k] for k in matches]

    def get_station_lines(self, name):
        return self.graph_obj.get_station_lines(name)

    def is_transfer_station(self, name):
        return self.graph_obj.is_transfer_station(name)

    def transfer_stations(self):
        return [n for n in self.stations if self.is_transfer_station(n)]

    def get_line_names(self):
        lines = []
        for st in self.stations.values():
            for ln in st["lines"]:
                if ln not in lines:
                    lines.append(ln)
        for c in self.connections:
            if c["line"] and c["line"] not in lines:
                lines.append(c["line"])
        return lines

    def find_line(self, name):
        """Return the official line name matching ``name`` or ``None``."""
        if not name:
            return None
        lines = self.get_line_names()
        if name in lines:
            return name
        key = normalize_line(name)
        for ln in lines:
            if normalize_line(ln) == key:
                return ln
        # allow "1" -> "Line 1"
        for ln in lines:
            if normalize_line(ln) in (f"line{key}", f"{key}号线"):
                return ln
        return None

    def get_line_stations(self, line):
        """Station sequence of a line, derived from its connections."""
        adj = defaultdict(list)
        first = None
        for c in self.connections:
            if c["line"] != line:
                continue
            if first is None:
                first = c["source"]
            if c["dest"] not in adj[c["source"]]:
                adj[c["source"]].append(c["dest"])
            if c["source"] not in adj[c["dest"]]:
                adj[c["dest"]].append(c["source"])
        if not adj:
            return []
        ends = [s for s in adj if len(adj[s]) == 1]
        start = ends[0] if ends else first
        order, seen, stack = [], set(), [start]
        while stack:
            s = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            order.append(s)
            for nb in reversed(adj[s]):
                if nb not in seen:
                    stack.append(nb)
        for s in adj:  # disconnected parts of a line
            if s not in seen:
                order.append(s)
                seen.add(s)
        return order

    def get_line_info(self):
        info = {}
        for ln in self.get_line_names():
            seq = self.get_line_stations(ln)
            info[ln] = {
                "name": ln,
                "stations": seq,
                "transfer_stations": [s for s in seq if self.is_transfer_station(s)],
            }
        return info

    # ------------------------------------------------------- path finding
    def shortest_path(self, start, end, config=None):
        """Compute a route; return ``(ShortestPath, station names, edges)``."""
        s = self.find_station(start)
        e = self.find_station(end)
        if s is None:
            raise KeyError(f"Unknown station '{start}'")
        if e is None:
            raise KeyError(f"Unknown station '{end}'")
        sp = ShortestPath(self.graph_obj, self.station_to_number[s],
                          config or PathfindingConfig())
        nums, edges = sp.path_with_edges(self.station_to_number[e])
        return sp, [self.number_to_station[n] for n in nums], edges

    # -------------------------------------------------------- data update
    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and segment distances."""
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations - 1")
        for d in distances:
            if not self._valid_distance(d) or d <= 0:
                raise ValueError(f"Invalid distance: {d!r}")
        names = []
        for n in station_names:
            official = self.find_station(n) or str(n).strip()
            names.append(official)
            self._register_station(official, [line_name])
        for i, d in enumerate(distances):
            self.connections.append({"source": names[i], "dest": names[i + 1],
                                     "distance": d, "line": line_name})
        self.rebuild()

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or change its line affiliation."""
        official = self.find_station(name)
        if official is None:
            raise KeyError(f"Unknown station '{name}'")
        st = self.stations[official]
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != official:
            new_name = str(new_name).strip()
            if new_name in self.stations:
                raise ValueError(f"Station '{new_name}' already exists")
            new_stations = {}
            for n, data in self.stations.items():
                if n == official:
                    data["name"] = new_name
                    new_stations[new_name] = data
                else:
                    new_stations[n] = data
            self.stations = new_stations
            for c in self.connections:
                if c["source"] == official:
                    c["source"] = new_name
                if c["dest"] == official:
                    c["dest"] = new_name
        self.rebuild()

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update distance between adjacent stations; return #updated records."""
        if not self._valid_distance(distance) or distance <= 0:
            raise ValueError(f"Invalid distance: {distance!r}")
        a, b = self.find_station(station_a), self.find_station(station_b)
        if a is None or b is None:
            raise KeyError("Unknown station")
        count = 0
        for c in self.connections:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        self.rebuild()
        return count

    def to_dict(self):
        return {
            "stations": [{"name": s["name"], "lines": list(s["lines"])}
                         for s in self.stations.values()],
            "connections": [dict(c) for c in self.connections],
        }

    def save(self, path=None):
        path = path or self.data_source_file
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Data integrity check
# ---------------------------------------------------------------------------

MAIN_LINES = {
    "Line 1": ["Line 1", "1号线", "Line 1/Batong", "1号线八通线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线", "Line 4/Daxing", "4号线大兴线"],
    "Line 5": ["Line 5", "5号线"],
    "Line 6": ["Line 6", "6号线"],
    "Line 8": ["Line 8", "8号线"],
    "Line 10": ["Line 10", "10号线"],
    "Line 13": ["Line 13", "13号线"],
    "Line 14": ["Line 14", "14号线"],
    "Line 15": ["Line 15", "15号线"],
    "Changping Line": ["Changping Line", "Changping", "昌平线"],
    "Yizhuang Line": ["Yizhuang Line", "Yizhuang", "亦庄线"],
    "Fangshan Line": ["Fangshan Line", "Fangshan", "房山线"],
    "Airport Line": ["Airport Line", "Airport Express", "Capital Airport Express",
                     "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = {
    "Xidan": ["Xidan", "西单"],
    "Xizhimen": ["Xizhimen", "西直门"],
    "Dongzhimen": ["Dongzhimen", "东直门"],
    "Guomao": ["Guomao", "国贸"],
    "Beijing Railway Station": ["Beijing Railway Station", "Beijingzhan", "北京站"],
    "Beijing South Railway Station": ["Beijing South Railway Station",
                                      "Beijingnanzhan", "北京南站"],
    "Jianguomen": ["Jianguomen", "建国门"],
    "Fuxingmen": ["Fuxingmen", "复兴门"],
}

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 50000


class DataIntegrityCheck:
    """Runs integrity checks on a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network
        self.station_coverage_valid = False
        self.connection_integrity_valid = False
        self.distance_accuracy_valid = False
        self.errors = []
        self.warnings = []
        self.info = []

    # aliases following the domain model naming
    @property
    def stationCoverageValid(self):
        return self.station_coverage_valid

    @property
    def connectionIntegrityValid(self):
        return self.connection_integrity_valid

    @property
    def distanceAccuracyValid(self):
        return self.distance_accuracy_valid

    @property
    def is_valid(self):
        return self.connection_integrity_valid and self.distance_accuracy_valid

    def run(self):
        self._check_coverage()
        self._check_connections()
        self._check_distances()
        return self

    def _check_coverage(self):
        net = self.network
        line_keys = {normalize_line(ln) for ln in net.get_line_names()}
        missing_lines = []
        for main, aliases in MAIN_LINES.items():
            if not any(normalize_line(a) in line_keys for a in aliases):
                missing_lines.append(main)
        missing_st = []
        for rep, aliases in REPRESENTATIVE_STATIONS.items():
            if not any(net.find_station(a) for a in aliases):
                missing_st.append(rep)
        self.info.append(f"Stations: {len(net.stations)}, connections: "
                         f"{len(net.connections)}, lines: {len(net.get_line_names())}, "
                         f"transfer stations: {len(net.transfer_stations())}")
        if missing_lines:
            self.warnings.append("Main lines not found: " + ", ".join(missing_lines))
        if missing_st:
            self.warnings.append("Representative stations not found: "
                                 + ", ".join(missing_st))
        self.station_coverage_valid = bool(net.stations) and not missing_lines \
            and not missing_st

    def _check_connections(self):
        net = self.network
        errors = list(net.load_issues)
        if not net.connections:
            errors.append("No connections defined")
        connected = set()
        for c in net.connections:
            if c["source"] == c["dest"]:
                errors.append(f"Self-loop connection at '{c['source']}'")
            if not c["line"]:
                self.warnings.append(
                    f"Connection {c['source']} - {c['dest']} has no line")
            for end in (c["source"], c["dest"]):
                connected.add(end)
                if c["line"] and c["line"] not in net.stations.get(end, {}).get("lines", []):
                    self.warnings.append(
                        f"Station '{end}' is not declared on line '{c['line']}'")
        isolated = [n for n in net.stations if n not in connected]
        if isolated:
            errors.append("Stations without connections: " + ", ".join(isolated[:20])
                          + (" ..." if len(isolated) > 20 else ""))
        # connectivity
        if net.graph:
            start = next(iter(net.graph))
            seen = {start}
            dq = deque([start])
            while dq:
                u = dq.popleft()
                for v, _, _ in net.graph[u]:
                    if v not in seen:
                        seen.add(v)
                        dq.append(v)
            unreachable = [net.number_to_station[n] for n in net.graph if n not in seen]
            if unreachable:
                self.warnings.append(
                    f"{len(unreachable)} station(s) not reachable from "
                    f"'{net.number_to_station[start]}': "
                    + ", ".join(unreachable[:10]) + (" ..." if len(unreachable) > 10 else ""))
        self.errors.extend(errors)
        self.connection_integrity_valid = not errors

    def _check_distances(self):
        net = self.network
        errors = []
        seen = {}
        for c in net.connections:
            d = c["distance"]
            label = f"{c['source']} - {c['dest']} ({c['line']})"
            if not net._valid_distance(d) or d <= 0:
                errors.append(f"Invalid distance {d!r} for {label}")
                continue
            if d < MIN_REASONABLE_DISTANCE or d > MAX_REASONABLE_DISTANCE:
                self.warnings.append(f"Unusual distance {d} m for {label}")
            key = (frozenset((c["source"], c["dest"])), c["line"])
            if key in seen and seen[key] != d:
                self.warnings.append(
                    f"Inconsistent duplicate distances for {label}: {seen[key]} vs {d}")
            seen.setdefault(key, d)
        self.errors.extend(errors)
        self.distance_accuracy_valid = not errors

    def report(self):
        def flag(v):
            return "PASS" if v else "FAIL"
        lines = ["Data Integrity Check Report", "=" * 40]
        lines.extend(self.info)
        lines.append(f"Station coverage:       {flag(self.station_coverage_valid)}")
        lines.append(f"Connection integrity:   {flag(self.connection_integrity_valid)}")
        lines.append(f"Distance accuracy:      {flag(self.distance_accuracy_valid)}")
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        lines.append("Overall: " + ("OK" if self.is_valid else "PROBLEMS FOUND"))
        return "\n".join(lines)


def check_data_integrity(network):
    return DataIntegrityCheck(network).run()
