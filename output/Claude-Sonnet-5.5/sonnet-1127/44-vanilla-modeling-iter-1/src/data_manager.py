"""Data management: build graph, integrity check, updates."""
from data_loader import load_subway_data, DATA_FILE_PATH
from models import Graph, Edge


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = {"stations": [], "connections": []}
        self.graph = Graph()

    def load(self):
        self.data = load_subway_data(self.data_file)
        self.build_graph()
        return self.graph

    def build_graph(self):
        g = Graph()
        for i, s in enumerate(self.data.get("stations", [])):
            g.add_station(s["name"], i)
            g.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a, b = c["source"], c["dest"]
            for n in (a, b):
                if n not in g.station_to_number:
                    g.add_station(n, len(g.station_to_number))
                    g.set_station_lines(n, [c.get("line")] if c.get("line") else [])
            g.add_edge(Edge(g.station_to_number[a], g.station_to_number[b],
                            c["distance"], c.get("line")))
        self.graph = g
        return g

    def lines(self):
        s = set()
        for st in self.data.get("stations", []):
            s.update(st.get("lines", []))
        for c in self.data.get("connections", []):
            if c.get("line"):
                s.add(c["line"])
        return sorted(s)

    def check_data(self):
        """Return (ok, list of messages)."""
        msgs = []
        names = [s["name"] for s in self.data.get("stations", [])]
        nameset = set(names)
        if not names:
            msgs.append("No station data")
        if len(names) != len(nameset):
            msgs.append("Duplicate station names found")
        for s in self.data.get("stations", []):
            if not s.get("lines"):
                msgs.append("Station without line: %s" % s["name"])
        conns = self.data.get("connections", [])
        if not conns:
            msgs.append("No connection data")
        for c in conns:
            for k in ("source", "dest"):
                if c[k] not in nameset:
                    msgs.append("Connection references unknown station: %s" % c[k])
            if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0:
                msgs.append("Invalid distance %s-%s" % (c["source"], c["dest"]))
            elif c["distance"] > 20000:
                msgs.append("Suspicious distance %s-%s: %s" % (c["source"], c["dest"], c["distance"]))
        connected = {c["source"] for c in conns} | {c["dest"] for c in conns}
        for n in names:
            if n not in connected:
                msgs.append("Isolated station: %s" % n)
        # connectivity
        g = self.graph
        if g.adjacency:
            start = next(iter(g.adjacency))
            seen = {start}
            stack = [start]
            while stack:
                u = stack.pop()
                for e in g.neighbors(u):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        stack.append(e.dest)
            if len(seen) != len(g.adjacency):
                msgs.append("Network not fully connected (%d of %d reachable)"
                            % (len(seen), len(g.adjacency)))
        return (not msgs), msgs

    # ---- updates ----
    def add_line(self, line_name, station_names, distances):
        """Add a new line: station_names in order, distances between consecutive stations."""
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances length must be stations-1")
        existing = {s["name"]: s for s in self.data["stations"]}
        for n in station_names:
            if n in existing:
                if line_name not in existing[n]["lines"]:
                    existing[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name})
        self.build_graph()

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
                self.build_graph()
                return True
        return False

    def update_distance(self, a, b, distance):
        n = 0
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = int(distance)
                n += 1
        if n:
            self.build_graph()
        return n > 0

    def save(self, path=None):
        import json
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
