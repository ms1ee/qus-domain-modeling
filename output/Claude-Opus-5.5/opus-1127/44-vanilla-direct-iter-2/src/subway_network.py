"""
Subway network modeling and data management.

Builds the station_to_number mapping, the adjacency-list ``graph`` dict and a
``Graph`` object from the JSON data, and provides integrity checks and data
update operations (adding lines, modifying stations, updating distances).
"""

import copy
from collections import deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph
from pathfinding import ShortestPath, PathfindingConfig

REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations of main lines (English / Chinese alternatives).
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "西单"],
    "Line 2": ["Xizhimen", "西直门"],
    "Line 4": ["Zhongguancun", "中关村"],
    "Line 5": ["Dongdan", "东单"],
    "Line 6": ["Chaoyangmen", "朝阳门"],
    "Line 8": ["Gulou Dajie", "鼓楼大街"],
    "Line 10": ["Guomao", "国贸"],
    "Line 13": ["Huilongguan", "回龙观"],
    "Line 14": ["Wangjing", "望京"],
    "Line 15": ["Wangjing East", "望京东"],
    "Changping Line": ["Shahe", "沙河"],
    "Yizhuang Line": ["Songjiazhuang", "宋家庄"],
    "Fangshan Line": ["Guogongzhuang", "郭公庄"],
    "Airport Line": ["Sanyuanqiao", "三元桥"],
}

MIN_REASONABLE_DISTANCE = 100       # meters
MAX_REASONABLE_DISTANCE = 30000     # meters


def normalize_name(name):
    """Normalize a station/line name for tolerant matching."""
    if name is None:
        return ""
    s = str(name).strip().lower()
    for ch in (" ", "\t", "'", "’", "`", "-", "_", "·", "　"):
        s = s.replace(ch, "")
    return s


def _strip_suffix(norm):
    for suffix in ("station", "站"):
        if norm.endswith(suffix) and len(norm) > len(suffix):
            return norm[: -len(suffix)]
    return norm


def normalize_line(name):
    s = normalize_name(name)
    if s.endswith("号线"):
        s = "line" + s[:-2]
    return s


class SubwayNetwork:
    """The Beijing Subway network model."""

    def __init__(self, data=None, data_path=DATA_FILE_PATH):
        self.data_path = data_path
        if data is None:
            data = load_subway_data(data_path)
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.build()

    # ------------------------------------------------------------------
    # Model construction
    # ------------------------------------------------------------------
    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = {}                 # number -> [(neighbor, distance, line)]
        self.subway_graph = Graph()
        self.lines = {}                 # line -> set of station names
        self._lookup = {}
        self._line_lookup = {}
        self.load_warnings = []

        station_lines = {}
        for st in self.data["stations"]:
            name = st.get("name") if isinstance(st, dict) else None
            if not name:
                self.load_warnings.append("Station entry without name: %r" % (st,))
                continue
            self._add_station_number(name)
            lst = station_lines.setdefault(name, [])
            for line in st.get("lines", []) or []:
                if line not in lst:
                    lst.append(line)

        for conn in self.data["connections"]:
            try:
                src, dst = conn["source"], conn["dest"]
                dist, line = conn["distance"], conn.get("line", "")
            except (KeyError, TypeError):
                self.load_warnings.append("Malformed connection: %r" % (conn,))
                continue
            for name in (src, dst):
                if name not in self.station_to_number:
                    self.load_warnings.append("Station '%s' used in connection but not declared" % name)
                    self._add_station_number(name)
                lst = station_lines.setdefault(name, [])
                if line and line not in lst:
                    lst.append(line)
            try:
                edge = Edge(self.station_to_number[src], self.station_to_number[dst], dist, line)
            except (TypeError, ValueError) as exc:
                self.load_warnings.append("Invalid connection %s-%s: %s" % (src, dst, exc))
                continue
            self.subway_graph.add_edge(edge)
            a, b = edge.source, edge.dest
            self.graph[a].append((b, dist, line))
            if a != b:
                self.graph[b].append((a, dist, line))

        for name, lines in station_lines.items():
            self.subway_graph.set_station_lines(name, lines)
            for line in lines:
                self.lines.setdefault(line, set()).add(name)
        for line in self.lines:
            self._line_lookup[normalize_line(line)] = line

    def _add_station_number(self, name):
        if name in self.station_to_number:
            return self.station_to_number[name]
        num = len(self.station_to_number)
        self.station_to_number[name] = num
        self.number_to_station[num] = name
        self.graph[num] = []
        self.subway_graph.add_vertex(num)
        norm = normalize_name(name)
        self._lookup.setdefault(norm, name)
        self._lookup.setdefault(_strip_suffix(norm), name)
        return num

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def station_lines(self):
        return self.subway_graph.station_lines

    def find_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name is None:
            return None
        name = str(name).strip()
        if name in self.station_to_number:
            return name
        norm = normalize_name(name)
        if not norm:
            return None
        if norm in self._lookup:
            return self._lookup[norm]
        return self._lookup.get(_strip_suffix(norm))

    def find_line(self, name):
        if name in self.lines:
            return name
        norm = normalize_line(name)
        if norm in self._line_lookup:
            return self._line_lookup[norm]
        if norm.isdigit():
            return self._line_lookup.get("line" + norm)
        return None

    def is_transfer_station(self, name):
        return self.subway_graph.is_transfer_station(name)

    def get_line_stations(self, line):
        """Return the ordered station sequence of a line (derived from connections)."""
        adj = {}
        for e in self.subway_graph.edges():
            if e.line != line:
                continue
            adj.setdefault(e.source, set()).add(e.dest)
            adj.setdefault(e.dest, set()).add(e.source)
        if not adj:
            return []
        ends = sorted(v for v, n in adj.items() if len(n) == 1)
        start = ends[0] if ends else min(adj)
        order, visited, stack = [], set(), [start]
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            order.append(self.number_to_station[v])
            stack.extend(sorted(adj[v] - visited, reverse=True))
        return order

    def find_route(self, start, end, config=None):
        """Compute a route. Returns (station names, edges) or ([], [])."""
        config = config or PathfindingConfig()
        s = self.station_to_number[start]
        t = self.station_to_number[end]
        sp = ShortestPath(self.subway_graph, s, config)
        nodes, edges = sp.path_with_edges(t)
        return [self.number_to_station[n] for n in nodes], edges

    # ------------------------------------------------------------------
    # Integrity check
    # ------------------------------------------------------------------
    def check_integrity(self):
        errors, warnings = [], list(self.load_warnings)
        stats = {
            "stations": len(self.station_to_number),
            "connections": self.subway_graph.E(),
            "lines": len(self.lines),
        }

        # Station coverage
        present_lines = {normalize_line(l) for l in self.lines}
        missing_lines = [l for l in REQUIRED_LINES if normalize_line(l) not in present_lines]
        if missing_lines:
            warnings.append("Main lines missing from data: " + ", ".join(missing_lines))
        missing_rep = []
        for line, candidates in REPRESENTATIVE_STATIONS.items():
            if not any(self.find_station(c) for c in candidates):
                missing_rep.append("%s (%s)" % (candidates[0], line))
        if missing_rep:
            warnings.append("Representative stations not found: " + ", ".join(missing_rep))

        # Station declarations
        names_seen = set()
        for st in self.data["stations"]:
            if not isinstance(st, dict) or not st.get("name"):
                errors.append("Invalid station entry: %r" % (st,))
                continue
            if st["name"] in names_seen:
                warnings.append("Duplicate station entry: %s" % st["name"])
            names_seen.add(st["name"])
            if not st.get("lines"):
                warnings.append("Station '%s' has no line information" % st["name"])

        # Connections
        pairs = set()
        for conn in self.data["connections"]:
            if not isinstance(conn, dict) or any(k not in conn for k in ("source", "dest", "distance")):
                errors.append("Malformed connection: %r" % (conn,))
                continue
            src, dst, dist = conn["source"], conn["dest"], conn["distance"]
            line = conn.get("line")
            if src not in names_seen:
                errors.append("Connection references undeclared station '%s'" % src)
            if dst not in names_seen:
                errors.append("Connection references undeclared station '%s'" % dst)
            if src == dst:
                errors.append("Self-loop connection at '%s'" % src)
            if not line:
                warnings.append("Connection %s-%s has no line" % (src, dst))
            key = (frozenset((src, dst)), line)
            if key in pairs:
                warnings.append("Duplicate connection %s-%s on %s" % (src, dst, line))
            pairs.add(key)
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append("Non-numeric distance for %s-%s" % (src, dst))
            elif dist <= 0:
                errors.append("Non-positive distance %s for %s-%s" % (dist, src, dst))
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append("Suspicious distance %s m for %s-%s" % (dist, src, dst))
            for name in (src, dst):
                if line and name in names_seen:
                    declared = next((s.get("lines", []) for s in self.data["stations"]
                                     if isinstance(s, dict) and s.get("name") == name), [])
                    if declared and line not in declared:
                        warnings.append("Station '%s' is on %s per connections but not declared"
                                        % (name, line))

        # Isolated stations and connectivity
        isolated = [self.number_to_station[v] for v, adj in self.graph.items() if not adj]
        if isolated:
            warnings.append("Isolated stations: " + ", ".join(sorted(isolated)))
        if self.graph:
            start = next(iter(self.graph))
            seen = {start}
            q = deque([start])
            while q:
                v = q.popleft()
                for w, _, _ in self.graph[v]:
                    if w not in seen:
                        seen.add(w)
                        q.append(w)
            unreachable = len(self.graph) - len(seen)
            stats["unreachable_from_first_station"] = unreachable
            if unreachable:
                warnings.append("%d stations are not connected to the main network" % unreachable)

        return {"passed": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line given ordered station names and inter-station distances."""
        if len(stations) < 2 or len(distances) != len(stations) - 1:
            raise ValueError("A line needs >= 2 stations and len(stations)-1 distances")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        existing = {s["name"]: s for s in self.data["stations"]}
        for name in stations:
            if name in existing:
                if line_name not in existing[name].setdefault("lines", []):
                    existing[name]["lines"].append(line_name)
            else:
                entry = {"name": name, "lines": [line_name]}
                self.data["stations"].append(entry)
                existing[name] = entry
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.build()

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        if old_name not in self.station_to_number:
            raise KeyError("Station '%s' does not exist" % old_name)
        if new_name and new_name != old_name and new_name in self.station_to_number:
            raise ValueError("Station '%s' already exists" % new_name)
        for st in self.data["stations"]:
            if st.get("name") == old_name:
                if new_name:
                    st["name"] = new_name
                if lines is not None:
                    st["lines"] = list(lines)
        if new_name:
            for conn in self.data["connections"]:
                if conn.get("source") == old_name:
                    conn["source"] = new_name
                if conn.get("dest") == old_name:
                    conn["dest"] = new_name
        self.build()

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance of an existing connection. Returns number updated."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        updated = 0
        for conn in self.data["connections"]:
            if {conn.get("source"), conn.get("dest")} == {station_a, station_b} and \
                    (line is None or conn.get("line") == line):
                conn["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError("No connection between '%s' and '%s'" % (station_a, station_b))
        self.build()
        return updated

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_path)
