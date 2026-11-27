"""Data management: build graph, integrity check, updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": [], "Line 2": [], "Line 4": [], "Line 5": [], "Line 6": [],
    "Line 8": [], "Line 10": [], "Line 13": [], "Line 14": [], "Line 15": [],
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = None
        self.station_to_number = {}
        self.number_to_station = {}
        self.build()

    def build(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        for s in self.data.get("stations", []):
            self._add_station(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in self.station_to_number:
                    self._add_station(n, [c.get("line")])
            self.graph.add_edge(Edge(self.station_to_number[c["source"]],
                                     self.station_to_number[c["dest"]],
                                     c["distance"], c.get("line")))

    def _add_station(self, name, lines):
        if name in self.station_to_number:
            return
        num = len(self.station_to_number)
        self.station_to_number[name] = num
        self.number_to_station[num] = name
        self.graph.set_station_lines(name, lines)
        self.graph.add_node(num)

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1

    def check_data(self):
        """Return (ok, list of messages)."""
        msgs = []
        stations = self.data.get("stations", [])
        conns = self.data.get("connections", [])
        names = {s["name"] for s in stations}
        lines = {l for s in stations for l in s.get("lines", [])}
        for ln in REPRESENTATIVE:
            if ln not in lines:
                msgs.append("Line missing from station data: %s" % ln)
        connected = set()
        for c in conns:
            for n in (c["source"], c["dest"]):
                connected.add(n)
                if n not in names:
                    msgs.append("Connection references unknown station: %s" % n)
            if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0:
                msgs.append("Invalid distance: %s - %s" % (c["source"], c["dest"]))
            elif c["distance"] > 20000:
                msgs.append("Suspicious distance: %s - %s (%s m)" % (c["source"], c["dest"], c["distance"]))
        for n in sorted(names - connected):
            msgs.append("Station without connections: %s" % n)
        return (not msgs), msgs

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters."""
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
        self.build()

    def update_station(self, name, lines):
        for s in self.data["stations"]:
            if s["name"] == name:
                s["lines"] = list(lines)
                self.build()
                return
        raise KeyError(name)

    def update_distance(self, a, b, distance):
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if not found:
            raise KeyError("%s-%s" % (a, b))
        self.build()
