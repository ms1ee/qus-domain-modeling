"""Data management and integrity checks."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": [], "Line 2": [], "Line 4": [], "Line 5": [], "Line 6": [], "Line 8": [],
    "Line 10": [], "Line 13": [], "Line 14": [], "Line 15": [], "Changping Line": [],
    "Yizhuang Line": [], "Fangshan Line": [], "Airport Line": [],
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = Graph()
        self.lines = {}
        self._build()

    def _build(self):
        g = Graph()
        for i, st in enumerate(sorted(self.data.get("stations", []), key=lambda s: s["name"])):
            g.add_station(st["name"], i)
            g.set_station_lines(st["name"], st.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    g.add_station(n, len(g.station_to_number))
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
        self.graph = g
        self.lines = {}
        for c in self.data.get("connections", []):
            seq = self.lines.setdefault(c["line"], [])
            for n in (c["source"], c["dest"]):
                if n not in seq:
                    seq.append(n)

    def get_graph(self):
        return self.graph

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """Add a line from an ordered station list and len-1 distances."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        for s in stations:
            if not any(x["name"] == s for x in self.data["stations"]):
                self.data["stations"].append({"name": s, "lines": [line_name]})
            else:
                self.update_station(s, add_line=line_name)
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self._build()

    def update_station(self, name, new_name=None, add_line=None):
        for st in self.data["stations"]:
            if st["name"] == name:
                if add_line and add_line not in st["lines"]:
                    st["lines"].append(add_line)
                if new_name:
                    st["name"] = new_name
                    for c in self.data["connections"]:
                        if c["source"] == name:
                            c["source"] = new_name
                        if c["dest"] == name:
                            c["dest"] = new_name
                self._build()
                return True
        return False

    def update_distance(self, a, b, distance, line=None):
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self._build()
        return found


class DataIntegrityChecker:
    def __init__(self, manager):
        self.manager = manager
        self.check_result = False

    def run(self):
        data = self.manager.data
        problems = []
        names = {s["name"] for s in data.get("stations", [])}
        lines = {l for s in data.get("stations", []) for l in s.get("lines", [])}
        for ln in REPRESENTATIVE:
            if ln not in lines:
                problems.append(f"Line missing from station data: {ln}")
        conn_nodes = set()
        for c in data.get("connections", []):
            conn_nodes.update((c["source"], c["dest"]))
            for n in (c["source"], c["dest"]):
                if n not in names:
                    problems.append(f"Connection refers to unknown station: {n}")
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                problems.append(f"Invalid distance {d} between {c['source']} and {c['dest']}")
            if c["source"] == c["dest"]:
                problems.append(f"Self loop at {c['source']}")
        for n in names - conn_nodes:
            problems.append(f"Station without connections: {n}")
        self.check_result = not problems
        return self.check_result, problems
