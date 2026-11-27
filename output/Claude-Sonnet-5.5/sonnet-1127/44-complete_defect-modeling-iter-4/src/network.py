"""SubwayNetwork and DataManager."""
import json

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


class SubwayNetwork:
    def __init__(self, data):
        self.data = data
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.lines = {}
        self._build()

    def _number(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
            self.graph.add_node(n)
        return self.station_to_number[name]

    def _build(self):
        for s in self.data.get("stations", []):
            self._number(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        seen = set()
        for c in self.data.get("connections", []):
            a, b = self._number(c["source"]), self._number(c["dest"])
            key = (min(a, b), max(a, b), c.get("line"))
            if key in seen or a == b:
                continue
            seen.add(key)
            self.graph.add_edge(Edge(a, b, c["distance"], c.get("line")))
            for nm in (c["source"], c["dest"]):
                ls = self.graph.station_lines.setdefault(nm, [])
                if c.get("line") not in ls:
                    ls.append(c.get("line"))
            seq = self.lines.setdefault(c.get("line"), [])
            for nm in (c["source"], c["dest"]):
                if nm not in seq:
                    seq.append(nm)

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1


REPRESENTATIVE = {
    "1号线": "天安门东", "2号线": "雍和宫", "4号线": "西单", "5号线": "东单",
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.network = SubwayNetwork(self.data)

    def rebuild(self):
        self.network = SubwayNetwork(self.data)

    def save(self, path=None):
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)

    def check_data(self):
        """Return list of issue strings (empty if data is fine)."""
        issues = []
        names = set()
        for s in self.data.get("stations", []):
            if not s.get("name"):
                issues.append("Station without name")
            if s["name"] in names:
                issues.append("Duplicate station: %s" % s["name"])
            names.add(s["name"])
            if not s.get("lines"):
                issues.append("Station without lines: %s" % s["name"])
        if not names:
            issues.append("No station data")
        linked = set()
        for c in self.data.get("connections", []):
            for k in ("source", "dest"):
                if c[k] not in names:
                    issues.append("Connection references unknown station: %s" % c[k])
                linked.add(c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                issues.append("Invalid distance %s-%s: %r" % (c["source"], c["dest"], d))
            elif d > 20000:
                issues.append("Suspicious distance %s-%s: %s" % (c["source"], c["dest"], d))
        for n in sorted(names - linked):
            issues.append("Station without connections: %s" % n)
        return issues

    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                st = {"name": n, "lines": [line_name]}
                self.data["stations"].append(st)
                known[n] = st
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.rebuild()

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
                self.rebuild()
                return True
        return False

    def update_distance(self, a, b, distance):
        if distance <= 0:
            raise ValueError("distance must be positive")
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if found:
            self.rebuild()
        return found
