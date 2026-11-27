"""High-level subway system: data, station numbering, graph and queries."""
import difflib

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]


class RouteError(Exception):
    pass


class SubwaySystem:
    def __init__(self, path=DATA_FILE_PATH, data=None):
        self.data = data if data is not None else load_subway_data(path)
        self.rebuild()

    def rebuild(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        # adjacency list dictionary: number -> list of (dest number, distance, line)
        self.graph_dict = {}
        for st in self.data.get("stations", []):
            self._register(st["name"], st.get("lines", []))
        for c in self.data.get("connections", []):
            for name in (c["source"], c["dest"]):
                if name not in self.station_to_number:
                    self._register(name, [c.get("line")] if c.get("line") else [])
            s = self.station_to_number[c["source"]]
            d = self.station_to_number[c["dest"]]
            self.graph.add_edge(Edge(s, d, c["distance"], c.get("line")))
            self.graph_dict[s].append((d, c["distance"], c.get("line")))

    def _register(self, name, lines):
        if name in self.station_to_number:
            return
        n = len(self.station_to_number)
        self.station_to_number[name] = n
        self.number_to_station[n] = name
        self.graph.add_vertex(n)
        self.graph.set_station_lines(name, lines)
        self.graph_dict[n] = []

    def resolve_station(self, name):
        """Return the matching official station name or None."""
        name = (name or "").strip()
        if not name:
            return None
        if name in self.station_to_number:
            return name
        lower = {k.lower(): k for k in self.station_to_number}
        if name.lower() in lower:
            return lower[name.lower()]
        matches = difflib.get_close_matches(name.lower(), list(lower.keys()), n=1, cutoff=0.6)
        if matches:
            return lower[matches[0]]
        return None

    def query(self, start, end, config=None):
        config = config or PathfindingConfig()
        if start not in self.station_to_number:
            raise RouteError(f"Starting station '{start}' does not exist, please check the station name")
        if end not in self.station_to_number:
            raise RouteError(f"Ending station '{end}' does not exist, please check the station name")
        if start == end:
            raise RouteError("Starting station cannot be the same as the ending station")
        s = self.station_to_number[start]
        t = self.station_to_number[end]
        try:
            sp = ShortestPath(self.graph, s, config)
            nums, edges = sp.path_with_edges(t)
        except Exception as exc:
            raise RouteError(f"Path calculation error: {exc}")
        if not nums:
            raise RouteError(f"No route found from '{start}' to '{end}' under the given constraints")
        distance = sum(e.weight for e in edges)
        transfers = sp.get_transfer_count(t)
        try:
            fare = Sum_money(distance)
        except Exception as exc:
            raise RouteError(f"Fare calculation error: {exc}")
        stations = [self.number_to_station[n] for n in nums]
        segments = []
        for i, e in enumerate(edges):
            if segments and segments[-1]["line"] == e.line:
                segments[-1]["stations"].append(stations[i + 1])
                segments[-1]["to"] = stations[i + 1]
                segments[-1]["distance"] += e.weight
            else:
                segments.append({"line": e.line, "from": stations[i], "to": stations[i + 1],
                                 "stations": [stations[i], stations[i + 1]], "distance": e.weight})
        transfer_stations = [seg["from"] for seg in segments[1:]]
        lines = []
        for seg in segments:
            if seg["line"] not in lines:
                lines.append(seg["line"])
        return {
            "query": {"start": start, "end": end, "mode": config.mode,
                      "max_transfers": config.max_transfers,
                      "line_preference": list(config.preferred_lines)},
            "path": stations,
            "segments": segments,
            "distance": distance,
            "distance_km": round(distance / 1000.0, 2),
            "fare": fare,
            "estimated_time": round(calculate_estimated_time(distance, transfers), 1),
            "transfer_count": transfers,
            "transfer_stations": transfer_stations,
            "lines": lines,
        }
