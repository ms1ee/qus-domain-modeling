"""SubwayNetwork: builds graph from data."""
import difflib
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Graph, Edge


class SubwayNetwork:
    def __init__(self, data_file=DATA_FILE_PATH, data=None):
        self.data_file = data_file
        self.data = data if data is not None else load_subway_data(data_file)
        self.build()

    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.lines = {}
        for s in self.data.get("stations", []):
            self._add_station(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in self.station_to_number:
                    self._add_station(n, [c.get("line")])
            a, b = self.station_to_number[c["source"]], self.station_to_number[c["dest"]]
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))
            seq = self.lines.setdefault(c["line"], [])
            for n in (c["source"], c["dest"]):
                if n not in seq:
                    seq.append(n)

    def _add_station(self, name, lines):
        if name in self.station_to_number:
            return
        num = len(self.station_to_number)
        self.station_to_number[name] = num
        self.number_to_station[num] = name
        self.graph.set_station_lines(name, [l for l in lines if l])
        self.graph.add_node(num)

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.graph.station_lines.get(name, [])) > 1

    def match_station(self, name):
        if name in self.station_to_number:
            return name
        m = difflib.get_close_matches(name, list(self.station_to_number), n=1, cutoff=0.5)
        return m[0] if m else None
