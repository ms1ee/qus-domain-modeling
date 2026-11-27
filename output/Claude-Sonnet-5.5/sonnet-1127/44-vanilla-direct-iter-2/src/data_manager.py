"""Network management, integrity checks and data updates."""
from data_loader import load_subway_data, DATA_FILE_PATH
from models import Graph, Edge

REPRESENTATIVE_STATIONS = ["西单", "国贸", "西直门", "东直门", "公主坟", "北京南站", "朝阳门", "北京西站"]


class SubwayNetwork:
    def __init__(self, data=None):
        self.data = data if data is not None else load_subway_data(DATA_FILE_PATH)
        self.rebuild()

    def rebuild(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for s in self.data.get("stations", []):
            if s["name"] not in self.station_to_number:
                n = len(self.station_to_number)
                self.station_to_number[s["name"]] = n
                self.number_to_station[n] = s["name"]
                self.graph.add_node(n)
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a = self.station_to_number.get(c["source"])
            b = self.station_to_number.get(c["dest"])
            if a is None or b is None:
                continue
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))

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

    def update_station(self, name, lines=None, new_name=None):
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
        if distance <= 0:
            raise ValueError("distance must be positive")
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self.rebuild()
        return found

    # ---- checks ----
    def check_integrity(self):
        issues = []
        names = {s["name"] for s in self.data["stations"]}
        lines = set()
        for s in self.data["stations"]:
            lines.update(s.get("lines", []))
        for m in REPRESENTATIVE_STATIONS:
            if m not in names:
                issues.append("Representative station missing: %s" % m)
        connected = set()
        for c in self.data["connections"]:
            for k in ("source", "dest"):
                if c[k] not in names:
                    issues.append("Connection references unknown station: %s" % c[k])
                connected.add(c[k])
            if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0:
                issues.append("Invalid distance %s-%s" % (c["source"], c["dest"]))
            elif c["distance"] > 30000:
                issues.append("Suspicious distance %s-%s: %s" % (c["source"], c["dest"], c["distance"]))
            if c["source"] == c["dest"]:
                issues.append("Self loop at %s" % c["source"])
        for n in names - connected:
            issues.append("Station without connections: %s" % n)
        return {"ok": not issues, "stations": len(names), "lines": len(lines),
                "connections": len(self.data["connections"]), "issues": issues}
