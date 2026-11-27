"""Data integrity checks and update mechanisms for subway data."""
import json

from data_loader import DATA_FILE_PATH
from subway_system import MAIN_LINES


class SubwayDataManager:
    def __init__(self, data):
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    def _station(self, name):
        for st in self.data["stations"]:
            if st["name"] == name:
                return st
        return None

    # ---- updates ----
    def add_station(self, name, lines):
        st = self._station(name)
        if st is None:
            self.data["stations"].append({"name": name, "lines": list(lines)})
        else:
            for l in lines:
                if l not in st["lines"]:
                    st["lines"].append(l)

    def add_line(self, line_name, stations, distances, bidirectional=True):
        """Add a line given ordered station names and distances between neighbours."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have exactly len(stations) - 1 entries")
        for s in stations:
            self.add_station(s, [line_name])
        for i, d in enumerate(distances):
            if d <= 0:
                raise ValueError("distance must be positive")
            self.data["connections"].append({"source": stations[i], "dest": stations[i + 1],
                                             "distance": int(d), "line": line_name})
            if bidirectional:
                self.data["connections"].append({"source": stations[i + 1], "dest": stations[i],
                                                 "distance": int(d), "line": line_name})

    def update_station(self, old_name, new_name=None, lines=None):
        st = self._station(old_name)
        if st is None:
            raise KeyError(f"Station '{old_name}' does not exist")
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != old_name:
            st["name"] = new_name
            for c in self.data["connections"]:
                if c["source"] == old_name:
                    c["source"] = new_name
                if c["dest"] == old_name:
                    c["dest"] = new_name

    def update_distance(self, source, dest, distance, line=None, both_directions=True):
        if distance <= 0:
            raise ValueError("distance must be positive")
        updated = 0
        for c in self.data["connections"]:
            if line is not None and c.get("line") != line:
                continue
            if (c["source"] == source and c["dest"] == dest) or \
               (both_directions and c["source"] == dest and c["dest"] == source):
                c["distance"] = int(distance)
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return updated

    def save(self, path=DATA_FILE_PATH):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ---- integrity ----
    def check_integrity(self):
        errors, warnings = [], []
        names = set()
        all_lines = set()
        for st in self.data["stations"]:
            name = st.get("name")
            if not name:
                errors.append("Station with empty name")
                continue
            if name in names:
                warnings.append(f"Duplicate station '{name}'")
            names.add(name)
            if not st.get("lines"):
                warnings.append(f"Station '{name}' has no line information")
            all_lines.update(st.get("lines", []))
        for line in MAIN_LINES:
            if line not in all_lines:
                warnings.append(f"Main line '{line}' not covered by station data")
        pairs = set()
        connected = set()
        for i, c in enumerate(self.data["connections"]):
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            if s not in names:
                errors.append(f"Connection #{i}: unknown source station '{s}'")
            if d not in names:
                errors.append(f"Connection #{i}: unknown destination station '{d}'")
            if s == d:
                errors.append(f"Connection #{i}: self-loop at '{s}'")
            if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
                errors.append(f"Connection #{i}: invalid distance {dist!r}")
            elif dist > 30000:
                warnings.append(f"Connection #{i}: unusually long distance {dist} m ({s} -> {d})")
            for n in (s, d):
                st = self._station(n)
                if st is not None and line and line not in st.get("lines", []):
                    warnings.append(f"Connection #{i}: station '{n}' not listed on '{line}'")
            pairs.add((s, d, line))
            connected.update([s, d])
        for s, d, line in pairs:
            if (d, s, line) not in pairs:
                warnings.append(f"Connection {s} -> {d} ({line}) has no reverse direction")
        for n in names - connected:
            warnings.append(f"Station '{n}' has no connections")
        return {"ok": not errors, "errors": errors, "warnings": warnings,
                "station_count": len(names), "connection_count": len(self.data["connections"]),
                "line_count": len(all_lines)}
