"""Data management: build graph, integrity check, updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE_STATIONS = ["西直门", "国贸", "北京南站", "朝阳门", "东直门", "公主坟"]


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.dataFile = data_file
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
            self._ensure(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a, b = self._ensure(c["source"]), self._ensure(c["dest"])
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))
            for n in (c["source"], c["dest"]):
                lines = self.graph.station_lines.setdefault(n, [])
                if c["line"] not in lines:
                    lines.append(c["line"])

    def _ensure(self, name):
        if name not in self.station_to_number:
            num = len(self.station_to_number)
            self.station_to_number[name] = num
            self.number_to_station[num] = name
            self.graph.add_node(num)
        return self.station_to_number[name]

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1

    def all_lines(self):
        lines = set()
        for ls in self.graph.station_lines.values():
            lines.update(ls)
        return sorted(lines)

    def resolve_line(self, pref):
        """Match a user supplied line preference to a known line name."""
        if not pref:
            return None
        lines = self.all_lines()
        if pref in lines:
            return pref
        for l in lines:
            if pref in l or l in pref:
                return l
        return None

    # ---- integrity check ----
    def check_integrity(self):
        """Return (ok, list of messages)."""
        problems, notes = [], []
        stations = self.data.get("stations", [])
        conns = self.data.get("connections", [])
        names = {s["name"] for s in stations}
        notes.append("Stations: %d, connections: %d, lines: %d" %
                     (len(names), len(conns), len(self.all_lines())))
        missing = [n for n in REPRESENTATIVE_STATIONS if n not in names]
        if missing:
            notes.append("Warning: representative stations missing: " + ", ".join(missing))
        for c in conns:
            for k in ("source", "dest"):
                if c[k] not in names:
                    problems.append("Connection station not in station list: %s" % c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                problems.append("Invalid distance %r between %s and %s" % (d, c["source"], c["dest"]))
            elif d > 20000:
                notes.append("Warning: unusually long distance %s-%s: %s m" % (c["source"], c["dest"], d))
            if c["source"] == c["dest"]:
                problems.append("Self loop at %s" % c["source"])
        connected = set()
        for c in conns:
            connected.update((c["source"], c["dest"]))
        for n in sorted(names - connected):
            problems.append("Station without connections: %s" % n)
        # connectivity of whole network
        if self.graph.nodes():
            start = self.graph.nodes()[0]
            seen, stack = {start}, [start]
            while stack:
                u = stack.pop()
                for e in self.graph.neighbors(u):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        stack.append(e.dest)
            if len(seen) != len(self.graph.nodes()):
                notes.append("Warning: network has %d disconnected stations" %
                             (len(self.graph.nodes()) - len(seen)))
        return (not problems), problems + notes

    # ---- updates ----
    def add_line(self, line_name, station_names, distances):
        """Add a line given ordered stations and distances between neighbors."""
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have len(stations)-1 entries")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in station_names:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
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
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self.build()
        return found

    def save(self, path=None):
        import json
        with open(path or self.dataFile, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
