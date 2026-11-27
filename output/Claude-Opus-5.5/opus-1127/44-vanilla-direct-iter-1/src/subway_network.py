"""Builds the subway network graph from raw data and answers route queries."""

import re

from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath, count_transfers


class StationNotFoundError(KeyError):
    pass


class PathNotFoundError(Exception):
    pass


def _norm(name):
    s = str(name).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _loose(name):
    s = _norm(name)
    for suffix in (" station", "站"):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
    return re.sub(r"[\s'’\-]", "", s)


def build_station_to_number(data):
    """Map every station name (stations + connection endpoints) to a number."""
    mapping = {}
    for st in data.get("stations", []):
        name = st.get("name")
        if name is not None and name not in mapping:
            mapping[name] = len(mapping)
    for c in data.get("connections", []):
        for key in ("source", "dest"):
            name = c.get(key)
            if name is not None and name not in mapping:
                mapping[name] = len(mapping)
    return mapping


class SubwayNetwork:
    """Subway network: station mapping, Graph object and adjacency dict."""

    def __init__(self, data):
        self.data = data
        self.station_to_number = build_station_to_number(data)
        self.number_to_station = {n: s for s, n in self.station_to_number.items()}
        self.graph = Graph()
        # graph dict: station name -> list of (neighbor name, distance, line)
        self.graph_dict = {name: [] for name in self.station_to_number}
        lines_map = {}
        for st in data.get("stations", []):
            lines_map.setdefault(st["name"], [])
            for ln in st.get("lines", []) or []:
                if ln not in lines_map[st["name"]]:
                    lines_map[st["name"]].append(ln)
        for c in data.get("connections", []):
            for key in ("source", "dest"):
                lst = lines_map.setdefault(c["source"] if key == "source" else c["dest"], [])
                if c.get("line") and c["line"] not in lst:
                    lst.append(c["line"])
        for name, num in self.station_to_number.items():
            self.graph.add_station(num, name, lines_map.get(name, []))
        for c in data.get("connections", []):
            try:
                s, d = c["source"], c["dest"]
                dist = c["distance"]
            except KeyError:
                continue
            if s == d or not isinstance(dist, (int, float)) or dist < 0:
                continue
            self.graph.add_edge(Edge(self.station_to_number[s], self.station_to_number[d],
                                     dist, c.get("line")))
            self.graph_dict[s].append((d, dist, c.get("line")))
            self.graph_dict[d].append((s, dist, c.get("line")))
        self._exact = {_norm(n): n for n in self.station_to_number}
        self._loose = {}
        for n in self.station_to_number:
            self._loose.setdefault(_loose(n), n)

    # ------------------------------------------------------------------
    @property
    def station_lines(self):
        return self.graph.station_lines

    def all_lines(self):
        lines = []
        for lst in self.graph.station_lines.values():
            for ln in lst:
                if ln not in lines:
                    lines.append(ln)
        return lines

    def resolve_station(self, name):
        """Standardize a user-entered station name; None if unknown."""
        if name is None:
            return None
        raw = str(name).strip()
        if raw in self.station_to_number:
            return raw
        n = _norm(raw)
        if n in self._exact:
            return self._exact[n]
        return self._loose.get(_loose(raw))

    def query(self, start, end, config=None):
        """Compute a route between two (canonical) station names.

        :return: dict describing the route
        """
        if start not in self.station_to_number:
            raise StationNotFoundError(start)
        if end not in self.station_to_number:
            raise StationNotFoundError(end)
        config = config or PathfindingConfig()
        src = self.station_to_number[start]
        dst = self.station_to_number[end]
        sp = ShortestPath(self.graph, src, config)
        path, edges = sp.path_with_edges(dst)
        if not path:
            msg = "No route found from '%s' to '%s'" % (start, end)
            if config.max_transfers is not None:
                msg += " within %d transfer(s)" % config.max_transfers
            raise PathNotFoundError(msg)
        names = [self.number_to_station[v] for v in path]
        segments = []
        for i, e in enumerate(edges):
            if not segments or segments[-1]["line"] != e.line:
                segments.append({"line": e.line, "stations": [names[i]], "distance": 0})
            segments[-1]["stations"].append(names[i + 1])
            segments[-1]["distance"] += e.weight
        lines = []
        for seg in segments:
            if seg["line"] not in lines:
                lines.append(seg["line"])
        transfer_stations = [seg["stations"][0] for seg in segments[1:]]
        distance = sp.dist_to[dst]
        transfers = count_transfers(edges)
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, transfers)
        return {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "preferred_lines": list(config.preferred_lines),
            "path": names,
            "distance": distance,
            "transfer_count": transfers,
            "transfer_stations": transfer_stations,
            "lines": lines,
            "segments": segments,
            "fare": fare,
            "estimated_time": est,
        }
