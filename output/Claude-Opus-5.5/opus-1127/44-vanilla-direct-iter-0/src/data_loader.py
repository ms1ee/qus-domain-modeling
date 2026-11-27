"""
Data management module.

Loads the Beijing Subway network from ``subway_data.json``, builds the
station mapping and graph structures, performs data integrity checks and
supports data updates (new lines, station modification, distance updates).
"""

from __future__ import annotations

import json
import os
from collections import deque
from typing import Dict, List, Optional

from models import Edge, Graph

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")

# Main lines that should be covered by the data set.
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations (English / Chinese candidates) for main lines.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Tian'anmen East", "Tiananmen East", "Xidan", "天安门东", "西单"],
    "Line 2": ["Beijing Railway Station", "Jishuitan", "北京站", "积水潭"],
    "Line 4": ["Xidan", "Zhongguancun", "西单", "中关村"],
    "Line 5": ["Dongdan", "Yonghegong Lama Temple", "Yonghegong", "东单", "雍和宫"],
    "Line 10": ["Guomao", "Sanyuanqiao", "国贸", "三元桥"],
    "Line 13": ["Xizhimen", "Huilongguan", "西直门", "回龙观"],
}

# Module-level data structures (populated by init_global_data()).
station_to_number: Dict[str, int] = {}
graph: Dict[str, Dict[str, int]] = {}


def load_subway_data(path: str = DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway data file."""
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be lists")
    return data


def build_station_mapping(data: dict) -> Dict[str, int]:
    """Map station names to numbers (in order of appearance)."""
    mapping: Dict[str, int] = {}
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


def build_graph_dict(data: dict) -> Dict[str, Dict[str, int]]:
    """Adjacency dict {station: {neighbor: distance}} (undirected, min distance)."""
    g: Dict[str, Dict[str, int]] = {}
    for st in data.get("stations", []):
        if st.get("name") is not None:
            g.setdefault(st["name"], {})
    for c in data.get("connections", []):
        s, d, dist = c.get("source"), c.get("dest"), c.get("distance")
        if s is None or d is None or not isinstance(dist, (int, float)):
            continue
        for a, b in ((s, d), (d, s)):
            g.setdefault(a, {})
            if b not in g[a] or dist < g[a][b]:
                g[a][b] = dist
    return g


def init_global_data(path: str = DATA_FILE_PATH) -> None:
    """Populate the module-level ``station_to_number`` and ``graph`` dicts."""
    data = load_subway_data(path)
    station_to_number.clear()
    station_to_number.update(build_station_mapping(data))
    graph.clear()
    graph.update(build_graph_dict(data))


class SubwayNetwork:
    """Container for the built network structures."""

    def __init__(self, graph_obj: Graph, station_to_number_map: Dict[str, int],
                 number_to_station_map: Dict[int, str], graph_dict: Dict[str, Dict[str, int]]):
        self.graph = graph_obj
        self.station_to_number = station_to_number_map
        self.number_to_station = number_to_station_map
        self.graph_dict = graph_dict

    def station_names(self) -> List[str]:
        return list(self.station_to_number.keys())


def build_network(data: dict) -> SubwayNetwork:
    """Build Graph and mappings from loaded data."""
    mapping = build_station_mapping(data)
    reverse = {v: k for k, v in mapping.items()}
    g = Graph()
    station_lines: Dict[str, List[str]] = {name: [] for name in mapping}
    for st in data.get("stations", []):
        name = st.get("name")
        if name is None:
            continue
        for line in st.get("lines", []) or []:
            if line not in station_lines[name]:
                station_lines[name].append(line)
    for c in data.get("connections", []):
        line = c.get("line")
        for key in ("source", "dest"):
            name = c.get(key)
            if name is not None and line and line not in station_lines[name]:
                station_lines[name].append(line)
    for name, num in mapping.items():
        g.add_station(name, num, station_lines[name])
    for c in data.get("connections", []):
        s, d, dist = c.get("source"), c.get("dest"), c.get("distance")
        if s is None or d is None or s == d:
            continue
        if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
            continue
        g.add_edge(Edge(mapping[s], mapping[d], dist, c.get("line")))
    return SubwayNetwork(g, mapping, reverse, build_graph_dict(data))


class SubwayDataManager:
    """Manages subway data: integrity checks and updates."""

    def __init__(self, data: Optional[dict] = None, path: str = DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ---------------------------------------------------------- queries
    def _station(self, name: str) -> Optional[dict]:
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def station_names(self) -> List[str]:
        return [st.get("name") for st in self.data["stations"] if st.get("name") is not None]

    def get_lines(self) -> List[str]:
        lines: List[str] = []
        for st in self.data["stations"]:
            for line in st.get("lines", []) or []:
                if line not in lines:
                    lines.append(line)
        for c in self.data["connections"]:
            line = c.get("line")
            if line and line not in lines:
                lines.append(line)
        return lines

    def get_line_stations(self, line: str) -> List[str]:
        """Station sequence of a line derived from its connections."""
        adj: Dict[str, List[str]] = {}
        for c in self.data["connections"]:
            if c.get("line") != line:
                continue
            s, d = c.get("source"), c.get("dest")
            adj.setdefault(s, [])
            adj.setdefault(d, [])
            if d not in adj[s]:
                adj[s].append(d)
            if s not in adj[d]:
                adj[d].append(s)
        if not adj:
            return [st["name"] for st in self.data["stations"] if line in (st.get("lines") or [])]
        endpoints = [n for n, nb in adj.items() if len(nb) == 1]
        start = endpoints[0] if endpoints else next(iter(adj))
        order, seen = [], set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            order.append(node)
            for nb in reversed(adj[node]):
                if nb not in seen:
                    stack.append(nb)
        return order

    def get_transfer_stations(self) -> Dict[str, List[str]]:
        return {st["name"]: list(st.get("lines") or []) for st in self.data["stations"]
                if len(st.get("lines") or []) > 1}

    def build_network(self) -> SubwayNetwork:
        return build_network(self.data)

    # ---------------------------------------------------------- integrity
    def check_integrity(self) -> dict:
        errors: List[str] = []
        warnings: List[str] = []
        stations = self.data["stations"]
        connections = self.data["connections"]
        names = set()

        for i, st in enumerate(stations):
            name = st.get("name")
            if not name or not isinstance(name, str):
                errors.append(f"Station #{i} has no valid name")
                continue
            if name in names:
                warnings.append(f"Duplicate station entry: '{name}'")
            names.add(name)
            if not st.get("lines"):
                warnings.append(f"Station '{name}' has no line information")

        lines = self.get_lines()
        # Coverage of main lines
        norm_lines = {l.lower().replace(" ", ""): l for l in lines}
        for main in MAIN_LINES:
            if main.lower().replace(" ", "") not in norm_lines:
                warnings.append(f"Main line '{main}' not found in data")
        for line, candidates in REPRESENTATIVE_STATIONS.items():
            if line in lines and not any(c in names for c in candidates):
                warnings.append(f"No representative station found for {line}")

        # Connection integrity and distance accuracy
        seen_pairs = set()
        connected = set()
        station_line_map = {st.get("name"): set(st.get("lines") or []) for st in stations}
        for i, c in enumerate(connections):
            s, d, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = f"Connection #{i} ({s} - {d})"
            if s not in names:
                errors.append(f"{label}: source station '{s}' does not exist")
            if d not in names:
                errors.append(f"{label}: destination station '{d}' does not exist")
            if s == d:
                errors.append(f"{label}: connects a station to itself")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append(f"{label}: invalid distance {dist!r}")
            elif dist <= 0:
                errors.append(f"{label}: distance must be positive (got {dist})")
            elif dist < 200 or dist > 30000:
                warnings.append(f"{label}: unusual distance {dist} meters")
            if not line:
                warnings.append(f"{label}: missing line information")
            else:
                for n in (s, d):
                    if n in station_line_map and line not in station_line_map[n]:
                        warnings.append(f"{label}: station '{n}' is not listed on {line}")
            key = (frozenset((s, d)), line)
            if key in seen_pairs:
                warnings.append(f"{label}: duplicate connection on {line}")
            seen_pairs.add(key)
            connected.add(s)
            connected.add(d)

        for n in names:
            if n not in connected:
                warnings.append(f"Station '{n}' has no connections")

        # Connectivity
        g = build_graph_dict(self.data)
        components = 0
        visited = set()
        for n in g:
            if n in visited:
                continue
            components += 1
            q = deque([n])
            visited.add(n)
            while q:
                x = q.popleft()
                for y in g[x]:
                    if y not in visited:
                        visited.add(y)
                        q.append(y)
        if components > 1:
            warnings.append(f"Network is not fully connected ({components} components)")

        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "stations": len(names),
                "connections": len(connections),
                "lines": len(lines),
                "transfer_stations": len(self.get_transfer_stations()),
                "components": components,
            },
        }

    # ---------------------------------------------------------- updates
    def add_station(self, name: str, lines: Optional[List[str]] = None) -> None:
        st = self._station(name)
        if st is None:
            self.data["stations"].append({"name": name, "lines": list(lines or [])})
        else:
            for line in lines or []:
                st.setdefault("lines", [])
                if line not in st["lines"]:
                    st["lines"].append(line)

    def add_line(self, line_name: str, stations: List[str], distances: List[int]) -> None:
        """Add a new line given its station sequence and inter-station distances."""
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for dist in distances:
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                raise ValueError(f"Invalid distance: {dist!r}")
        for name in stations:
            self.add_station(name, [line_name])
        for i, dist in enumerate(distances):
            self.data["connections"].append({
                "source": stations[i], "dest": stations[i + 1],
                "distance": dist, "line": line_name,
            })

    def modify_station(self, name: str, new_name: Optional[str] = None,
                       lines: Optional[List[str]] = None) -> None:
        st = self._station(name)
        if st is None:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self._station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)

    def update_distance(self, source: str, dest: str, distance: int,
                        line: Optional[str] = None) -> int:
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Invalid distance: {distance!r}")
        count = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return count

    def save(self, path: Optional[str] = None) -> None:
        with open(path or self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
