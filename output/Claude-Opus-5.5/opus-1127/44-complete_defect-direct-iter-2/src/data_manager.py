"""Data management: integrity checks and update mechanisms."""

import re

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data, normalize_station_name

MAIN_LINES = {
    "Line 1": ["line 1", "1号线", "1号线八通线"],
    "Line 2": ["line 2", "2号线"],
    "Line 4": ["line 4", "4号线", "4号线大兴线"],
    "Line 5": ["line 5", "5号线"],
    "Line 6": ["line 6", "6号线"],
    "Line 8": ["line 8", "8号线"],
    "Line 10": ["line 10", "10号线"],
    "Line 13": ["line 13", "13号线"],
    "Line 14": ["line 14", "14号线"],
    "Line 15": ["line 15", "15号线"],
    "Changping Line": ["changping line", "昌平线"],
    "Yizhuang Line": ["yizhuang line", "亦庄线"],
    "Fangshan Line": ["fangshan line", "房山线"],
    "Airport Line": ["airport line", "airport express", "capital airport line", "首都机场线", "机场线"],
}

# Representative stations (English / Chinese aliases) of main lines.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "西单"],
    "Line 2": ["Dongzhimen", "东直门"],
    "Line 4": ["Xizhimen", "西直门"],
    "Line 5": ["Dongdan", "东单"],
    "Line 10": ["Guomao", "国贸"],
    "Line 13": ["Xi'erqi", "Xierqi", "西二旗"],
}

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 30000


def _loose(text):
    return re.sub(r"[\s'’\-]", "", str(text)).lower()


class DataManager:
    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ----- lookup helpers -----
    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    # ----- integrity check -----
    def check_integrity(self):
        errors, warnings = [], []
        names = {}
        for i, st in enumerate(self.data["stations"]):
            name = st.get("name") if isinstance(st, dict) else None
            if not name or not isinstance(name, str):
                errors.append("Station #%d has no valid name" % i)
                continue
            if name in names:
                warnings.append("Duplicate station entry: %s" % name)
            names[name] = list(st.get("lines", []) or [])
            if not names[name]:
                warnings.append("Station '%s' has no line affiliation" % name)

        all_lines = set()
        for lines in names.values():
            all_lines.update(lines)
        adjacency = {n: set() for n in names}
        seen = set()
        for i, c in enumerate(self.data["connections"]):
            if not isinstance(c, dict):
                errors.append("Connection #%d is malformed" % i)
                continue
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = "Connection #%d (%s - %s)" % (i, s, d)
            if s not in names:
                errors.append("%s: unknown source station '%s'" % (label, s))
            if d not in names:
                errors.append("%s: unknown destination station '%s'" % (label, d))
            if s == d:
                errors.append("%s: self loop" % label)
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                errors.append("%s: invalid distance %r" % (label, dist))
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append("%s: suspicious distance %s meters" % (label, dist))
            if not line:
                errors.append("%s: missing line" % label)
            else:
                all_lines.add(line)
                for n in (s, d):
                    if n in names and line not in names[n]:
                        warnings.append("%s: station '%s' not listed on line '%s'" % (label, n, line))
            key = (frozenset((s, d)), line)
            if key in seen:
                warnings.append("%s: duplicate connection on line '%s'" % (label, line))
            seen.add(key)
            if s in adjacency and d in adjacency:
                adjacency[s].add(d)
                adjacency[d].add(s)

        isolated = [n for n, adj in adjacency.items() if not adj]
        for n in isolated:
            warnings.append("Station '%s' has no connections" % n)

        # connectivity
        components = 0
        visited = set()
        for n in adjacency:
            if n in visited or not adjacency[n]:
                continue
            components += 1
            stack = [n]
            visited.add(n)
            while stack:
                v = stack.pop()
                for w in adjacency[v]:
                    if w not in visited:
                        visited.add(w)
                        stack.append(w)
        if components > 1:
            warnings.append("Network is split into %d disconnected components" % components)

        # coverage of main lines
        loose_lines = {_loose(l) for l in all_lines}
        missing_lines = []
        for main, aliases in MAIN_LINES.items():
            if not any(_loose(a) in loose_lines for a in aliases + [main]):
                missing_lines.append(main)
        for m in missing_lines:
            warnings.append("Main line not found in data: %s" % m)
        loose_names = {_loose(n) for n in names}
        for line, aliases in REPRESENTATIVE_STATIONS.items():
            if not any(_loose(a) in loose_names for a in aliases):
                warnings.append("Representative station of %s not found (%s)" % (line, "/".join(aliases)))

        return {
            "ok": not errors,
            "station_count": len(names),
            "connection_count": len(self.data["connections"]),
            "line_count": len(all_lines),
            "errors": errors,
            "warnings": warnings,
        }

    # ----- updates -----
    def add_line(self, line_name, station_sequence, distances):
        if not line_name:
            raise ValueError("line name required")
        if len(station_sequence) < 2 or len(distances) != len(station_sequence) - 1:
            raise ValueError("need N stations and N-1 distances")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("distances must be positive numbers")
        for name in station_sequence:
            name = normalize_station_name(name)
            st = self._station(name)
            if st is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in st.setdefault("lines", []):
                st["lines"].append(line_name)
        for i, d in enumerate(distances):
            self.data["connections"].append({
                "source": normalize_station_name(station_sequence[i]),
                "dest": normalize_station_name(station_sequence[i + 1]),
                "distance": d,
                "line": line_name,
            })

    def modify_station(self, name, new_name=None, lines=None):
        st = self._station(name)
        if st is None:
            raise KeyError("Station '%s' does not exist" % name)
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != name:
            new_name = normalize_station_name(new_name)
            if self._station(new_name) is not None:
                raise ValueError("Station '%s' already exists" % new_name)
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name

    def update_distance(self, a, b, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("distance must be a positive number")
        count = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {a, b} and (line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError("No connection between '%s' and '%s'" % (a, b))
        return count

    def save(self, path=None):
        save_subway_data(self.data, path or self.path)


def format_report(report):
    out = ["Data integrity check",
           "Stations: %d, Connections: %d, Lines: %d" % (
               report["station_count"], report["connection_count"], report["line_count"])]
    out.append("Errors: %d" % len(report["errors"]))
    out.extend("  [ERROR] " + e for e in report["errors"])
    out.append("Warnings: %d" % len(report["warnings"]))
    out.extend("  [WARN] " + w for w in report["warnings"])
    out.append("Result: %s" % ("PASSED" if report["ok"] else "FAILED"))
    return "\n".join(out)
