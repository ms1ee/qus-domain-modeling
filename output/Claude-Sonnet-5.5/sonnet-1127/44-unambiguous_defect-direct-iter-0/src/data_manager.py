"""Network construction, integrity checks and data updates."""
from models import Graph, Edge
from data_loader import load_subway_data, DATA_FILE_PATH

MAIN_LINE_KEYS = ["1", "2", "4", "5", "6", "8", "10", "13", "14", "15"]


class SubwayNetwork:
    def __init__(self, data=None):
        self.data = data if data is not None else load_subway_data(DATA_FILE_PATH)
        self.rebuild()

    def rebuild(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        for s in self.data.get("stations", []):
            self._number(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a, b = self._number(c["source"]), self._number(c["dest"])
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))
            for n in (c["source"], c["dest"]):
                ls = self.graph.station_lines.setdefault(n, [])
                if c["line"] not in ls:
                    ls.append(c["line"])
        for n in self.station_to_number.values():
            self.graph.add_node(n)

    def _number(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
        return self.station_to_number[name]

    # ---- integrity check ----
    def check_data(self):
        """Return (ok, list of messages)."""
        msgs = []
        ok = True
        names = {s["name"] for s in self.data.get("stations", [])}
        lines = set()
        for s in self.data.get("stations", []):
            lines.update(s.get("lines", []))
        msgs.append("Stations: %d, connections: %d, lines: %d" % (
            len(names), len(self.data.get("connections", [])), len(lines)))
        for k in MAIN_LINE_KEYS:
            if not any(k in "".join(ch if ch.isdigit() else " " for ch in l).split() for l in lines):
                msgs.append("Warning: main line %s not found" % k)
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in names:
                    ok = False
                    msgs.append("Connection references unknown station: %s" % n)
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                ok = False
                msgs.append("Invalid distance %s between %s and %s" % (d, c["source"], c["dest"]))
            elif d > 30000:
                msgs.append("Warning: suspicious long distance %s-%s: %s" % (c["source"], c["dest"], d))
        connected = {n for n in self.graph.nodes() if self.graph.neighbors(n)}
        for name, n in self.station_to_number.items():
            if n not in connected:
                msgs.append("Warning: station without connections: %s" % name)
        msgs.append("Data check " + ("passed" if ok else "FAILED"))
        return ok, msgs

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        if len(distances) != len(stations) - 1:
            raise ValueError("need len(stations)-1 distances")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for i, d in enumerate(distances):
            self.data["connections"].append(
                {"source": stations[i], "dest": stations[i + 1], "distance": d, "line": line_name})
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

    def update_distance(self, a, b, distance, line=None):
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self.rebuild()
        return found
