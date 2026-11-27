"""Data management: building the graph, checks and updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "1号线": [], "2号线": [], "4号线": [], "5号线": [], "10号线": [],
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
        self.graph.add_node(num)
        self.graph.set_station_lines(name, lines)

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1

    def lines(self):
        result = {}
        for s in self.data.get("stations", []):
            for l in s.get("lines", []):
                result.setdefault(l, []).append(s["name"])
        return result

    # ---- integrity check ----
    def check_data(self):
        """Return (ok, list of messages)."""
        msgs = []
        ok = True
        names = set(self.station_to_number)
        lines = self.lines()
        wanted = ["1号线", "2号线", "4号线", "5号线", "6号线", "8号线", "10号线",
                  "13号线", "14号线", "15号线", "昌平线", "亦庄线", "房山线", "首都机场线"]
        missing = [w for w in wanted if not any(w in l or l in w for l in lines)]
        msgs.append("Stations: %d, lines: %d" % (len(names), len(lines)))
        if missing:
            msgs.append("Lines possibly missing: " + ", ".join(missing))
        conns = self.data.get("connections", [])
        stset = {s["name"] for s in self.data.get("stations", [])}
        for c in conns:
            if c["source"] not in stset or c["dest"] not in stset:
                ok = False
                msgs.append("Connection references unknown station: %s -> %s" % (c["source"], c["dest"]))
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                ok = False
                msgs.append("Invalid distance: %s -> %s (%r)" % (c["source"], c["dest"], d))
        connected = set()
        for c in conns:
            connected.add(c["source"])
            connected.add(c["dest"])
        isolated = stset - connected
        if isolated:
            ok = False
            msgs.append("Stations without connections: %d" % len(isolated))
        msgs.append("Data check " + ("passed" if ok else "FAILED"))
        return ok, msgs

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: meters between consecutive stations."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
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

    def modify_station(self, name, new_name=None, lines=None):
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
                c["distance"] = distance
                found = True
        if found:
            self.build()
        return found
