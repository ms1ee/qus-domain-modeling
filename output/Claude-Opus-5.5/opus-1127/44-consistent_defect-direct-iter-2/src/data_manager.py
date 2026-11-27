"""Data management: integrity checks and update operations."""

import json

from data_loader import DATA_FILE_PATH, load_subway_data

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]
MAX_REASONABLE_DISTANCE = 50000


def _norm(s):
    return "".join(str(s).lower().split())


class SubwayDataManager:
    """Manage stations, connections and lines of the subway dataset."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ---- lookup helpers ----
    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def station_names(self):
        return [s.get("name") for s in self.data["stations"]]

    def lines(self):
        result = []
        for st in self.data["stations"]:
            for l in st.get("lines", []):
                if l not in result:
                    result.append(l)
        for c in self.data["connections"]:
            l = c.get("line")
            if l and l not in result:
                result.append(l)
        return result

    def line_stations(self, line):
        """Station sequence of a line (ordered following connections)."""
        conns = [c for c in self.data["connections"] if c.get("line") == line]
        if not conns:
            return []
        adj = {}
        for c in conns:
            adj.setdefault(c["source"], []).append(c["dest"])
            adj.setdefault(c["dest"], []).append(c["source"])
        start = next((n for n, v in adj.items() if len(v) == 1), conns[0]["source"])
        seq, seen, cur = [], set(), start
        while cur is not None and cur not in seen:
            seq.append(cur)
            seen.add(cur)
            cur = next((n for n in adj[cur] if n not in seen), None)
        return seq

    def transfer_stations(self):
        return [s["name"] for s in self.data["stations"] if len(s.get("lines", [])) > 1]

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        if len(stations) < 2 or len(distances) != len(stations) - 1:
            raise ValueError("A line needs >= 2 stations and len(stations)-1 distances")
        for d in distances:
            if not isinstance(d, int) or d <= 0:
                raise ValueError("Distances must be positive integers (meters)")
        for name in stations:
            st = self._station(name)
            if st is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in st.setdefault("lines", []):
                st["lines"].append(line_name)
        for i, d in enumerate(distances):
            self.data["connections"].append(
                {"source": stations[i], "dest": stations[i + 1], "distance": d, "line": line_name})

    def update_station(self, old_name, new_name=None, lines=None):
        st = self._station(old_name)
        if st is None:
            raise KeyError("Station '%s' does not exist" % old_name)
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != old_name:
            if self._station(new_name) is not None:
                raise ValueError("Station '%s' already exists" % new_name)
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == old_name:
                    c["source"] = new_name
                if c.get("dest") == old_name:
                    c["dest"] = new_name

    def update_distance(self, a, b, distance, line=None):
        if not isinstance(distance, int) or distance <= 0:
            raise ValueError("Distance must be a positive integer (meters)")
        updated = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {a, b} and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError("No connection between '%s' and '%s'" % (a, b))
        return updated

    def save(self, path=None):
        with open(path or self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)

    # ---- integrity ----
    def check_integrity(self):
        errors, warnings = [], []
        names = set()
        for st in self.data["stations"]:
            n = st.get("name")
            if not n:
                errors.append("Station entry without name: %r" % (st,))
                continue
            if n in names:
                warnings.append("Duplicate station name: %s" % n)
            names.add(n)
            if not st.get("lines"):
                warnings.append("Station '%s' has no line affiliation" % n)
        connected = set()
        seen_pairs = set()
        for c in self.data["connections"]:
            s, d, dist = c.get("source"), c.get("dest"), c.get("distance")
            for end in (s, d):
                if end not in names:
                    errors.append("Connection references unknown station '%s'" % end)
            if s == d:
                errors.append("Self-loop connection at '%s'" % s)
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                errors.append("Invalid distance %r between '%s' and '%s'" % (dist, s, d))
            elif dist > MAX_REASONABLE_DISTANCE:
                warnings.append("Unusually large distance %s m between '%s' and '%s'" % (dist, s, d))
            key = (frozenset((s, d)), c.get("line"))
            if key in seen_pairs:
                warnings.append("Duplicate connection '%s'-'%s' on %s" % (s, d, c.get("line")))
            seen_pairs.add(key)
            connected.add(s)
            connected.add(d)
        for n in names - connected:
            warnings.append("Station '%s' has no connections" % n)
        known = {_norm(l) for l in self.lines()}
        for line in MAIN_LINES:
            if _norm(line) not in known:
                warnings.append("Main line '%s' not found in data" % line)
        return {
            "errors": errors,
            "warnings": warnings,
            "station_count": len(names),
            "connection_count": len(self.data["connections"]),
            "line_count": len(self.lines()),
        }
