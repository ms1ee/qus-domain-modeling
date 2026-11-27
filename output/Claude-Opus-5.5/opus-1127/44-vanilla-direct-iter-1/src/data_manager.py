"""Data management: integrity checks and update operations."""

import copy
import re

from data_loader import DATA_FILE_PATH, save_subway_data

MAIN_LINES = {
    "Line 1": ["line 1", "1号线", "line1"],
    "Line 2": ["line 2", "2号线", "line2"],
    "Line 4": ["line 4", "4号线", "line4", "4号线大兴线"],
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
    "Airport Line": ["airport line", "airport express", "capital airport express",
                     "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = [
    ["Xidan", "西单"], ["Guomao", "国贸"], ["Tian'anmen East", "天安门东"],
    ["Xizhimen", "西直门"], ["Dongzhimen", "东直门"], ["Jianguomen", "建国门"],
    ["Zhongguancun", "中关村"], ["Xuanwumen", "宣武门"],
    ["Dongdan", "东单"], ["Tiantongyuan", "天通苑"],
    ["Chegongzhuang", "车公庄"], ["Dongsi", "东四"],
    ["Gulou Dajie", "鼓楼大街"], ["Sanyuanqiao", "三元桥"],
    ["Wudaokou", "五道口"], ["Xi'erqi", "西二旗"], ["Wangjing", "望京"],
    ["Songjiazhuang", "宋家庄"], ["Guogongzhuang", "郭公庄"],
]

MIN_REASONABLE_DISTANCE = 100      # meters
MAX_REASONABLE_DISTANCE = 15000    # meters


def _loose(s):
    s = str(s).strip().lower()
    for suffix in (" station", "站"):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
    return re.sub(r"[\s'’\-]", "", s)


class SubwayDataManager:
    """Wraps raw subway data with check and update operations."""

    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ---- lookup helpers ---------------------------------------------
    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def _ensure_station(self, name, line):
        st = self._station(name)
        if st is None:
            st = {"name": name, "lines": []}
            self.data["stations"].append(st)
        st.setdefault("lines", [])
        if line and line not in st["lines"]:
            st["lines"].append(line)
        return st

    def line_names(self):
        names = []
        for st in self.data["stations"]:
            for ln in st.get("lines", []) or []:
                if ln not in names:
                    names.append(ln)
        for c in self.data["connections"]:
            if c.get("line") and c["line"] not in names:
                names.append(c["line"])
        return names

    def get_line_stations(self, line):
        """Ordered station sequence of a line, derived from connections."""
        adj = {}
        for c in self.data["connections"]:
            if c.get("line") == line:
                adj.setdefault(c["source"], []).append(c["dest"])
                adj.setdefault(c["dest"], []).append(c["source"])
        if not adj:
            return []
        start = next((s for s, n in adj.items() if len(set(n)) == 1), next(iter(adj)))
        order, seen, cur = [start], {start}, start
        while True:
            nxt = next((n for n in adj[cur] if n not in seen), None)
            if nxt is None:
                break
            order.append(nxt)
            seen.add(nxt)
            cur = nxt
        for s in adj:  # remaining stations of branched/loop lines
            if s not in seen:
                order.append(s)
                seen.add(s)
        return order

    def get_transfer_stations(self):
        return sorted(st["name"] for st in self.data["stations"]
                      if len(st.get("lines", []) or []) > 1)

    # ---- integrity check --------------------------------------------
    def check_integrity(self):
        errors, warnings = [], []
        stations = self.data["stations"]
        names = set()
        for i, st in enumerate(stations):
            name = st.get("name")
            if not name:
                errors.append("Station #%d has no name" % i)
                continue
            if name in names:
                errors.append("Duplicate station name: %s" % name)
            names.add(name)
            if not st.get("lines"):
                warnings.append("Station '%s' has no line information" % name)

        # Coverage
        loose_lines = {_loose(l) for l in self.line_names()}
        missing_lines = []
        for canonical, aliases in MAIN_LINES.items():
            if not any(_loose(a) in loose_lines for a in aliases + [canonical]):
                missing_lines.append(canonical)
        for ml in missing_lines:
            warnings.append("Main line not found in data: %s" % ml)
        loose_names = {_loose(n) for n in names}
        found_rep = 0
        missing_rep = []
        for candidates in REPRESENTATIVE_STATIONS:
            if any(_loose(c) in loose_names for c in candidates):
                found_rep += 1
            else:
                missing_rep.append(candidates[0])
        if missing_rep:
            warnings.append("Representative stations not found: %s" % ", ".join(missing_rep))

        # Connections
        seen_pairs = {}
        connected = set()
        adj = {}
        bad_distance = 0
        for i, c in enumerate(self.data["connections"]):
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            if s is None or d is None:
                errors.append("Connection #%d missing source/dest" % i)
                continue
            if s not in names:
                errors.append("Connection #%d references unknown station '%s'" % (i, s))
            if d not in names:
                errors.append("Connection #%d references unknown station '%s'" % (i, d))
            if s == d:
                errors.append("Connection #%d is a self loop at '%s'" % (i, s))
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                errors.append("Connection %s - %s has invalid distance %r" % (s, d, dist))
                bad_distance += 1
            elif not (MIN_REASONABLE_DISTANCE <= dist <= MAX_REASONABLE_DISTANCE):
                warnings.append("Connection %s - %s has unusual distance %s m" % (s, d, dist))
            if not line:
                warnings.append("Connection %s - %s has no line" % (s, d))
            else:
                for n in (s, d):
                    st = self._station(n)
                    if st is not None and line not in (st.get("lines") or []):
                        warnings.append("Station '%s' is on connection of '%s' but does not "
                                        "list that line" % (n, line))
            key = (frozenset((s, d)), line)
            if key in seen_pairs and seen_pairs[key] != dist:
                errors.append("Inconsistent distances for %s - %s on %s: %s vs %s"
                              % (s, d, line, seen_pairs[key], dist))
            seen_pairs[key] = dist
            connected.update((s, d))
            adj.setdefault(s, set()).add(d)
            adj.setdefault(d, set()).add(s)

        isolated = sorted(names - connected)
        for n in isolated:
            warnings.append("Station '%s' has no connections" % n)
        components = 0
        visited = set()
        for n in adj:
            if n in visited:
                continue
            components += 1
            stack = [n]
            visited.add(n)
            while stack:
                v = stack.pop()
                for w in adj[v]:
                    if w not in visited:
                        visited.add(w)
                        stack.append(w)
        if components > 1:
            warnings.append("Network is split into %d disconnected components" % components)

        return {
            "ok": not errors,
            "station_count": len(names),
            "connection_count": len(self.data["connections"]),
            "line_count": len(self.line_names()),
            "transfer_station_count": len(self.get_transfer_stations()),
            "representative_coverage": "%d/%d" % (found_rep, len(REPRESENTATIVE_STATIONS)),
            "missing_main_lines": missing_lines,
            "components": components,
            "errors": errors,
            "warnings": warnings,
        }

    # ---- updates ----------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line given station sequence and inter-station distances."""
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Need exactly len(stations) - 1 distances")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in stations:
            self._ensure_station(name, line_name)
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name})

    def modify_station(self, name, new_name=None, lines=None):
        st = self._station(name)
        if st is None:
            raise KeyError("Station '%s' does not exist" % name)
        if new_name and new_name != name:
            if self._station(new_name) is not None:
                raise ValueError("Station '%s' already exists" % new_name)
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)

    def update_distance(self, source, dest, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        updated = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and \
                    (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                updated += 1
        if not updated:
            raise KeyError("No connection between '%s' and '%s'" % (source, dest))
        return updated

    def save(self, path=DATA_FILE_PATH):
        save_subway_data(self.data, path)


def format_integrity_report(report):
    out = ["Data integrity check",
           "Stations: %d" % report["station_count"],
           "Connections: %d" % report["connection_count"],
           "Lines: %d" % report["line_count"],
           "Transfer stations: %d" % report["transfer_station_count"],
           "Representative station coverage: %s" % report["representative_coverage"],
           "Connected components: %d" % report["components"]]
    if report["errors"]:
        out.append("Errors (%d):" % len(report["errors"]))
        out.extend("  - " + e for e in report["errors"])
    if report["warnings"]:
        out.append("Warnings (%d):" % len(report["warnings"]))
        out.extend("  - " + w for w in report["warnings"])
    out.append("Result: %s" % ("PASSED" if report["ok"] else "FAILED"))
    return "\n".join(out)
