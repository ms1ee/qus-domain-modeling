"""Subway network data management: graph building, integrity check, updates."""

import copy
import re
from collections import deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

MAIN_LINES = [
    ("Line 1", "1号线"), ("Line 2", "2号线"), ("Line 4", "4号线"), ("Line 5", "5号线"),
    ("Line 6", "6号线"), ("Line 8", "8号线"), ("Line 10", "10号线"), ("Line 13", "13号线"),
    ("Line 14", "14号线"), ("Line 15", "15号线"), ("Changping Line", "昌平线"),
    ("Yizhuang Line", "亦庄线"), ("Fangshan Line", "房山线"),
    ("Airport Line", "Capital Airport Express", "首都机场线", "机场线"),
]

REPRESENTATIVE_STATIONS = [
    ("Tian'anmen East", "Tiananmen East", "天安门东"),
    ("Xidan", "西单"),
    ("Dongzhimen", "东直门"),
    ("Xizhimen", "西直门"),
    ("Guomao", "国贸"),
    ("Beijing Railway Station", "Beijing Station", "北京站"),
    ("Zhongguancun", "中关村"),
    ("Huixinxijie Nankou", "惠新西街南口"),
]

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 50000


def normalize_station_name(name):
    """Normalize a station name for tolerant lookup."""
    text = str(name).strip().casefold()
    text = re.sub(r"(\s*station|站)$", "", text)
    return re.sub(r"[\s'’`\-_.·]", "", text)


def _norm_line(name):
    return "".join(str(name).split()).casefold()


class SubwayNetwork:
    """Holds stations, connections and lines, and the derived graph.

    Attributes:
        station_to_number: dict station name -> station number.
        number_to_station: dict station number -> station name.
        graph: :class:`models.Graph` built from the connections.
    """

    def __init__(self, data=None, path=None):
        if data is None:
            data = load_subway_data(path or DATA_FILE_PATH)
        self.data = copy.deepcopy(data)
        self.stations = {}
        self.declared_stations = set()
        for item in self.data.get("stations", []):
            name = item.get("name") if isinstance(item, dict) else None
            if not name:
                continue
            self.declared_stations.add(name)
            lines = self.stations.setdefault(name, [])
            for line in item.get("lines", []) or []:
                if line not in lines:
                    lines.append(line)
        self.connections = [dict(c) for c in self.data.get("connections", []) if isinstance(c, dict)]
        self.rebuild()

    # ----- building ------------------------------------------------------------
    def rebuild(self):
        """(Re)build station numbering and the graph from current data."""
        for c in self.connections:
            for key in ("source", "dest"):
                name = c.get(key)
                if name and name not in self.stations:
                    self.stations[name] = []
                if name and c.get("line") and c["line"] not in self.stations[name]:
                    self.stations[name].append(c["line"])
        self.station_to_number = {}
        self.number_to_station = {}
        for i, name in enumerate(self.stations):
            self.station_to_number[name] = i
            self.number_to_station[i] = name
        self.graph = Graph()
        for name, lines in self.stations.items():
            self.graph.add_node(self.station_to_number[name])
            self.graph.set_station_lines(name, lines)
        for c in self.connections:
            try:
                s, d = c["source"], c["dest"]
                if s == d:
                    continue
                self.graph.add_edge(Edge(self.station_to_number[s], self.station_to_number[d],
                                         c["distance"], c.get("line", "")))
            except (KeyError, TypeError, ValueError):
                continue  # reported by check_integrity
        self._norm_index = {}
        for name in self.stations:
            self._norm_index.setdefault(normalize_station_name(name), name)

    # ----- lookups ---------------------------------------------------------------
    def find_station(self, name):
        """Return the canonical station name for ``name`` or None."""
        if name is None:
            return None
        if name in self.stations:
            return name
        return self._norm_index.get(normalize_station_name(name))

    def suggest_stations(self, name, limit=3):
        import difflib
        norm = normalize_station_name(name)
        matches = difflib.get_close_matches(norm, list(self._norm_index.keys()), n=limit, cutoff=0.6)
        return [self._norm_index[m] for m in matches]

    def all_lines(self):
        lines = []
        for ls in self.stations.values():
            for line in ls:
                if line not in lines:
                    lines.append(line)
        for c in self.connections:
            if c.get("line") and c["line"] not in lines:
                lines.append(c["line"])
        return lines

    def transfer_stations(self):
        return [n for n, ls in self.stations.items() if len(ls) > 1]

    def line_stations(self, line):
        """Return the station sequence of a line (derived from connections)."""
        adj = {}
        for c in self.connections:
            if c.get("line") != line:
                continue
            adj.setdefault(c["source"], []).append(c["dest"])
            adj.setdefault(c["dest"], []).append(c["source"])
        if not adj:
            return [n for n, ls in self.stations.items() if line in ls]
        ends = [n for n, nb in adj.items() if len(nb) == 1]
        start = ends[0] if ends else next(iter(adj))
        order, seen, stack = [], set(), [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            order.append(node)
            for nb in reversed(adj[node]):
                if nb not in seen:
                    stack.append(nb)
        for node in adj:
            if node not in seen:
                order.append(node)
        return order

    # ----- updates -------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in station_names:
            lines = self.stations.setdefault(name, [])
            if line_name not in lines:
                lines.append(line_name)
            self.declared_stations.add(name)
        for i, d in enumerate(distances):
            self.connections.append({"source": station_names[i], "dest": station_names[i + 1],
                                     "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its lines."""
        canonical = self.find_station(name)
        if canonical is None:
            raise KeyError("Station '%s' does not exist" % name)
        if new_name and new_name != canonical:
            if new_name in self.stations:
                raise ValueError("Station '%s' already exists" % new_name)
            self.stations = {(new_name if k == canonical else k): v for k, v in self.stations.items()}
            self.declared_stations.discard(canonical)
            self.declared_stations.add(new_name)
            for c in self.connections:
                for key in ("source", "dest"):
                    if c.get(key) == canonical:
                        c[key] = new_name
            canonical = new_name
        if lines is not None:
            self.stations[canonical] = list(dict.fromkeys(lines))
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update (or create, if ``line`` is given) a connection distance."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        s, d = self.find_station(source), self.find_station(dest)
        if s is None or d is None:
            raise KeyError("Unknown station: %s" % (source if s is None else dest))
        updated = 0
        for c in self.connections:
            if {c.get("source"), c.get("dest")} == {s, d} and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            if line is None:
                raise KeyError("No connection between '%s' and '%s'" % (s, d))
            self.connections.append({"source": s, "dest": d, "distance": distance, "line": line})
            updated = 1
        self.rebuild()
        return updated

    def to_data(self):
        return {"stations": [{"name": n, "lines": list(ls)} for n, ls in self.stations.items()],
                "connections": [dict(c) for c in self.connections]}

    def save(self, path=DATA_FILE_PATH):
        save_subway_data(self.to_data(), path)

    # ----- integrity check -----------------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks; returns a report dict."""
        errors, warnings = [], []
        norm_lines = {_norm_line(l) for l in self.all_lines()}
        for aliases in MAIN_LINES:
            if not any(_norm_line(a) in norm_lines for a in aliases):
                warnings.append("Main line '%s' not found in data" % aliases[0])
        for aliases in REPRESENTATIVE_STATIONS:
            if not any(self.find_station(a) for a in aliases):
                warnings.append("Representative station '%s' not found in data" % aliases[0])

        seen_pairs = set()
        connected = set()
        for i, c in enumerate(self.connections):
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = "Connection #%d (%s - %s)" % (i, s, d)
            if not s or not d:
                errors.append("%s: missing endpoint" % label)
                continue
            for name in (s, d):
                if name not in self.declared_stations:
                    errors.append("%s: station '%s' not declared in station list" % (label, name))
            if s == d:
                errors.append("%s: source equals destination" % label)
            if not line:
                errors.append("%s: missing line" % label)
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append("%s: invalid distance %r" % (label, dist))
            elif dist <= 0:
                errors.append("%s: non-positive distance %r" % (label, dist))
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append("%s: suspicious distance %r m" % (label, dist))
            if line:
                for name in (s, d):
                    if name in self.declared_stations and line not in self.stations.get(name, []):
                        warnings.append("%s: station '%s' not listed on line '%s'" % (label, name, line))
            pair = (frozenset((s, d)), line)
            if pair in seen_pairs:
                warnings.append("%s: duplicate connection" % label)
            seen_pairs.add(pair)
            connected.update((s, d))

        for name in self.stations:
            if name not in connected:
                errors.append("Station '%s' has no connections" % name)

        components = self._component_count()
        if components > 1:
            warnings.append("Network has %d disconnected components" % components)

        stats = {"stations": len(self.stations), "connections": len(self.connections),
                 "lines": len(self.all_lines()), "transfer_stations": len(self.transfer_stations()),
                 "components": components}
        return {"passed": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    def _component_count(self):
        seen, count = set(), 0
        for v in self.graph.graph:
            if v in seen:
                continue
            count += 1
            queue = deque([v])
            seen.add(v)
            while queue:
                u = queue.popleft()
                for e in self.graph.graph[u]:
                    if e.dest not in seen:
                        seen.add(e.dest)
                        queue.append(e.dest)
        return count


def format_integrity_report(report):
    stats = report["stats"]
    lines = ["Data integrity check",
             "=" * 40,
             "Stations: %d" % stats["stations"],
             "Connections: %d" % stats["connections"],
             "Lines: %d" % stats["lines"],
             "Transfer stations: %d" % stats["transfer_stations"],
             "Connected components: %d" % stats["components"],
             "Errors: %d" % len(report["errors"])]
    lines += ["  - " + e for e in report["errors"]]
    lines.append("Warnings: %d" % len(report["warnings"]))
    lines += ["  - " + w for w in report["warnings"]]
    lines.append("Result: %s" % ("PASSED" if report["passed"] else "FAILED"))
    return "\n".join(lines)
