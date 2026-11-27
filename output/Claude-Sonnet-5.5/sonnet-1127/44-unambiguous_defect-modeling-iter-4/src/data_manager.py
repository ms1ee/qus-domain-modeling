"""Data management and integrity checking."""
import json

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": "Tiananmen East", "Line 2": "Xizhimen", "Line 4": "Xidan",
    "Line 5": "Dongdan", "Line 10": "Guomao", "Line 13": "Wudaokou",
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = Graph()
        self.build()

    def build(self):
        g = Graph()
        names = []
        seen = set()
        for s in self.data.get("stations", []):
            if s["name"] not in seen:
                seen.add(s["name"])
                names.append(s["name"])
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in seen:
                    seen.add(n)
                    names.append(n)
        for i, n in enumerate(names):
            g.add_station(n, i)
        for s in self.data.get("stations", []):
            g.set_station_lines(s["name"], s.get("lines", []))
        derived = {}
        for c in self.data.get("connections", []):
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
            for n in (c["source"], c["dest"]):
                derived.setdefault(n, [])
                if c["line"] not in derived[n]:
                    derived[n].append(c["line"])
        for n in names:
            if n not in g.station_lines:
                g.set_station_lines(n, derived.get(n, []))
        self.graph = g

    def station_names(self):
        return list(self.graph.station_to_number)

    def lines(self):
        result = {}
        for n, ls in self.graph.station_lines.items():
            for l in ls:
                result.setdefault(l, []).append(n)
        return result

    def save(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters."""
        if len(distances) != len(stations) - 1:
            raise ValueError("need len(stations)-1 distances")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name})
        self.build()

    def update_station(self, name, new_name=None, lines=None):
        for s in self.data["stations"]:
            if s["name"] == name:
                if lines is not None:
                    s["lines"] = list(lines)
                if new_name:
                    s["name"] = new_name
                    for c in self.data["connections"]:
                        if c["source"] == name:
                            c["source"] = new_name
                        if c["dest"] == name:
                            c["dest"] = new_name
                self.build()
                return True
        return False

    def update_distance(self, a, b, distance, line=None):
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = int(distance)
                found = True
        if found:
            self.build()
        return found


class DataIntegrityChecker:
    def __init__(self, manager):
        self.manager = manager
        self.station_coverage_valid = False
        self.connection_valid = False
        self.distance_valid = False

    def run(self):
        msgs = []
        g = self.manager.graph
        lines = self.manager.lines()
        missing = [f"{l}:{s}" for l, s in REPRESENTATIVE.items() if s not in g.station_to_number]
        self.station_coverage_valid = not missing and len(g.station_to_number) > 0
        if missing:
            msgs.append("Missing representative stations: " + ", ".join(missing))
        msgs.append("Stations: %d, lines: %d" % (len(g.station_to_number), len(lines)))
        bad = []
        for c in self.manager.data.get("connections", []):
            if c["source"] not in g.station_to_number or c["dest"] not in g.station_to_number:
                bad.append(c)
        isolated = [n for n, i in g.station_to_number.items() if not g.neighbors(i)]
        self.connection_valid = not bad and not isolated
        if isolated:
            msgs.append("Isolated stations: " + ", ".join(isolated[:10]))
        baddist = [c for c in self.manager.data.get("connections", [])
                   if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0
                   or c["distance"] > 20000]
        self.distance_valid = not baddist
        if baddist:
            msgs.append("%d connections have suspicious distances" % len(baddist))
        ok = self.station_coverage_valid and self.connection_valid and self.distance_valid
        msgs.append("Data check " + ("PASSED" if ok else "FAILED"))
        return ok, msgs
