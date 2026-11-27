"""
Subway network data management: building the network model, data integrity
checks, and data update mechanisms.
"""

import copy
import re

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph, Line, Station

#: Main lines that must be covered, with name aliases.
MAIN_LINES = {
    "Line 1": ["line 1", "1号线"],
    "Line 2": ["line 2", "2号线"],
    "Line 4": ["line 4", "4号线"],
    "Line 5": ["line 5", "5号线"],
    "Line 6": ["line 6", "6号线"],
    "Line 8": ["line 8", "8号线"],
    "Line 10": ["line 10", "10号线"],
    "Line 13": ["line 13", "13号线"],
    "Line 14": ["line 14", "14号线"],
    "Line 15": ["line 15", "15号线"],
    "Changping Line": ["changping", "昌平"],
    "Yizhuang Line": ["yizhuang", "亦庄"],
    "Fangshan Line": ["fangshan", "房山"],
    "Airport Line": ["airport", "机场"],
}

MAX_REASONABLE_DISTANCE = 50000  # meters between adjacent stations
MIN_REASONABLE_DISTANCE = 100


def normalize_name(name):
    """Normalize a station name for lookup."""
    if name is None:
        return ""
    s = re.sub(r"\s+", " ", str(name).strip()).casefold()
    for suffix in (" station", "站"):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)].strip()
    return s


def _line_matches(line_name, aliases):
    n = line_name.casefold().strip()
    for alias in aliases:
        if alias.startswith("line "):
            if n == alias:
                return True
        elif alias.endswith("号线"):
            if n == alias or n == "地铁" + alias:
                return True
        elif alias in n:
            return True
    return False


class SubwayNetwork:
    """The subway network: stations, lines, connections and graph model."""

    def __init__(self, data=None, data_source=DATA_FILE_PATH):
        self.data_source = data_source
        if data is None:
            data = load_subway_data(data_source)
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.rebuild()

    # ---- building -------------------------------------------------------
    def rebuild(self):
        """(Re)build all derived structures from ``self.data``."""
        self.stations = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self.issues = []

        for entry in self.data["stations"]:
            name = entry.get("name")
            if not name:
                self.issues.append(f"Station entry without name: {entry!r}")
                continue
            if name in self.stations:
                st = self.stations[name]
                for ln in entry.get("lines", []):
                    if ln not in st.lines:
                        st.lines.append(ln)
                self.issues.append(f"Duplicate station entry: '{name}'")
                continue
            self._register_station(name, entry.get("lines", []))

        self.graph = {name: [] for name in self.stations}
        self.graph_obj = Graph()
        for name, st in self.stations.items():
            self.graph_obj.add_station(st.number, name)

        for conn in self.data["connections"]:
            a, b = conn.get("source"), conn.get("dest")
            dist, line = conn.get("distance"), conn.get("line")
            if not a or not b:
                self.issues.append(f"Connection with missing endpoint: {conn!r}")
                continue
            for n in (a, b):
                if n not in self.stations:
                    self.issues.append(f"Connection references unknown station '{n}'")
                    self._register_station(n, [line] if line else [])
                    self.graph[n] = []
                    self.graph_obj.add_station(self.stations[n].number, n)
                if line and line not in self.stations[n].lines:
                    self.stations[n].lines.append(line)
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
                self.issues.append(f"Invalid distance in connection {a} - {b}: {dist!r}")
                continue
            self.graph[a].append((b, dist, line))
            self.graph[b].append((a, dist, line))
            self.graph_obj.add_edge(Edge(self.station_to_number[a], self.station_to_number[b], dist, line))

        for name, st in self.stations.items():
            self.graph_obj.set_station_lines(name, st.lines)

        self._lookup = {}
        for name in self.stations:
            self._lookup.setdefault(normalize_name(name), name)
        self._build_lines()

    def _register_station(self, name, lines):
        number = len(self.station_to_number)
        self.stations[name] = Station(name, number, list(lines))
        self.station_to_number[name] = number
        self.number_to_station[number] = name

    def _build_lines(self):
        per_line = {}
        for conn in self.data["connections"]:
            line, a, b = conn.get("line"), conn.get("source"), conn.get("dest")
            if not line or not a or not b:
                continue
            adj = per_line.setdefault(line, {})
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        for st in self.stations.values():
            for ln in st.lines:
                per_line.setdefault(ln, {}).setdefault(st.name, set())

        self.lines = {}
        for line, adj in per_line.items():
            ends = sorted(s for s, n in adj.items() if len(n) == 1)
            start = ends[0] if ends else (sorted(adj)[0] if adj else None)
            seq, visited = [], set()
            cur = start
            while cur is not None:
                seq.append(cur)
                visited.add(cur)
                nxt = [n for n in sorted(adj[cur]) if n not in visited]
                cur = nxt[0] if nxt else None
            seq.extend(s for s in sorted(adj) if s not in visited)
            transfer_info = {
                s: [ln for ln in self.stations[s].lines if ln != line]
                for s in seq if s in self.stations and self.stations[s].is_transfer_station
            }
            self.lines[line] = Line(line, seq, transfer_info)

    # ---- lookup ---------------------------------------------------------
    def find_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name is None:
            return None
        if name in self.stations:
            return name
        return self._lookup.get(normalize_name(name))

    def find_line(self, name):
        if name in self.lines:
            return name
        n = normalize_name(name)
        for ln in self.lines:
            if normalize_name(ln) == n:
                return ln
        return None

    # ---- data updates ---------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and segment distances."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have exactly len(station_names) - 1 entries")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance: {d!r}")
        existing = {s["name"]: s for s in self.data["stations"]}
        for name in station_names:
            if name in existing:
                lines = existing[name].setdefault("lines", [])
                if line_name not in lines:
                    lines.append(line_name)
            else:
                entry = {"name": name, "lines": [line_name]}
                self.data["stations"].append(entry)
                existing[name] = entry
        for (a, b), d in zip(zip(station_names, station_names[1:]), distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        official = self.find_station(name)
        if official is None:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != official and new_name in self.stations:
            raise ValueError(f"Station '{new_name}' already exists")
        for entry in self.data["stations"]:
            if entry.get("name") == official:
                if new_name:
                    entry["name"] = new_name
                if lines is not None:
                    entry["lines"] = list(lines)
        if new_name:
            for conn in self.data["connections"]:
                if conn.get("source") == official:
                    conn["source"] = new_name
                if conn.get("dest") == official:
                    conn["dest"] = new_name
        self.rebuild()

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance between two adjacent stations."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Invalid distance: {distance!r}")
        a, b = self.find_station(station_a), self.find_station(station_b)
        if a is None or b is None:
            raise KeyError("Both stations must exist")
        updated = 0
        for conn in self.data["connections"]:
            if {conn.get("source"), conn.get("dest")} == {a, b} and (line is None or conn.get("line") == line):
                conn["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        self.rebuild()
        return updated

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_source)


class DataIntegrityReport:
    """Result of a data integrity check."""

    def __init__(self):
        self.station_coverage_valid = True
        self.connection_integrity_valid = True
        self.distance_accuracy_valid = True
        self.messages = []
        self.stats = {}

    @property
    def is_valid(self):
        return self.station_coverage_valid and self.connection_integrity_valid and self.distance_accuracy_valid

    def to_text(self):
        lines = ["Data Integrity Check", "=" * 40]
        for k, v in self.stats.items():
            lines.append(f"{k}: {v}")
        lines.append("-" * 40)
        lines.append(f"Station coverage:       {'PASS' if self.station_coverage_valid else 'FAIL'}")
        lines.append(f"Connection integrity:   {'PASS' if self.connection_integrity_valid else 'FAIL'}")
        lines.append(f"Distance accuracy:      {'PASS' if self.distance_accuracy_valid else 'FAIL'}")
        if self.messages:
            lines.append("-" * 40)
            lines.extend(f"- {m}" for m in self.messages)
        lines.append("=" * 40)
        lines.append("Overall: " + ("PASS" if self.is_valid else "FAIL"))
        return "\n".join(lines)


def check_data_integrity(network):
    """Run all integrity checks on a ``SubwayNetwork``."""
    report = DataIntegrityReport()
    report.stats = {
        "Stations": len(network.stations),
        "Connections": len(network.data["connections"]),
        "Lines": len(network.lines),
        "Transfer stations": sum(1 for s in network.stations.values() if s.is_transfer_station),
    }

    # Station coverage: each main line must exist with stations.
    all_lines = list(network.lines.keys())
    for main, aliases in MAIN_LINES.items():
        matched = [ln for ln in all_lines if _line_matches(ln, aliases)]
        if not matched or not any(len(network.lines[m].station_sequence) >= 2 for m in matched):
            report.station_coverage_valid = False
            report.messages.append(f"Main line '{main}' is missing or has too few stations")
    if not network.stations:
        report.station_coverage_valid = False
        report.messages.append("No stations in data")

    # Connection integrity.
    known = {s.get("name") for s in network.data["stations"]}
    for conn in network.data["connections"]:
        a, b, line = conn.get("source"), conn.get("dest"), conn.get("line")
        if a not in known or b not in known:
            report.connection_integrity_valid = False
            report.messages.append(f"Connection {a} - {b} references a station not in the station list")
        if a == b:
            report.connection_integrity_valid = False
            report.messages.append(f"Self-loop connection at '{a}'")
        if not line:
            report.connection_integrity_valid = False
            report.messages.append(f"Connection {a} - {b} has no line")
    for name, neighbors in network.graph.items():
        if not neighbors:
            report.connection_integrity_valid = False
            report.messages.append(f"Station '{name}' has no connections")
    if network.stations:
        start = next(iter(network.graph))
        seen, stack = {start}, [start]
        while stack:
            cur = stack.pop()
            for nb, _d, _l in network.graph[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if len(seen) != len(network.graph):
            report.connection_integrity_valid = False
            report.messages.append(f"Network is not connected: {len(network.graph) - len(seen)} stations unreachable")

    # Distance accuracy.
    seen_pairs = {}
    for conn in network.data["connections"]:
        a, b, d, line = conn.get("source"), conn.get("dest"), conn.get("distance"), conn.get("line")
        if isinstance(d, bool) or not isinstance(d, (int, float)):
            report.distance_accuracy_valid = False
            report.messages.append(f"Non-numeric distance for {a} - {b}: {d!r}")
            continue
        if d < MIN_REASONABLE_DISTANCE or d > MAX_REASONABLE_DISTANCE:
            report.distance_accuracy_valid = False
            report.messages.append(f"Unreasonable distance for {a} - {b}: {d} m")
        key = (frozenset((a, b)), line)
        if key in seen_pairs and seen_pairs[key] != d:
            report.distance_accuracy_valid = False
            report.messages.append(f"Inconsistent distances for {a} - {b} on {line}: {seen_pairs[key]} vs {d}")
        seen_pairs.setdefault(key, d)

    for issue in network.issues:
        if issue not in report.messages:
            report.messages.append(issue)
    return report
