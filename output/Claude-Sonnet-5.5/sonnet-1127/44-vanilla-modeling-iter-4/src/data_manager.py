"""Data management: building the graph, integrity checks and updates."""
import json

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

MAIN_LINES = ["1", "2", "4", "5", "6", "8", "10", "13", "14", "15",
              "昌平", "亦庄", "房山", "机场", "Changping", "Yizhuang", "Fangshan", "Airport"]


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = Graph()
        self.lines = {}
        self.build()

    def build(self):
        g = Graph()
        self.graph = g
        data = self.data
        num = 0
        for s in data.get("stations", []):
            if s["name"] not in g.station_to_number:
                num += 1
                g.register_station(s["name"], num)
            g.set_station_lines(s["name"], s.get("lines", []))
        lines = {}
        for c in data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    num += 1
                    g.register_station(n, num)
                    g.set_station_lines(n, [c["line"]])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
            seq = lines.setdefault(c["line"], [])
            for n in (c["source"], c["dest"]):
                if n not in seq:
                    seq.append(n)
        for s in data.get("stations", []):
            for l in s.get("lines", []):
                seq = lines.setdefault(l, [])
                if s["name"] not in seq:
                    seq.append(s["name"])
        self.lines = lines

    @property
    def station_to_number(self):
        return self.graph.station_to_number

    def has_station(self, name):
        return name in self.graph.station_to_number

    def normalize_station(self, name):
        name = (name or "").strip()
        if name in self.station_to_number:
            return name
        if name.endswith("站") and name[:-1] in self.station_to_number:
            return name[:-1]
        if name + "站" in self.station_to_number:
            return name + "站"
        return None

    def check_data(self):
        """Return (ok, messages)."""
        msgs, ok = [], True
        names = set(s["name"] for s in self.data.get("stations", []))
        if not names:
            return False, ["No station data"]
        msgs.append("Stations: %d, lines: %d" % (len(names), len(self.lines)))
        for l in MAIN_LINES:
            pass
        found = [m for m in MAIN_LINES if any(m in ln for ln in self.lines)]
        if len(found) < 5:
            msgs.append("WARNING: few main lines recognized")
        conns = self.data.get("connections", [])
        for c in conns:
            if c["source"] not in names or c["dest"] not in names:
                ok = False
                msgs.append("ERROR: connection references unknown station: %s - %s"
                            % (c["source"], c["dest"]))
            if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0:
                ok = False
                msgs.append("ERROR: invalid distance %s - %s: %r"
                            % (c["source"], c["dest"], c["distance"]))
            elif c["distance"] > 30000:
                msgs.append("WARNING: suspicious distance %s - %s: %s"
                            % (c["source"], c["dest"], c["distance"]))
        connected = set()
        for c in conns:
            connected.add(c["source"])
            connected.add(c["dest"])
        for n in sorted(names - connected):
            msgs.append("WARNING: station without connections: %s" % n)
        # connectivity
        g = self.graph
        if g.station_to_number:
            start = next(iter(g.station_to_number.values()))
            seen, stack = {start}, [start]
            while stack:
                u = stack.pop()
                for e in g.neighbors(u):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        stack.append(e.dest)
            if len(seen) < len(connected):
                msgs.append("WARNING: network has %d disconnected stations"
                            % (len(connected) - len(seen)))
        msgs.append("Data check " + ("passed" if ok else "FAILED"))
        return ok, msgs

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters values."""
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
        if distance <= 0:
            raise ValueError("distance must be positive")
        hit = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = int(distance)
                hit = True
        if hit:
            self.build()
        return hit

    def save(self, path=None):
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
