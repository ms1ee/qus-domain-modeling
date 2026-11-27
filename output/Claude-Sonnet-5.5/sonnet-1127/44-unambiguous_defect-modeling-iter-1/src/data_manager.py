"""Data management and integrity checking."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE_STATIONS = {
    "1号线": "苹果园", "2号线": "西直门", "4号线": "西单", "5号线": "宋家庄",
    "10号线": "知春路", "13号线": "西二旗", "八通线": "土桥",
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = None
        self.rebuild_graph()

    def rebuild_graph(self):
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
        lines = {}
        for s in self.data.get("stations", []):
            lines.setdefault(s["name"], [])
            for l in s.get("lines", []):
                if l not in lines[s["name"]]:
                    lines[s["name"]].append(l)
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                lines.setdefault(n, [])
                if c["line"] not in lines[n]:
                    lines[n].append(c["line"])
        for n in names:
            g.set_station_lines(n, lines.get(n, []))
        for c in self.data.get("connections", []):
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
        self.graph = g

    def station_names(self):
        return set(self.graph.station_to_number)

    def line_names(self):
        out = []
        for ls in self.graph.station_lines.values():
            for l in ls:
                if l not in out:
                    out.append(l)
        return out

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """Add a line: stations is an ordered list, distances has len(stations)-1 entries."""
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
        self.rebuild_graph()

    def update_station(self, name, new_name=None, lines=None):
        found = False
        for s in self.data["stations"]:
            if s["name"] == name:
                found = True
                if lines is not None:
                    s["lines"] = list(lines)
                if new_name:
                    s["name"] = new_name
        if not found:
            raise KeyError(name)
        if new_name:
            for c in self.data["connections"]:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name
        self.rebuild_graph()

    def update_distance(self, a, b, distance, line=None):
        if distance <= 0:
            raise ValueError("distance must be positive")
        hit = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                hit = True
        if not hit:
            raise KeyError((a, b))
        self.rebuild_graph()

    def save(self, path=None):
        import json
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)


class DataIntegrityChecker:
    def __init__(self, manager):
        self.manager = manager
        self.stationCoverageValid = False
        self.connectionValid = False
        self.distanceValid = False
        self.messages = []

    def check(self):
        d = self.manager.data
        names = {s["name"] for s in d.get("stations", [])}
        lines = set(self.manager.line_names())
        self.messages = []
        missing = [(l, s) for l, s in REPRESENTATIVE_STATIONS.items()
                   if l in lines and s not in self.manager.station_names()]
        self.stationCoverageValid = bool(names) and not missing
        for l, s in missing:
            self.messages.append("Missing representative station %s on %s" % (s, l))
        bad = [c for c in d.get("connections", [])
               if c["source"] not in names or c["dest"] not in names or c["source"] == c["dest"]]
        g = self.manager.graph
        isolated = [n for n, num in g.station_to_number.items() if not g.neighbors(num)]
        self.connectionValid = not bad and not isolated and bool(d.get("connections"))
        for c in bad[:10]:
            self.messages.append("Bad connection: %s-%s" % (c["source"], c["dest"]))
        for n in isolated[:10]:
            self.messages.append("Isolated station: %s" % n)
        badd = [c for c in d.get("connections", [])
                if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0 or c["distance"] > 30000]
        self.distanceValid = not badd
        for c in badd[:10]:
            self.messages.append("Suspicious distance: %s-%s %s" % (c["source"], c["dest"], c["distance"]))
        return self.stationCoverageValid and self.connectionValid and self.distanceValid

    def report(self):
        ok = self.check()
        out = ["Station coverage: %s" % ("OK" if self.stationCoverageValid else "FAILED"),
               "Connections: %s" % ("OK" if self.connectionValid else "FAILED"),
               "Distances: %s" % ("OK" if self.distanceValid else "FAILED")]
        out += self.messages
        out.append("Data check %s" % ("passed" if ok else "failed"))
        return "\n".join(out)
