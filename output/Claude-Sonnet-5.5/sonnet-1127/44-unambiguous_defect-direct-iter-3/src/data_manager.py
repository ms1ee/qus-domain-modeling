"""Network building, integrity check, and data updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "1号线": [], "2号线": [], "4号线": [], "5号线": [], "6号线": [], "8号线": [],
    "10号线": [], "13号线": [], "14号线": [], "15号线": [],
}


class DataManager:
    def __init__(self, path=DATA_FILE_PATH):
        self.data = load_subway_data(path)
        self.rebuild()

    def rebuild(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for s in self.data.get("stations", []):
            self._num(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a, b = self._num(c["source"]), self._num(c["dest"])
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))
            for n in (c["source"], c["dest"]):
                ls = self.graph.station_lines.setdefault(n, [])
                if c["line"] not in ls:
                    ls.append(c["line"])
        for n in self.station_to_number.values():
            self.graph.add_node(n)

    def _num(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
        return self.station_to_number[name]

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1

    def check_data(self):
        """Return (ok, list of messages)."""
        msgs = []
        ok = True
        stations = self.data.get("stations", [])
        conns = self.data.get("connections", [])
        names = {s["name"] for s in stations}
        if not stations or not conns:
            return False, ["Data is empty"]
        msgs.append("Stations: %d, connections: %d" % (len(names), len(conns)))
        lines = set()
        for s in stations:
            lines.update(s.get("lines", []))
        for c in conns:
            lines.add(c["line"])
        missing = [l for l in REPRESENTATIVE if l not in lines
                   and l.replace("号线", "") not in {x.replace("号线", "") for x in lines}]
        if missing:
            msgs.append("Warning: lines not found: " + ", ".join(missing))
        bad = [c for c in conns if c["source"] not in names or c["dest"] not in names]
        if bad:
            ok = False
            msgs.append("%d connections reference unknown stations" % len(bad))
        badd = [c for c in conns if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0]
        if badd:
            ok = False
            msgs.append("%d connections have invalid distance" % len(badd))
        loops = [c for c in conns if c["source"] == c["dest"]]
        if loops:
            ok = False
            msgs.append("%d self-loop connections" % len(loops))
        connected = {n for n, e in self.graph.graph.items() if e}
        iso = [self.number_to_station[n] for n in self.graph.graph if n not in connected]
        if iso:
            ok = False
            msgs.append("Isolated stations: " + ", ".join(iso[:10]))
        msgs.append("Data check " + ("passed" if ok else "FAILED"))
        return ok, msgs

    # updates
    def add_line(self, line_name, station_names, distances):
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in station_names:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                s = {"name": n, "lines": [line_name]}
                self.data["stations"].append(s)
                known[n] = s
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name})
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
                c["distance"] = int(distance)
                found = True
        if found:
            self.rebuild()
        return found
