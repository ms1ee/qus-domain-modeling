"""Subway data management: integrity checking and data updates."""

import json
import math

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data

MAIN_LINES = {
    "Line 1": ["line1", "1号线", "地铁1号线"],
    "Line 2": ["line2", "2号线", "地铁2号线"],
    "Line 4": ["line4", "4号线", "4号线大兴线", "地铁4号线"],
    "Line 5": ["line5", "5号线", "地铁5号线"],
    "Line 6": ["line6", "6号线", "地铁6号线"],
    "Line 8": ["line8", "8号线", "地铁8号线"],
    "Line 10": ["line10", "10号线", "地铁10号线"],
    "Line 13": ["line13", "13号线", "地铁13号线"],
    "Line 14": ["line14", "14号线", "地铁14号线"],
    "Line 15": ["line15", "15号线", "地铁15号线"],
    "Changping Line": ["changpingline", "changping", "昌平线"],
    "Yizhuang Line": ["yizhuangline", "yizhuang", "亦庄线"],
    "Fangshan Line": ["fangshanline", "fangshan", "房山线"],
    "Airport Line": ["airportline", "capitalairportline", "airportexpress", "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = {
    "Line 1": [["Xidan", "西单"], ["Tian'anmen East", "Tiananmen East", "天安门东"]],
    "Line 2": [["Dongzhimen", "东直门"], ["Xizhimen", "西直门"]],
    "Line 4": [["Xidan", "西单"]],
    "Line 5": [["Dongdan", "东单"]],
    "Line 10": [["Guomao", "国贸"]],
    "Line 13": [["Xizhimen", "西直门"]],
}

MAX_REASONABLE_DISTANCE = 30000
MIN_REASONABLE_DISTANCE = 100


def _norm(name):
    return "".join(str(name).lower().split())


class SubwayDataManager:
    """Manage subway data (stations, connections, lines)."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ---- queries -------------------------------------------------------
    def station_names(self):
        return [s.get("name") for s in self.data["stations"]]

    def get_station(self, name):
        for s in self.data["stations"]:
            if s.get("name") == name:
                return s
        return None

    def get_lines(self):
        lines = []
        for s in self.data["stations"]:
            for ln in s.get("lines", []) or []:
                if ln not in lines:
                    lines.append(ln)
        for c in self.data["connections"]:
            ln = c.get("line")
            if ln and ln not in lines:
                lines.append(ln)
        return lines

    def get_line_sequences(self):
        """Derive station sequences per line from connections."""
        adjacency = {}
        for c in self.data["connections"]:
            ln = c.get("line")
            a, b = c.get("source"), c.get("dest")
            adj = adjacency.setdefault(ln, {})
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        sequences = {}
        for ln, adj in adjacency.items():
            visited = set()
            seq = []
            ends = sorted([s for s, n in adj.items() if len(n) == 1]) or sorted(adj.keys())
            for start in ends + sorted(adj.keys()):
                if start in visited:
                    continue
                cur, prev = start, None
                while cur is not None and cur not in visited:
                    visited.add(cur)
                    seq.append(cur)
                    nxt = [n for n in sorted(adj[cur]) if n != prev and n not in visited]
                    prev, cur = cur, (nxt[0] if nxt else None)
            sequences[ln] = seq
        return sequences

    def build_graph(self):
        return build_graph(self.data)

    # ---- integrity check ---------------------------------------------
    def check_integrity(self):
        errors, warnings, info = [], [], []
        stations = self.data.get("stations", [])
        connections = self.data.get("connections", [])
        names = set()
        for i, s in enumerate(stations):
            name = s.get("name") if isinstance(s, dict) else None
            if not isinstance(name, str) or not name.strip():
                errors.append(f"Station #{i} has no valid name")
                continue
            if name in names:
                warnings.append(f"Duplicate station entry: '{name}'")
            names.add(name)
            if not s.get("lines"):
                warnings.append(f"Station '{name}' has no line affiliation")
        info.append(f"Stations: {len(names)}")
        info.append(f"Connections: {len(connections)}")

        # Coverage of main lines
        all_lines = self.get_lines()
        normalized = {_norm(ln) for ln in all_lines}
        info.append(f"Lines: {len(all_lines)}")
        for main, aliases in MAIN_LINES.items():
            if _norm(main) not in normalized and not any(_norm(a) in normalized for a in aliases):
                warnings.append(f"Main line '{main}' not found in data")
        for line, groups in REPRESENTATIVE_STATIONS.items():
            for group in groups:
                if not any(n in names for n in group):
                    warnings.append(f"Representative station '{group[0]}' ({line}) not found")

        # Connections
        seen = set()
        connected = set()
        for i, c in enumerate(connections):
            src, dst = c.get("source"), c.get("dest")
            dist, line = c.get("distance"), c.get("line")
            label = f"Connection #{i} ({src} - {dst})"
            if src not in names:
                errors.append(f"{label}: unknown source station '{src}'")
            if dst not in names:
                errors.append(f"{label}: unknown destination station '{dst}'")
            if src == dst:
                errors.append(f"{label}: connects a station to itself")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or \
                    (isinstance(dist, float) and (math.isnan(dist) or math.isinf(dist))):
                errors.append(f"{label}: invalid distance {dist!r}")
            elif dist <= 0:
                errors.append(f"{label}: non-positive distance {dist}")
            elif dist > MAX_REASONABLE_DISTANCE:
                warnings.append(f"{label}: unusually long distance {dist} m")
            elif dist < MIN_REASONABLE_DISTANCE:
                warnings.append(f"{label}: unusually short distance {dist} m")
            if not line:
                warnings.append(f"{label}: no line specified")
            key = (frozenset((src, dst)), line)
            if key in seen:
                warnings.append(f"{label}: duplicate connection on {line}")
            seen.add(key)
            connected.add(src)
            connected.add(dst)
            for n in (src, dst):
                st = self.get_station(n) if n in names else None
                if st is not None and line and line not in (st.get("lines") or []):
                    warnings.append(f"{label}: station '{n}' not listed on line '{line}'")
        for n in sorted(names - connected):
            warnings.append(f"Station '{n}' has no connections")

        # Connectivity
        if names:
            adj = {}
            for c in connections:
                a, b = c.get("source"), c.get("dest")
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
            start = next(iter(sorted(names)))
            stack, comp = [start], {start}
            while stack:
                v = stack.pop()
                for w in adj.get(v, ()):
                    if w not in comp:
                        comp.add(w)
                        stack.append(w)
            unreachable = names - comp
            if unreachable:
                warnings.append(f"Network not fully connected: {len(unreachable)} station(s) unreachable from '{start}'")
            else:
                info.append("Network is fully connected")

        return {"passed": not errors, "errors": errors, "warnings": warnings, "info": info}

    @staticmethod
    def format_integrity_report(report):
        out = ["Data integrity check report", "=" * 40]
        out.extend(report["info"])
        out.append(f"Errors: {len(report['errors'])}")
        out.extend("  [ERROR] " + e for e in report["errors"])
        out.append(f"Warnings: {len(report['warnings'])}")
        out.extend("  [WARN] " + w for w in report["warnings"])
        out.append("Result: " + ("PASSED" if report["passed"] else "FAILED"))
        return "\n".join(out)

    # ---- updates -----------------------------------------------------
    def add_station(self, name, lines=None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Station name must be a non-empty string")
        st = self.get_station(name)
        if st is None:
            st = {"name": name, "lines": []}
            self.data["stations"].append(st)
        for ln in lines or []:
            if ln not in st.setdefault("lines", []):
                st["lines"].append(ln)
        return st

    def add_line(self, line_name, station_sequence, distances):
        """Add a new line given its station sequence and inter-station distances."""
        if not line_name:
            raise ValueError("Line name must not be empty")
        if len(station_sequence) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance: {d!r}")
        for name in station_sequence:
            self.add_station(name, [line_name])
        for a, b, d in zip(station_sequence, station_sequence[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})

    def update_station(self, name, new_name=None, lines=None):
        st = self.get_station(name)
        if st is None:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self.get_station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
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
        updated = False
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated = True
        return updated

    def save(self, path=None):
        with open(path or self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
