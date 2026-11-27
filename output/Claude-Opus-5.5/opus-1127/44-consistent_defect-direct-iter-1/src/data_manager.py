"""Data integrity checks and update mechanisms."""

import json

from data_loader import DATA_FILE_PATH

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

MAX_REASONABLE_DISTANCE = 30000


class SubwayDataManager:
    def __init__(self, data):
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_line(self, line_name, station_names, distances):
        """Add a line: station_names in order, distances between consecutive stations."""
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have len(station_names) - 1 entries")
        for name in station_names:
            st = self._station(name)
            if st is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in st.setdefault("lines", []):
                st["lines"].append(line_name)
        for i, d in enumerate(distances):
            if d <= 0:
                raise ValueError("distance must be positive")
            a, b = station_names[i], station_names[i + 1]
            self.data["connections"].append({"source": a, "dest": b, "distance": int(d), "line": line_name})
            self.data["connections"].append({"source": b, "dest": a, "distance": int(d), "line": line_name})

    def modify_station(self, old_name, new_name=None, lines=None):
        st = self._station(old_name)
        if st is None:
            raise KeyError("Station '%s' does not exist" % old_name)
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != old_name:
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == old_name:
                    c["source"] = new_name
                if c.get("dest") == old_name:
                    c["dest"] = new_name

    def update_distance(self, source, dest, distance, line=None):
        if distance <= 0:
            raise ValueError("distance must be positive")
        count = 0
        for c in self.data["connections"]:
            if c.get("source") == source and c.get("dest") == dest and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                count += 1
        return count

    def save(self, path=DATA_FILE_PATH):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def check_integrity(self):
        """Return (ok, errors, warnings)."""
        errors, warnings = [], []
        names = set()
        all_lines = set()
        for st in self.data["stations"]:
            name = st.get("name")
            if not name:
                errors.append("Station entry without a name: %r" % (st,))
                continue
            if name in names:
                warnings.append("Duplicate station name: %s" % name)
            names.add(name)
            lines = st.get("lines") or []
            if not lines:
                warnings.append("Station '%s' has no line information" % name)
            all_lines.update(lines)
        for line in MAIN_LINES:
            if line not in all_lines:
                warnings.append("Main line '%s' not covered by station data" % line)
        connected = set()
        pairs = set()
        for c in self.data["connections"]:
            s, d = c.get("source"), c.get("dest")
            if s not in names:
                errors.append("Connection source '%s' is not a known station" % s)
            if d not in names:
                errors.append("Connection destination '%s' is not a known station" % d)
            if s == d:
                errors.append("Self-loop connection at '%s'" % s)
            dist = c.get("distance")
            if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
                errors.append("Invalid distance %r for %s -> %s" % (dist, s, d))
            elif dist > MAX_REASONABLE_DISTANCE:
                warnings.append("Unusually large distance %r m for %s -> %s" % (dist, s, d))
            connected.add(s)
            connected.add(d)
            pairs.add((s, d, c.get("line")))
        for s, d, line in pairs:
            if (d, s, line) not in pairs:
                warnings.append("Connection %s -> %s (%s) has no reverse direction" % (s, d, line))
        for name in names:
            if name not in connected:
                warnings.append("Station '%s' has no connections" % name)
        return (not errors), errors, warnings
