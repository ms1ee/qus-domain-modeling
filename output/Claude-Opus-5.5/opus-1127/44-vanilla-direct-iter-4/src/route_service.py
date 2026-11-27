"""High-level subway system: builds the network and answers route queries."""

from data_loader import DATA_FILE_PATH, load_subway_data
from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath


class StationNotFoundError(ValueError):
    pass


class PathNotFoundError(RuntimeError):
    pass


def _normalize(name):
    n = " ".join(str(name).strip().split()).lower()
    for suffix in ("站", " station"):
        if n.endswith(suffix) and len(n) > len(suffix):
            n = n[: -len(suffix)].strip()
    return n


class SubwaySystem:
    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.data = data if data is not None else load_subway_data(path)
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self._normalized = {}
        self._build()

    def _add_station(self, name):
        if name not in self.station_to_number:
            num = len(self.station_to_number)
            self.station_to_number[name] = num
            self.number_to_station[num] = name
            self.graph.add_vertex(num)
            self._normalized.setdefault(_normalize(name), name)
        return self.station_to_number[name]

    def _build(self):
        for st in self.data.get("stations", []):
            name = st.get("name")
            if not name:
                continue
            self._add_station(name)
            self.graph.set_station_lines(name, st.get("lines", []))
        for c in self.data.get("connections", []):
            s, d = c.get("source"), c.get("dest")
            dist = c.get("distance")
            if not s or not d or dist is None or dist < 0:
                continue
            u = self._add_station(s)
            v = self._add_station(d)
            self.graph.add_edge(Edge(u, v, dist, c.get("line")))
            for name in (s, d):
                lines = self.graph.station_lines.setdefault(name, [])
                if c.get("line") and c.get("line") not in lines:
                    lines.append(c.get("line"))

    def find_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        stripped = str(name).strip()
        if stripped in self.station_to_number:
            return stripped
        return self._normalized.get(_normalize(stripped))

    def all_lines(self):
        lines = set()
        for ls in self.graph.station_lines.values():
            lines.update(ls)
        return sorted(lines)

    def query(self, start, end, config=None):
        config = config or PathfindingConfig()
        s_name = self.find_station(start)
        if s_name is None:
            raise StationNotFoundError(
                f"Starting station '{start}' does not exist, please check the station name")
        e_name = self.find_station(end)
        if e_name is None:
            raise StationNotFoundError(
                f"Ending station '{end}' does not exist, please check the station name")
        if s_name == e_name:
            raise ValueError("Starting station cannot be the same as the ending station")

        s, t = self.station_to_number[s_name], self.station_to_number[e_name]
        sp = ShortestPath(self.graph, s, config)
        if not sp.has_path_to(t):
            msg = f"No path found from '{s_name}' to '{e_name}'"
            if config.max_transfers is not None:
                msg += f" within {config.max_transfers} transfer(s)"
            raise PathNotFoundError(msg)
        nums, edges = sp.path_with_edges(t)
        distance = sp.dist_to[t]
        transfers = sp.get_transfer_count(t)
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, transfers)
        return build_result(self, s_name, e_name, config, nums, edges,
                            distance, transfers, fare, est)


def build_result(system, start, end, config, nums, edges, distance,
                 transfers, fare, est):
    names = [system.number_to_station[n] for n in nums]
    segments = []
    transfer_stations = []
    lines = []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if not segments or segments[-1]["line"] != e.line:
            if segments:
                transfer_stations.append({
                    "station": names[i],
                    "from_line": segments[-1]["line"],
                    "to_line": e.line,
                })
            segments.append({"line": e.line, "stations": [names[i]], "distance": 0})
        segments[-1]["stations"].append(names[i + 1])
        segments[-1]["distance"] += e.distance
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": names,
        "station_count": len(names),
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "estimated_time": round(est, 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }
