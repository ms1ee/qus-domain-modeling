"""Data management: build graph, integrity check, updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Graph, Edge

REPRESENTATIVE_STATIONS = ["西直门", "国贸", "北京站", "天安门东", "东直门", "公主坟"]


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = None
        self.build_graph()

    def build_graph(self):
        g = Graph()
        num = 0
        for st in self.data.get("stations", []):
            if st["name"] not in g.station_to_number:
                g.add_station(st["name"], num)
                num += 1
            g.set_station_lines(st["name"], st.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    g.add_station(n, num)
                    num += 1
                    g.set_station_lines(n, [c["line"]])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
        self.graph = g
        return g

    def line_names(self):
        names = []
        for st in self.data.get("stations", []):
            for l in st.get("lines", []):
                if l not in names:
                    names.append(l)
        for c in self.data.get("connections", []):
            if c["line"] not in names:
                names.append(c["line"])
        return names

    def resolve_line(self, text):
        if not text:
            return None
        names = self.line_names()
        if text in names:
            return text
        low = text.lower().replace(" ", "")
        for n in names:
            if n.lower().replace(" ", "") == low:
                return n
        return text

    def check_data(self):
        """Return (ok, messages)."""
        msgs = []
        ok = True
        names = {s["name"] for s in self.data.get("stations", [])}
        if not names:
            return False, ["No station data"]
        msgs.append("Stations: %d, lines: %d" % (len(names), len(self.line_names())))
        missing = [s for s in REPRESENTATIVE_STATIONS if s not in names]
        if missing:
            msgs.append("Warning: representative stations missing: " + ", ".join(missing))
        conns = self.data.get("connections", [])
        msgs.append("Connections: %d" % len(conns))
        for c in conns:
            for k in ("source", "dest"):
                if c[k] not in names:
                    ok = False
                    msgs.append("Connection refers to unknown station: %s" % c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                ok = False
                msgs.append("Suspicious distance %r between %s and %s" % (d, c["source"], c["dest"]))
        connected = set()
        for c in conns:
            connected.add(c["source"])
            connected.add(c["dest"])
        isolated = names - connected
        if isolated:
            ok = False
            msgs.append("Stations without connections: " + ", ".join(sorted(isolated)))
        msgs.append("Data check " + ("passed" if ok else "FAILED"))
        return ok, msgs

    # ---- update mechanisms (in-memory; optionally saved) ----
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
        self.build_graph()

    def update_station(self, name, new_name=None, lines=None):
        for st in self.data["stations"]:
            if st["name"] == name:
                if lines is not None:
                    st["lines"] = list(lines)
                if new_name:
                    st["name"] = new_name
                    for c in self.data["connections"]:
                        if c["source"] == name:
                            c["source"] = new_name
                        if c["dest"] == name:
                            c["dest"] = new_name
                self.build_graph()
                return True
        return False

    def update_distance(self, a, b, distance):
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if found:
            self.build_graph()
        return found

    def save(self, path=None):
        import json
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
