"""
Data management: integrity checks and update mechanisms for subway data.
"""

import json
from collections import deque

from data_loader import DATA_FILE_PATH

# Main lines that must be covered, with accepted aliases.
MAIN_LINES = {
    "Line 1": ["line 1", "1号线", "line1"],
    "Line 2": ["line 2", "2号线", "line2"],
    "Line 4": ["line 4", "4号线", "line4", "4号线大兴线", "line 4/daxing line"],
    "Line 5": ["line 5", "5号线", "line5"],
    "Line 6": ["line 6", "6号线", "line6"],
    "Line 8": ["line 8", "8号线", "line8"],
    "Line 10": ["line 10", "10号线", "line10"],
    "Line 13": ["line 13", "13号线", "line13"],
    "Line 14": ["line 14", "14号线", "line14"],
    "Line 15": ["line 15", "15号线", "line15"],
    "Changping Line": ["changping line", "昌平线", "changping"],
    "Yizhuang Line": ["yizhuang line", "亦庄线", "yizhuang"],
    "Fangshan Line": ["fangshan line", "房山线", "fangshan"],
    "Airport Line": ["airport line", "airport express", "首都机场线", "机场线", "capital airport express"],
}

MIN_REASONABLE_DISTANCE = 100      # meters
MAX_REASONABLE_DISTANCE = 30000    # meters


class DataIntegrityReport:
    def __init__(self):
        self.station_coverage_valid = True
        self.connection_integrity_valid = True
        self.distance_accuracy_valid = True
        self.errors = []
        self.warnings = []
        self.stats = {}

    @property
    def is_valid(self):
        return (self.station_coverage_valid and self.connection_integrity_valid
                and self.distance_accuracy_valid)

    def to_text(self):
        out = ["Data integrity check report", "-" * 40]
        for k, v in self.stats.items():
            out.append(f"{k}: {v}")
        out.append(f"Station coverage: {'PASS' if self.station_coverage_valid else 'FAIL'}")
        out.append(f"Connection integrity: {'PASS' if self.connection_integrity_valid else 'FAIL'}")
        out.append(f"Distance accuracy: {'PASS' if self.distance_accuracy_valid else 'FAIL'}")
        for e in self.errors:
            out.append(f"ERROR: {e}")
        for w in self.warnings:
            out.append(f"WARNING: {w}")
        out.append(f"Overall: {'PASS' if self.is_valid else 'FAIL'}")
        return "\n".join(out)


def _norm(s):
    return " ".join(str(s).split()).casefold()


class SubwayDataManager:
    """Manage raw subway data (dict in subway_data.json format)."""

    def __init__(self, data, path=DATA_FILE_PATH):
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.path = path

    # -- lookups ---------------------------------------------------------
    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    # -- integrity check -----------------------------------------------
    def check_integrity(self):
        report = DataIntegrityReport()
        stations = self.data["stations"]
        conns = self.data["connections"]
        names = set()
        all_lines = set()
        for st in stations:
            name = st.get("name")
            if not name:
                report.errors.append("Station without name found")
                report.station_coverage_valid = False
                continue
            if name in names:
                report.warnings.append(f"Duplicate station entry: {name}")
            names.add(name)
            if not st.get("lines"):
                report.warnings.append(f"Station '{name}' has no line information")
            for l in st.get("lines", []) or []:
                all_lines.add(l)
        for c in conns:
            if c.get("line"):
                all_lines.add(c["line"])

        report.stats["Stations"] = len(names)
        report.stats["Connections"] = len(conns)
        report.stats["Lines"] = len(all_lines)

        # Station coverage: main lines present with stations
        normalized = {_norm(l): l for l in all_lines}
        line_counts = {}
        for st in stations:
            for l in st.get("lines", []) or []:
                line_counts[l] = line_counts.get(l, 0) + 1
        if not names:
            report.station_coverage_valid = False
            report.errors.append("No stations in data")
        for main, aliases in MAIN_LINES.items():
            found = None
            for a in [main] + aliases:
                if _norm(a) in normalized:
                    found = normalized[_norm(a)]
                    break
            if found is None:
                report.station_coverage_valid = False
                report.errors.append(f"Main line '{main}' is not covered by the data")
            elif line_counts.get(found, 0) < 2:
                report.warnings.append(f"Line '{found}' has fewer than 2 stations")

        # Connection integrity
        adjacency = {n: set() for n in names}
        for i, c in enumerate(conns):
            s, d = c.get("source"), c.get("dest")
            if s not in names or d not in names:
                report.connection_integrity_valid = False
                report.errors.append(f"Connection #{i} references unknown station(s): {s} - {d}")
                continue
            if s == d:
                report.connection_integrity_valid = False
                report.errors.append(f"Connection #{i} is a self-loop at {s}")
                continue
            adjacency[s].add(d)
            adjacency[d].add(s)
            line = c.get("line")
            for n in (s, d):
                st_lines = (self._station(n) or {}).get("lines", []) or []
                if line and st_lines and line not in st_lines:
                    report.warnings.append(f"Station '{n}' not listed on line '{line}' of its connection")
        isolated = [n for n, nb in adjacency.items() if not nb]
        if isolated:
            report.connection_integrity_valid = False
            report.errors.append(f"Isolated stations: {', '.join(sorted(isolated)[:20])}")
        if names:
            start = next(iter(names))
            seen = {start}
            dq = deque([start])
            while dq:
                v = dq.popleft()
                for w in adjacency[v]:
                    if w not in seen:
                        seen.add(w)
                        dq.append(w)
            if len(seen) != len(names):
                report.connection_integrity_valid = False
                report.errors.append(f"Network not connected: {len(names) - len(seen)} stations unreachable")

        # Distance accuracy
        pair_dist = {}
        for i, c in enumerate(conns):
            dist = c.get("distance")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                report.distance_accuracy_valid = False
                report.errors.append(f"Connection #{i} has invalid distance: {dist}")
                continue
            if dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                report.warnings.append(
                    f"Connection {c.get('source')} - {c.get('dest')} has unusual distance {dist} m")
            key = (frozenset((c.get("source"), c.get("dest"))), c.get("line"))
            if key in pair_dist and pair_dist[key] != dist:
                report.distance_accuracy_valid = False
                report.errors.append(
                    f"Inconsistent distances for {c.get('source')} - {c.get('dest')}: "
                    f"{pair_dist[key]} vs {dist}")
            pair_dist[key] = dist
        return report

    # -- updates -------------------------------------------------------
    def add_station(self, name, lines):
        st = self._station(name)
        if st is None:
            self.data["stations"].append({"name": name, "lines": list(lines)})
        else:
            for l in lines:
                if l not in st.setdefault("lines", []):
                    st["lines"].append(l)

    def add_line(self, line_name, station_names, distances):
        """Add a new line given ordered stations and inter-station distances."""
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if len(station_names) < 2:
            raise ValueError("A line needs at least 2 stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations - 1")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance: {d}")
        for name in station_names:
            self.add_station(name, [line_name])
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})

    def update_station(self, old_name, new_name=None, lines=None):
        st = self._station(old_name)
        if st is None:
            raise KeyError(f"Station '{old_name}' does not exist")
        if new_name and new_name != old_name:
            if self._station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == old_name:
                    c["source"] = new_name
                if c.get("dest") == old_name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)

    def update_distance(self, source, dest, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        count = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return count

    def save(self, path=None):
        with open(path or self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
