"""Subway data management: graph building, integrity checks and updates."""

import copy
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field

from line_utils import canonical_line_key
from models import Edge, Graph

# Main lines required by the PRD, with representative stations (Chinese and
# English spellings are both accepted).
MAIN_LINES = {
    "line1": ("Line 1", ["西单", "王府井", "天安门西", "Xidan", "Wangfujing"]),
    "line2": ("Line 2", ["西直门", "北京站", "Xizhimen", "Beijing Railway Station"]),
    "line4": ("Line 4", ["北京南站", "动物园", "Beijing South Railway Station", "Beijing Zoo"]),
    "line5": ("Line 5", ["东单", "雍和宫", "Dongdan", "Yonghegong"]),
    "line6": ("Line 6", ["朝阳门", "车公庄", "Chaoyangmen", "Chegongzhuang"]),
    "line8": ("Line 8", ["鼓楼大街", "南锣鼓巷", "Guloudajie", "Nanluoguxiang"]),
    "line10": ("Line 10", ["国贸", "知春路", "Guomao", "Zhichunlu"]),
    "line13": ("Line 13", ["西直门", "东直门", "Xizhimen", "Dongzhimen"]),
    "line14": ("Line 14", ["望京", "Wangjing"]),
    "line15": ("Line 15", ["望京", "Wangjing"]),
    "changping": ("Changping Line", ["西二旗", "Xi'erqi", "Xierqi"]),
    "yizhuang": ("Yizhuang Line", ["宋家庄", "Songjiazhuang"]),
    "fangshan": ("Fangshan Line", ["郭公庄", "Guogongzhuang"]),
    "airport": ("Airport Line", ["东直门", "三元桥", "Dongzhimen", "Sanyuanqiao"]),
}

MIN_REASONABLE_DISTANCE = 100      # meters
MAX_REASONABLE_DISTANCE = 30000    # meters


def build_graph(data):
    """Build a ``Graph`` from subway data; station numbers follow file order."""
    graph = Graph()
    number = 0
    for station in data.get("stations", []) or []:
        name = station.get("name") if isinstance(station, dict) else None
        if not name or name in graph.station_to_number:
            continue
        graph.add_station(name, number, list(station.get("lines", []) or []))
        number += 1
    for conn in data.get("connections", []) or []:
        if not isinstance(conn, dict):
            continue
        src, dst = conn.get("source"), conn.get("dest")
        dist = conn.get("distance")
        line = conn.get("line")
        if not src or not dst or src == dst:
            continue
        if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
            continue
        for name in (src, dst):
            if name not in graph.station_to_number:
                graph.add_station(name, number, [])
                number += 1
            if line and line not in graph.station_lines.get(name, []):
                graph.station_lines.setdefault(name, []).append(line)
        graph.add_edge(Edge(graph.station_to_number[src], graph.station_to_number[dst], dist, line))
    return graph


@dataclass
class DataIntegrityReport:
    """Result of a data integrity check."""
    station_coverage_valid: bool = True
    connection_integrity_valid: bool = True
    distance_accuracy_valid: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def is_valid(self):
        return not self.errors

    def format(self):
        def flag(ok):
            return "PASS" if ok else "WARN/FAIL"
        out = ["===== Data Integrity Check ====="]
        for key, value in self.stats.items():
            out.append("%s: %s" % (key, value))
        out.append("Station coverage: %s" % flag(self.station_coverage_valid))
        out.append("Connection integrity: %s" % flag(self.connection_integrity_valid))
        out.append("Distance accuracy: %s" % flag(self.distance_accuracy_valid))
        if self.errors:
            out.append("Errors (%d):" % len(self.errors))
            out.extend("  - " + e for e in self.errors)
        if self.warnings:
            out.append("Warnings (%d):" % len(self.warnings))
            out.extend("  - " + w for w in self.warnings)
        out.append("Result: %s" % ("PASSED" if self.is_valid else "FAILED"))
        return "\n".join(out)


class SubwayDataManager:
    """Manages subway data (stations, connections, lines) and updates."""

    def __init__(self, data):
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a dict")
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ----- accessors ------------------------------------------------
    @property
    def stations(self):
        return self.data["stations"]

    @property
    def connections(self):
        return self.data["connections"]

    def station_names(self):
        return [s.get("name") for s in self.stations if isinstance(s, dict)]

    def _find_station(self, name):
        for s in self.stations:
            if isinstance(s, dict) and s.get("name") == name:
                return s
        return None

    def build_graph(self):
        return build_graph(self.data)

    def get_lines(self):
        """Return dict line name -> ordered list of station names."""
        adjacency = defaultdict(lambda: defaultdict(list))
        for c in self.connections:
            line = c.get("line")
            if not line:
                continue
            a, b = c.get("source"), c.get("dest")
            adjacency[line][a].append(b)
            adjacency[line][b].append(a)
        for s in self.stations:
            for line in s.get("lines", []) or []:
                adjacency[line].setdefault(s.get("name"), [])
        result = {}
        for line, adj in adjacency.items():
            order, seen = [], set()
            starts = [n for n in adj if len(adj[n]) == 1] + list(adj.keys())
            for start in starts:
                if start in seen:
                    continue
                stack = [start]
                while stack:
                    node = stack.pop()
                    if node in seen:
                        continue
                    seen.add(node)
                    order.append(node)
                    for nxt in reversed(adj[node]):
                        if nxt not in seen:
                            stack.append(nxt)
            result[line] = order
        return result

    def get_transfer_stations(self):
        return [s["name"] for s in self.stations if len(s.get("lines", []) or []) > 1]

    # ----- updates --------------------------------------------------
    def add_station(self, name, lines=None):
        if not name:
            raise ValueError("Station name must not be empty")
        if self._find_station(name) is not None:
            raise ValueError("Station '%s' already exists" % name)
        self.stations.append({"name": name, "lines": list(lines or [])})

    def add_line(self, line_name, station_sequence, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if not line_name:
            raise ValueError("Line name must not be empty")
        if len(station_sequence) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("distances must have len(station_sequence) - 1 entries")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in station_sequence:
            st = self._find_station(name)
            if st is None:
                self.stations.append({"name": name, "lines": [line_name]})
            elif line_name not in st.setdefault("lines", []):
                st["lines"].append(line_name)
        for i, d in enumerate(distances):
            self.connections.append({"source": station_sequence[i], "dest": station_sequence[i + 1],
                                     "distance": d, "line": line_name})

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        st = self._find_station(name)
        if st is None:
            raise ValueError("Station '%s' does not exist" % name)
        if new_name and new_name != name:
            if self._find_station(new_name) is not None:
                raise ValueError("Station '%s' already exists" % new_name)
            st["name"] = new_name
            for c in self.connections:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations (adds if missing and line given)."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        updated = 0
        for c in self.connections:
            pair = {c.get("source"), c.get("dest")}
            if pair == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if updated == 0:
            if line is None:
                raise ValueError("No connection between '%s' and '%s'" % (source, dest))
            for name in (source, dest):
                if self._find_station(name) is None:
                    raise ValueError("Station '%s' does not exist" % name)
            self.connections.append({"source": source, "dest": dest, "distance": distance, "line": line})
            updated = 1
        return updated

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    # ----- integrity check -----------------------------------------
    def check_integrity(self):
        report = DataIntegrityReport()
        names = []
        station_lines = {}
        for i, s in enumerate(self.stations):
            if not isinstance(s, dict) or not s.get("name"):
                report.errors.append("Station entry #%d has no name" % i)
                report.station_coverage_valid = False
                continue
            name = s["name"]
            if name in station_lines:
                report.warnings.append("Duplicate station entry '%s'" % name)
            lines = s.get("lines", []) or []
            if not lines:
                report.warnings.append("Station '%s' has no line information" % name)
            station_lines[name] = lines
            names.append(name)

        # Coverage of main lines and representative stations.
        line_members = defaultdict(set)
        for name, lines in station_lines.items():
            for line in lines:
                line_members[canonical_line_key(line)].add(name)
        for c in self.connections:
            if isinstance(c, dict) and c.get("line"):
                key = canonical_line_key(c["line"])
                line_members[key].update(x for x in (c.get("source"), c.get("dest")) if x)
        for key, (label, reps) in MAIN_LINES.items():
            members = line_members.get(key)
            if not members:
                report.station_coverage_valid = False
                report.warnings.append("Main line '%s' not found in data" % label)
                continue
            if len(members) < 2:
                report.station_coverage_valid = False
                report.warnings.append("Main line '%s' has fewer than 2 stations" % label)
            lowered = {m.casefold() for m in members}
            if not any(r.casefold() in lowered or (r + "站").casefold() in lowered for r in reps):
                report.warnings.append("No representative station found for '%s'" % label)

        # Connections.
        adjacency = defaultdict(set)
        seen_pairs = {}
        for i, c in enumerate(self.connections):
            if not isinstance(c, dict):
                report.errors.append("Connection #%d is malformed" % i)
                report.connection_integrity_valid = False
                continue
            src, dst, line, dist = c.get("source"), c.get("dest"), c.get("line"), c.get("distance")
            label = "%s - %s (%s)" % (src, dst, line)
            if src not in station_lines or dst not in station_lines:
                missing = [x for x in (src, dst) if x not in station_lines]
                report.errors.append("Connection %s references unknown station(s): %s"
                                     % (label, ", ".join(str(m) for m in missing)))
                report.connection_integrity_valid = False
            if src == dst:
                report.errors.append("Connection %s is a self loop" % label)
                report.connection_integrity_valid = False
            if not line:
                report.warnings.append("Connection %s has no line" % label)
            else:
                for n in (src, dst):
                    if n in station_lines and line not in station_lines[n]:
                        report.warnings.append("Station '%s' is not marked as on '%s'" % (n, line))
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                report.errors.append("Connection %s has invalid distance %r" % (label, dist))
                report.distance_accuracy_valid = False
            else:
                if dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                    report.warnings.append("Connection %s has unusual distance %s m" % (label, dist))
                key = (frozenset((src, dst)), line)
                if key in seen_pairs and seen_pairs[key] != dist:
                    report.warnings.append("Connection %s has inconsistent distances %s and %s"
                                           % (label, seen_pairs[key], dist))
                    report.distance_accuracy_valid = False
                seen_pairs[key] = dist
            if src and dst:
                adjacency[src].add(dst)
                adjacency[dst].add(src)

        isolated = [n for n in names if n not in adjacency]
        for n in isolated:
            report.warnings.append("Station '%s' has no connections" % n)
        # Connectivity.
        components = 0
        visited = set()
        for n in adjacency:
            if n in visited:
                continue
            components += 1
            queue = deque([n])
            visited.add(n)
            while queue:
                cur = queue.popleft()
                for nxt in adjacency[cur]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
        if components > 1:
            report.warnings.append("Network has %d disconnected components" % components)

        report.stats = {
            "Stations": len(names),
            "Connections": len(self.connections),
            "Lines": len({l for ls in station_lines.values() for l in ls}
                         | {c.get("line") for c in self.connections if isinstance(c, dict) and c.get("line")}),
            "Transfer stations": sum(1 for ls in station_lines.values() if len(ls) > 1),
        }
        return report
