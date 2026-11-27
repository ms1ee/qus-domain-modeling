"""Data management: loading, graph building, checks and updates."""
from data_loader import load_subway_data, DATA_FILE_PATH
from models import Graph, Edge

REPRESENTATIVE = {
    "1号线": ["苹果园", "国贸"], "2号线": ["西直门", "积水潭"],
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.build()

    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.line_stations = {}
        for s in self.data.get("stations", []):
            n = self.station_to_number.setdefault(s["name"], len(self.station_to_number))
            self.number_to_station[n] = s["name"]
            self.graph.add_node(n)
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for nm in (c["source"], c["dest"]):
                if nm not in self.station_to_number:
                    n = len(self.station_to_number)
                    self.station_to_number[nm] = n
                    self.number_to_station[n] = nm
                    self.graph.add_node(n)
                    self.graph.set_station_lines(nm, [c["line"]])
            a, b = self.station_to_number[c["source"]], self.station_to_number[c["dest"]]
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))
            seq = self.line_stations.setdefault(c["line"], [])
            for nm in (c["source"], c["dest"]):
                if nm not in seq:
                    seq.append(nm)

    def has_station(self, name):
        return name in self.station_to_number

    def station_names(self):
        return list(self.station_to_number.keys())

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1

    def lines(self):
        return sorted(self.line_stations)

    def check_data(self):
        """Return (ok, list of messages)."""
        msgs, ok = [], True
        stations = self.data.get("stations", [])
        conns = self.data.get("connections", [])
        msgs.append(f"Stations: {len(stations)}, connections: {len(conns)}, lines: {len(self.line_stations)}")
        if not stations or not conns:
            return False, msgs + ["Data is empty"]
        names = set(self.station_to_number)
        listed = {s["name"] for s in stations}
        if len(listed) != len(stations):
            ok = False
            msgs.append("Duplicate station names found")
        for c in conns:
            for k in ("source", "dest"):
                if c[k] not in listed:
                    ok = False
                    msgs.append(f"Connection references unknown station: {c[k]}")
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                ok = False
                msgs.append(f"Suspicious distance {d} between {c['source']} and {c['dest']}")
            if c["source"] == c["dest"]:
                ok = False
                msgs.append(f"Self-loop at {c['source']}")
        connected = set()
        for c in conns:
            connected.update((c["source"], c["dest"]))
        for nm in names - connected:
            ok = False
            msgs.append(f"Station without connections: {nm}")
        for line in REPRESENTATIVE and ["1号线", "2号线"]:
            pass
        msgs.append("Data check passed" if ok else "Data check found problems")
        return ok, msgs

    # ---- updates ----
    def add_line(self, line, station_names, distances):
        """Add a line; distances has len(station_names)-1 entries (meters)."""
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances length must be stations-1")
        known = {s["name"]: s for s in self.data["stations"]}
        for nm in station_names:
            if nm in known:
                if line not in known[nm]["lines"]:
                    known[nm]["lines"].append(line)
            else:
                self.data["stations"].append({"name": nm, "lines": [line]})
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line})
        self.build()

    def update_station(self, name, lines):
        for s in self.data["stations"]:
            if s["name"] == name:
                s["lines"] = list(lines)
                self.build()
                return
        raise KeyError(name)

    def update_distance(self, a, b, distance):
        if distance <= 0:
            raise ValueError("distance must be positive")
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if not found:
            raise KeyError((a, b))
        self.build()

    def save(self, path=None):
        import json
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
