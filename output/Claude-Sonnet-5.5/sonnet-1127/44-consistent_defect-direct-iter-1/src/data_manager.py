"""Network building, integrity checks and data updates."""
from models import Edge, Graph

REPRESENTATIVE = {
    "1号线": "天安门东", "2号线": "西直门", "4号线": "西单", "5号线": "东单",
}


class SubwayNetwork:
    def __init__(self, data):
        self.data = data
        self.build()

    def build(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        names = [s["name"] for s in self.data.get("stations", [])]
        for c in self.data.get("connections", []):
            names.append(c["source"])
            names.append(c["dest"])
        for n in names:
            if n not in self.station_to_number:
                i = len(self.station_to_number)
                self.station_to_number[n] = i
                self.number_to_station[i] = n
                self.graph.add_node(i)
        for s in self.data.get("stations", []):
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            self.graph.add_edge(Edge(self.station_to_number[c["source"]],
                                     self.station_to_number[c["dest"]],
                                     c["distance"], c["line"]))

    # ---- updates ----
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: len(stations)-1 values (bidirectional)."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distance count mismatch")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line not in known[n]["lines"]:
                    known[n]["lines"].append(line)
            else:
                self.data["stations"].append({"name": n, "lines": [line]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line})
            self.data["connections"].append({"source": b, "dest": a, "distance": d, "line": line})
        self.build()

    def modify_station(self, name, new_name=None, lines=None):
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

    def update_distance(self, source, dest, distance, line=None):
        ok = False
        for c in self.data["connections"]:
            if c["source"] == source and c["dest"] == dest and (line is None or c["line"] == line):
                c["distance"] = distance
                ok = True
        if ok:
            self.build()
        return ok

    # ---- checks ----
    def check_data(self):
        problems = []
        names = {s["name"] for s in self.data.get("stations", [])}
        lines = set()
        for s in self.data.get("stations", []):
            lines.update(s.get("lines", []))
        report = ["Stations: %d, Connections: %d, Lines: %d" % (
            len(names), len(self.data.get("connections", [])), len(lines))]
        for ln, st in REPRESENTATIVE.items():
            if ln in lines and st not in names:
                problems.append("Representative station %s missing for %s" % (st, ln))
        connected = set()
        for c in self.data.get("connections", []):
            for k in ("source", "dest"):
                if c[k] not in names:
                    problems.append("Connection station %s not in station list" % c[k])
                connected.add(c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                problems.append("Bad distance %s->%s: %r" % (c["source"], c["dest"], d))
            if c["source"] == c["dest"]:
                problems.append("Self loop at %s" % c["source"])
        for n in sorted(names - connected):
            problems.append("Station %s has no connections" % n)
        if problems:
            report.append("Problems found (%d):" % len(problems))
            report.extend("  - " + p for p in problems[:50])
        else:
            report.append("Data check passed.")
        return not problems, "\n".join(report)
