"""Subway data management: integrity checks and data updates."""

import copy
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, save_subway_data

MAIN_LINES = {
    "Line 1": ["Line 1", "1号线", "地铁1号线", "1号线八通线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线", "4号线大兴线"],
    "Line 5": ["Line 5", "5号线"],
    "Line 6": ["Line 6", "6号线"],
    "Line 8": ["Line 8", "8号线"],
    "Line 10": ["Line 10", "10号线"],
    "Line 13": ["Line 13", "13号线"],
    "Line 14": ["Line 14", "14号线"],
    "Line 15": ["Line 15", "15号线"],
    "Changping Line": ["Changping Line", "昌平线"],
    "Yizhuang Line": ["Yizhuang Line", "亦庄线"],
    "Fangshan Line": ["Fangshan Line", "房山线"],
    "Airport Line": ["Airport Line", "Capital Airport Express", "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "西单", "Wangfujing", "王府井"],
    "Line 2": ["Xizhimen", "西直门", "Dongzhimen", "东直门"],
    "Line 4": ["Xidan", "西单", "Zhongguancun", "中关村"],
    "Line 5": ["Dongdan", "东单", "Yonghegong", "雍和宫"],
    "Line 10": ["Guomao", "国贸", "Sanyuanqiao", "三元桥"],
    "Line 13": ["Xizhimen", "西直门", "Huilongguan", "回龙观"],
}


def _norm(s):
    return " ".join(str(s).split()).lower()


class SubwayDataManager:
    def __init__(self, data):
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ---------------- integrity check ----------------
    def check_integrity(self):
        errors, warnings = [], []
        stations = self.data["stations"]
        conns = self.data["connections"]
        names = []
        station_lines = {}
        for i, st in enumerate(stations):
            name = st.get("name") if isinstance(st, dict) else None
            if not name:
                errors.append(f"Station #{i} has no name")
                continue
            if name in station_lines:
                warnings.append(f"Duplicate station entry: '{name}'")
            names.append(name)
            lines = st.get("lines") or []
            if not lines:
                warnings.append(f"Station '{name}' has no line information")
            station_lines[name] = set(lines)

        adj = defaultdict(set)
        seen = {}
        for i, c in enumerate(conns):
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            if not s or not d:
                errors.append(f"Connection #{i} is missing source/dest")
                continue
            for n in (s, d):
                if n not in station_lines:
                    errors.append(f"Connection #{i} references unknown station '{n}'")
            if s == d:
                errors.append(f"Connection #{i} is a self-loop at '{s}'")
            if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
                errors.append(f"Connection {s} - {d} has invalid distance {dist!r}")
            elif dist < 100:
                warnings.append(f"Connection {s} - {d} distance {dist} m is suspiciously short")
            elif dist > 40000:
                warnings.append(f"Connection {s} - {d} distance {dist} m is suspiciously long")
            if line:
                for n in (s, d):
                    if n in station_lines and station_lines[n] and line not in station_lines[n]:
                        warnings.append(f"Station '{n}' is not listed on line '{line}'")
            else:
                warnings.append(f"Connection {s} - {d} has no line")
            key = (frozenset((s, d)), line)
            if key in seen and seen[key] != dist:
                warnings.append(f"Inconsistent distances for {s} - {d} on {line}: "
                                f"{seen[key]} vs {dist}")
            seen[key] = dist
            adj[s].add(d)
            adj[d].add(s)

        isolated = [n for n in station_lines if n not in adj]
        for n in isolated:
            warnings.append(f"Station '{n}' has no connections")

        components = 0
        visited = set()
        for n in station_lines:
            if n in visited or n not in adj:
                continue
            components += 1
            dq = deque([n])
            visited.add(n)
            while dq:
                x = dq.popleft()
                for y in adj[x]:
                    if y not in visited:
                        visited.add(y)
                        dq.append(y)
        if components > 1:
            warnings.append(f"Network is split into {components} disconnected components")

        all_lines = set()
        for ls in station_lines.values():
            all_lines.update(ls)
        for c in conns:
            if c.get("line"):
                all_lines.add(c["line"])
        norm_lines = {_norm(l) for l in all_lines}
        missing_lines = []
        for main, aliases in MAIN_LINES.items():
            if not any(_norm(a) in norm_lines for a in aliases):
                missing_lines.append(main)
        if missing_lines:
            warnings.append("Main lines not found in data: " + ", ".join(missing_lines))

        norm_names = {_norm(n) for n in station_lines}
        for line, reps in REPRESENTATIVE_STATIONS.items():
            if not any(_norm(r) in norm_names for r in reps):
                warnings.append(f"No representative station of {line} found "
                                f"(checked: {', '.join(reps)})")

        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "stations": len(station_lines),
                "connections": len(conns),
                "lines": len(all_lines),
                "components": components,
            },
        }

    def format_report(self, report=None):
        report = report or self.check_integrity()
        out = ["Data integrity check report", "=" * 40]
        st = report["stats"]
        out.append(f"Stations: {st['stations']}, Connections: {st['connections']}, "
                   f"Lines: {st['lines']}, Components: {st['components']}")
        out.append(f"Errors: {len(report['errors'])}")
        out += ["  [ERROR] " + e for e in report["errors"]]
        out.append(f"Warnings: {len(report['warnings'])}")
        out += ["  [WARN] " + w for w in report["warnings"]]
        out.append("Result: " + ("PASSED" if report["ok"] else "FAILED"))
        return "\n".join(out)

    # ---------------- update mechanisms ----------------
    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_line(self, line_name, station_names, distances):
        """Add a new line: stations in order and distances between consecutive ones."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be number of stations - 1")
        if any(d <= 0 for d in distances):
            raise ValueError("Distances must be positive")
        for name in station_names:
            st = self._station(name)
            if st is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in st.setdefault("lines", []):
                st["lines"].append(line_name)
        for i, d in enumerate(distances):
            self.data["connections"].append({
                "source": station_names[i], "dest": station_names[i + 1],
                "distance": d, "line": line_name})

    def modify_station(self, name, new_name=None, lines=None):
        st = self._station(name)
        if st is None:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self._station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)

    def update_distance(self, source, dest, distance, line=None):
        if distance <= 0:
            raise ValueError("Distance must be positive")
        updated = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and \
                    (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return updated

    def snapshot(self):
        return copy.deepcopy(self.data)

    def save(self, path=DATA_FILE_PATH):
        save_subway_data(self.data, path)
