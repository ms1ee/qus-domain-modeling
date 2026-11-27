"""Network building, integrity checks and data updates."""
from data_loader import load_subway_data, DATA_FILE_PATH
from models import Graph, Edge

MAIN_LINES = ["1号线", "2号线", "4号线", "5号线", "6号线", "8号线", "10号线",
              "13号线", "14号线", "15号线", "昌平线", "亦庄线", "房山线", "机场线"]


class SubwayNetwork:
    def __init__(self, data=None):
        self.data = data if data is not None else load_subway_data(DATA_FILE_PATH)
        self.rebuild()

    def rebuild(self):
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

    # ---- updates ----
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: len(stations)-1 metres."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances length mismatch")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line not in known[n]["lines"]:
                    known[n]["lines"].append(line)
            else:
                self.data["stations"].append({"name": n, "lines": [line]})
        for i, d in enumerate(distances):
            self.data["connections"].append(
                {"source": stations[i], "dest": stations[i + 1], "distance": d, "line": line})
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
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if found:
            self.rebuild()
        return found

    # ---- check ----
    def check_data(self):
        """Return (ok, list of messages)."""
        msgs, ok = [], True
        names = {s["name"] for s in self.data.get("stations", [])}
        if not names:
            return False, ["No station data"]
        msgs.append("Stations: %d" % len(names))
        present = set()
        for s in self.data["stations"]:
            present.update(s.get("lines", []))
        missing = [l for l in MAIN_LINES if l not in present]
        if missing:
            msgs.append("Warning: lines not found: " + ", ".join(missing))
        bad = 0
        connected = set()
        for c in self.data.get("connections", []):
            connected.update((c["source"], c["dest"]))
            if c["source"] not in names or c["dest"] not in names:
                bad += 1
                msgs.append("Connection refers to unknown station: %s-%s" % (c["source"], c["dest"]))
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                bad += 1
                msgs.append("Suspicious distance: %s-%s %r" % (c["source"], c["dest"], d))
        isolated = names - connected
        if isolated:
            msgs.append("Warning: stations without connections: %d" % len(isolated))
        if bad:
            ok = False
        msgs.append("Connections: %d" % len(self.data.get("connections", [])))
        msgs.append("Data check " + ("passed" if ok else "FAILED"))
        return ok, msgs
