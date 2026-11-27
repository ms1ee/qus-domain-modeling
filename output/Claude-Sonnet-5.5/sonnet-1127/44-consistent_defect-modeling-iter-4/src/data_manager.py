"""Data management: loading, graph building, integrity check, updates."""
import json

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": "苹果园", "Line 2": "西直门", "Line 4": "安河桥北", "Line 5": "宋家庄",
    "Line 10": "知春路", "Line 13": "西二旗",
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.build()

    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        names = [s["name"] for s in self.data.get("stations", [])]
        for c in self.data.get("connections", []):
            names.extend([c["source"], c["dest"]])
        for n in names:
            if n not in self.station_to_number:
                num = len(self.station_to_number)
                self.station_to_number[n] = num
                self.number_to_station[num] = n
                self.graph.add_node(num)
        for s in self.data.get("stations", []):
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            self.graph.add_edge(Edge(self.station_to_number[c["source"]],
                                     self.station_to_number[c["dest"]],
                                     c["distance"], c["line"]))

    def station_names(self):
        return list(self.station_to_number.keys())

    def lines_of(self, name):
        return self.graph.station_lines.get(name, [])

    def line_names(self):
        res = set()
        for s in self.data.get("stations", []):
            res.update(s.get("lines", []))
        return sorted(res)

    def is_transfer(self, name):
        return len(self.lines_of(name)) > 1

    def check_data(self):
        """Return (ok, list of messages)."""
        msgs = []
        names = {s["name"] for s in self.data.get("stations", [])}
        lines = set(self.line_names())
        for line, st in REPRESENTATIVE.items():
            if line in lines and st not in names:
                msgs.append("Representative station '%s' of %s missing" % (st, line))
        if not names:
            msgs.append("No stations defined")
        for c in self.data.get("connections", []):
            for k in ("source", "dest"):
                if c[k] not in names:
                    msgs.append("Connection refers to unknown station '%s'" % c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                msgs.append("Invalid distance %r between %s and %s" % (d, c["source"], c["dest"]))
            elif d > 30000:
                msgs.append("Suspicious distance %r between %s and %s" % (d, c["source"], c["dest"]))
        connected = set()
        for c in self.data.get("connections", []):
            connected.add(c["source"])
            connected.add(c["dest"])
        for n in names - connected:
            msgs.append("Station '%s' has no connections" % n)
        return (not msgs), msgs

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: len(stations)-1 values (bidirectional)."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 entries")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
            self.data["connections"].append({"source": b, "dest": a, "distance": d, "line": line_name})
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

    def update_distance(self, source, dest, distance, line=None):
        found = False
        for c in self.data["connections"]:
            if c["source"] == source and c["dest"] == dest and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self.build()
        return found

    def save(self, path=None):
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
