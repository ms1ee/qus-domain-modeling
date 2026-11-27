"""
Data management module: builds the subway network model from the data file,
provides station lookup/standardization, route queries, data integrity
checks and data update mechanisms.
"""

import copy
import difflib
import re
import unicodedata
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath

MAIN_LINES = {
    "Line 1": ["line 1", "1号线", "地铁1号线", "1号线八通线", "line 1/batong"],
    "Line 2": ["line 2", "2号线", "地铁2号线"],
    "Line 4": ["line 4", "4号线", "4号线大兴线", "line 4/daxing"],
    "Line 5": ["line 5", "5号线"],
    "Line 6": ["line 6", "6号线"],
    "Line 8": ["line 8", "8号线"],
    "Line 10": ["line 10", "10号线"],
    "Line 13": ["line 13", "13号线"],
    "Line 14": ["line 14", "14号线"],
    "Line 15": ["line 15", "15号线"],
    "Changping Line": ["changping line", "changping", "昌平线"],
    "Yizhuang Line": ["yizhuang line", "yizhuang", "亦庄线"],
    "Fangshan Line": ["fangshan line", "fangshan", "房山线"],
    "Airport Line": ["airport line", "airport express", "capital airport express",
                     "首都机场线", "机场线"],
}

# Representative stations (Chinese name, English name) for main lines.
REPRESENTATIVE_STATIONS = {
    "Line 1": [("西单", "Xidan"), ("国贸", "Guomao")],
    "Line 2": [("西直门", "Xizhimen"), ("北京站", "Beijing Railway Station")],
    "Line 4": [("中关村", "Zhongguancun"), ("北京南站", "Beijing South Railway Station")],
    "Line 5": [("天通苑", "Tiantongyuan"), ("宋家庄", "Songjiazhuang")],
    "Line 6": [("车公庄", "Chegongzhuang")],
    "Line 8": [("鼓楼大街", "Guloudajie")],
    "Line 10": [("知春路", "Zhichunlu"), ("国贸", "Guomao")],
    "Line 13": [("西直门", "Xizhimen"), ("东直门", "Dongzhimen")],
    "Line 14": [("望京", "Wangjing")],
    "Line 15": [("望京", "Wangjing")],
    "Changping Line": [("西二旗", "Xi'erqi")],
    "Yizhuang Line": [("宋家庄", "Songjiazhuang")],
    "Fangshan Line": [("郭公庄", "Guogongzhuang")],
    "Airport Line": [("三元桥", "Sanyuanqiao"), ("东直门", "Dongzhimen")],
}

MIN_REASONABLE_DISTANCE = 200       # meters
MAX_REASONABLE_DISTANCE = 30000     # meters


def _norm(text):
    text = unicodedata.normalize("NFKC", str(text)).strip().lower()
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text)


def _compact(text):
    return re.sub(r"[\s'\-·.]", "", _norm(text))


def _strip_suffix(text):
    t = _norm(text)
    if t.endswith("站") and len(t) > 1:
        t = t[:-1]
    elif t.endswith(" station") and len(t) > len(" station"):
        t = t[: -len(" station")]
    return t


class NetworkError(Exception):
    """Raised on invalid data update or query operations."""


class SubwayNetwork:
    """Beijing Subway network model."""

    def __init__(self, data=None, data_path=None):
        self.data_path = data_path or DATA_FILE_PATH
        if data is None:
            data = load_subway_data(self.data_path)
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a JSON object")
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self._rebuild()

    # ------------------------------------------------------------------
    # Model construction
    # ------------------------------------------------------------------
    def _rebuild(self):
        stations = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        self.station_to_number = {}
        self.number_to_station = {}
        self.station_info = {}

        def register(name, lines):
            if name in self.station_to_number:
                existing = self.station_info[name]["lines"]
                for ln in lines:
                    if ln not in existing:
                        existing.append(ln)
                return
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.station_info[name] = {"name": name, "number": number,
                                       "lines": list(lines)}

        for st in stations:
            if isinstance(st, dict) and st.get("name"):
                register(st["name"], st.get("lines", []) or [])

        for c in connections:
            for key in ("source", "dest"):
                name = c.get(key)
                if name and name not in self.station_to_number:
                    register(name, [c["line"]] if c.get("line") else [])
                elif name and c.get("line") and not self.station_info[name]["lines"]:
                    self.station_info[name]["lines"].append(c["line"])

        # Name-based adjacency dictionary (weighted undirected graph).
        self.graph = {name: [] for name in self.station_to_number}
        self.network = Graph()
        for name, info in self.station_info.items():
            self.network.add_vertex(info["number"])
            self.network.set_station_lines(name, info["lines"])

        for c in connections:
            s, d = c.get("source"), c.get("dest")
            dist = c.get("distance")
            if not s or not d or s == d:
                continue
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
                continue
            line = c.get("line", "")
            self.network.add_edge(Edge(self.station_to_number[s],
                                       self.station_to_number[d], dist, line))
            self.graph[s].append({"station": d, "distance": dist, "line": line})
            self.graph[d].append({"station": s, "distance": dist, "line": line})

        self.lines = self._build_line_sequences()
        self._build_name_index()

    def _build_line_sequences(self):
        per_line = defaultdict(dict)
        for c in self.data.get("connections", []):
            s, d, line = c.get("source"), c.get("dest"), c.get("line")
            if not s or not d or not line or s == d:
                continue
            per_line[line].setdefault(s, [])
            per_line[line].setdefault(d, [])
            if d not in per_line[line][s]:
                per_line[line][s].append(d)
            if s not in per_line[line][d]:
                per_line[line][d].append(s)

        lines = {}
        for line, adj in per_line.items():
            ends = [s for s in adj if len(adj[s]) == 1]
            is_loop = not ends and all(len(n) == 2 for n in adj.values())
            order, visited = [], set()
            starts = ends + [s for s in adj if s not in ends]
            for start in starts:
                if start in visited:
                    continue
                stack = [start]
                while stack:
                    v = stack.pop()
                    if v in visited:
                        continue
                    visited.add(v)
                    order.append(v)
                    for w in reversed(adj[v]):
                        if w not in visited:
                            stack.append(w)
            transfers = [s for s in order
                         if len(self.station_info.get(s, {}).get("lines", [])) > 1]
            lines[line] = {"name": line, "stations": order, "is_loop": is_loop,
                           "transfer_stations": transfers}
        return lines

    def _build_name_index(self):
        self._exact = {}
        self._compact_index = {}
        for name in self.station_to_number:
            self._exact.setdefault(_norm(name), name)
        for name in self.station_to_number:
            for key in (_strip_suffix(name),):
                self._exact.setdefault(key, name)
            self._compact_index.setdefault(_compact(name), name)
            self._compact_index.setdefault(_compact(_strip_suffix(name)), name)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def resolve_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name is None:
            return None
        if name in self.station_to_number:
            return name
        for key in (_norm(name), _strip_suffix(name)):
            if key in self._exact:
                return self._exact[key]
        for key in (_compact(name), _compact(_strip_suffix(name))):
            if key and key in self._compact_index:
                return self._compact_index[key]
        return None

    def suggest_stations(self, name, n=3):
        return difflib.get_close_matches(str(name).strip(),
                                         list(self.station_to_number), n=n, cutoff=0.6)

    def all_line_names(self):
        names = set(self.lines)
        for info in self.station_info.values():
            names.update(info["lines"])
        return sorted(names)

    def resolve_line(self, line):
        target = _compact(line)
        for name in self.all_line_names():
            if _compact(name) == target:
                return name
        return None

    def transfer_stations(self):
        return [n for n, i in self.station_info.items() if len(i["lines"]) > 1]

    # ------------------------------------------------------------------
    # Route queries
    # ------------------------------------------------------------------
    def find_route(self, start, end, config=None):
        """Compute a route. Returns dict with station names, edges, distance,
        transfer count; or None if no route satisfies the constraints."""
        if start not in self.station_to_number:
            raise NetworkError(f"Unknown station '{start}'")
        if end not in self.station_to_number:
            raise NetworkError(f"Unknown station '{end}'")
        src = self.station_to_number[start]
        dst = self.station_to_number[end]
        sp = ShortestPath(self.network, src, config or PathfindingConfig())
        if not sp.has_path_to(dst):
            return None
        numbers, edges = sp.path_with_edges(dst)
        return {
            "stations": [self.number_to_station[n] for n in numbers],
            "edges": [{"source": self.number_to_station[e.source],
                       "dest": self.number_to_station[e.dest],
                       "distance": e.distance, "line": e.line} for e in edges],
            "distance": sp.dist_to[dst],
            "transfer_count": sp.get_transfer_count(dst),
        }

    # ------------------------------------------------------------------
    # Integrity check
    # ------------------------------------------------------------------
    def check_data_integrity(self):
        errors, warnings = [], []
        raw_stations = self.data.get("stations", [])
        raw_connections = self.data.get("connections", [])

        declared = {}
        for i, st in enumerate(raw_stations):
            if not isinstance(st, dict) or not st.get("name"):
                errors.append(f"Station entry #{i} has no name")
                continue
            if st["name"] in declared:
                warnings.append(f"Duplicate station entry '{st['name']}'")
            declared[st["name"]] = st.get("lines", []) or []
            if not declared[st["name"]]:
                warnings.append(f"Station '{st['name']}' has no line information")

        seen_pairs = {}
        for i, c in enumerate(raw_connections):
            if not isinstance(c, dict):
                errors.append(f"Connection #{i} is not an object")
                continue
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = f"Connection #{i} ({s} - {d}, {line})"
            if not s or not d:
                errors.append(f"{label}: missing source or destination")
                continue
            for name in (s, d):
                if name not in declared:
                    errors.append(f"{label}: station '{name}' is not in the station list")
            if s == d:
                errors.append(f"{label}: connects a station to itself")
            if not line:
                warnings.append(f"{label}: missing line name")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append(f"{label}: distance is not a number")
                continue
            if dist <= 0:
                errors.append(f"{label}: distance must be positive")
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append(f"{label}: unusual distance {dist} meters")
            if line:
                for name in (s, d):
                    if name in declared and declared[name] and line not in declared[name]:
                        warnings.append(
                            f"{label}: station '{name}' is not marked as on line '{line}'")
            key = (frozenset((s, d)), line)
            if key in seen_pairs:
                if seen_pairs[key] != dist:
                    errors.append(f"{label}: conflicting distances "
                                  f"{seen_pairs[key]} and {dist}")
                else:
                    warnings.append(f"{label}: duplicate connection")
            else:
                seen_pairs[key] = dist

        for name, neighbors in self.graph.items():
            if not neighbors:
                errors.append(f"Station '{name}' has no connections")

        components = self._count_components()
        if components > 1:
            warnings.append(f"Network is not fully connected ({components} components)")

        # Main line coverage
        line_norms = {_compact(n): n for n in self.all_line_names()}
        missing_lines = []
        for main, aliases in MAIN_LINES.items():
            found = any(_compact(a) in line_norms for a in aliases)
            if not found:
                found = any(any(_compact(a) in ln for a in aliases if len(_compact(a)) > 4)
                            for ln in line_norms)
            if not found:
                missing_lines.append(main)
        for ln in missing_lines:
            warnings.append(f"Main line '{ln}' not found in data")

        missing_stations = []
        checked = 0
        for line, reps in REPRESENTATIVE_STATIONS.items():
            for cn, en in reps:
                checked += 1
                if not (self.resolve_station(cn) or self.resolve_station(en)):
                    missing_stations.append(f"{en} ({cn}) [{line}]")
        for s in missing_stations:
            warnings.append(f"Representative station {s} not found")

        stats = {
            "stations": len(self.station_to_number),
            "connections": len(raw_connections),
            "lines": len(self.all_line_names()),
            "transfer_stations": len(self.transfer_stations()),
            "components": components,
            "representative_stations_checked": checked,
            "representative_stations_found": checked - len(missing_stations),
            "main_lines_found": len(MAIN_LINES) - len(missing_lines),
            "main_lines_total": len(MAIN_LINES),
        }
        return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    def _count_components(self):
        seen, count = set(), 0
        for start in self.graph:
            if start in seen:
                continue
            count += 1
            queue = deque([start])
            seen.add(start)
            while queue:
                v = queue.popleft()
                for nb in self.graph[v]:
                    if nb["station"] not in seen:
                        seen.add(nb["station"])
                        queue.append(nb["station"])
        return count

    # ------------------------------------------------------------------
    # Data updates
    # ------------------------------------------------------------------
    def _find_station_entry(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_station(self, name, lines):
        if not name or not str(name).strip():
            raise NetworkError("Station name cannot be empty")
        entry = self._find_station_entry(name)
        if entry is None:
            self.data["stations"].append({"name": name, "lines": list(lines)})
        else:
            for ln in lines:
                if ln not in entry.setdefault("lines", []):
                    entry["lines"].append(ln)
        self._rebuild()

    def add_line(self, line_name, stations, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if not line_name:
            raise NetworkError("Line name cannot be empty")
        if len(stations) < 2:
            raise NetworkError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise NetworkError("Number of distances must equal number of stations - 1")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise NetworkError(f"Invalid distance {d!r}")
        for name in stations:
            entry = self._find_station_entry(name)
            if entry is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in entry.setdefault("lines", []):
                entry["lines"].append(line_name)
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": d, "line": line_name})
        self._rebuild()

    def update_station(self, name, new_name=None, lines=None):
        entry = self._find_station_entry(name)
        if entry is None:
            raise NetworkError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self._find_station_entry(new_name) is not None:
                raise NetworkError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            entry["lines"] = list(lines)
        self._rebuild()

    def update_distance(self, source, dest, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise NetworkError(f"Invalid distance {distance!r}")
        updated = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and \
                    (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise NetworkError(f"No connection between '{source}' and '{dest}'")
        self._rebuild()
        return updated

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_path)
