"""Subway network data management.

Builds the graph from the JSON data, resolves station names, plans routes,
checks data integrity and supports data updates.
"""

import re
import unicodedata
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Base class for route query errors."""


class StationNotFoundError(RouteError):
    pass


class SameStationError(RouteError):
    pass


class PathCalculationError(RouteError):
    pass


class FareError(RouteError):
    pass


# Main lines that must be covered, with name aliases (normalized form).
MAIN_LINES = {
    "Line 1": ["line1", "1号线", "line1/batong", "line1batongline"],
    "Line 2": ["line2", "2号线"],
    "Line 4": ["line4", "4号线", "line4daxingline", "line4/daxing"],
    "Line 5": ["line5", "5号线"],
    "Line 6": ["line6", "6号线"],
    "Line 8": ["line8", "8号线"],
    "Line 10": ["line10", "10号线"],
    "Line 13": ["line13", "13号线"],
    "Line 14": ["line14", "14号线"],
    "Line 15": ["line15", "15号线"],
    "Changping Line": ["changpingline", "changping", "昌平线"],
    "Yizhuang Line": ["yizhuangline", "yizhuang", "亦庄线"],
    "Fangshan Line": ["fangshanline", "fangshan", "房山线"],
    "Airport Line": ["airportline", "airportexpress", "capitalairportexpress",
                     "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "Guomao", "Tian'anmen East", "Tiananmen East", "西单", "国贸"],
    "Line 2": ["Xizhimen", "Dongzhimen", "Beijing Railway Station", "西直门", "东直门"],
    "Line 4": ["Xidan", "Zhongguancun", "Beijing South Railway Station", "中关村"],
    "Line 5": ["Dongdan", "Yonghegong Lama Temple", "Yonghegong", "东单", "雍和宫"],
    "Line 6": ["Chegongzhuang", "Dongsi", "车公庄", "东四"],
    "Line 8": ["Gulou Dajie", "Olympic Green", "鼓楼大街", "奥林匹克公园"],
    "Line 10": ["Guomao", "Haidian Huangzhuang", "Sanyuanqiao", "国贸", "三元桥"],
    "Line 13": ["Xizhimen", "Huilongguan", "Wangjing West", "回龙观", "望京西"],
    "Line 14": ["Wangjing", "Jintai Lu", "望京", "金台路"],
    "Line 15": ["Wangjing", "Olympic Green", "望京"],
    "Changping Line": ["Xi'erqi", "Xierqi", "Changping", "西二旗", "昌平"],
    "Yizhuang Line": ["Songjiazhuang", "Ciqu", "宋家庄", "次渠"],
    "Fangshan Line": ["Guogongzhuang", "郭公庄"],
    "Airport Line": ["Dongzhimen", "Sanyuanqiao", "Terminal 3", "T3", "东直门"],
}

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 30000


def normalize_station_name(name):
    """Normalize a station name for tolerant lookup."""
    text = unicodedata.normalize("NFKC", str(name)).strip()
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text).lower()
    for suffix in (" station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
    return text


def _compact(text):
    return re.sub(r"[\s'\-_.·]", "", text)


def normalize_line_name(name):
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    return re.sub(r"[\s\-_]", "", text)


class SubwayNetwork:
    """In-memory model of the subway network."""

    def __init__(self, data=None, data_path=None):
        self.data_path = data_path or DATA_FILE_PATH
        if data is None:
            data = load_subway_data(self.data_path)
        self.stations = []
        for st in data.get("stations", []):
            if isinstance(st, dict) and "name" in st:
                self.stations.append(
                    {"name": str(st["name"]), "lines": list(st.get("lines") or [])}
                )
        self.connections = []
        for c in data.get("connections", []):
            if isinstance(c, dict):
                self.connections.append(dict(c))
        self.build()

    # ---------------------------------------------------------------- build
    def build(self):
        """(Re)build station mapping and graph from stations/connections."""
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.load_warnings = []

        def register(name, lines):
            if name in self.station_to_number:
                return self.station_to_number[name]
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, lines)
            return number

        for st in self.stations:
            if st["name"] in self.station_to_number:
                self.load_warnings.append(f"Duplicate station '{st['name']}' ignored")
                continue
            register(st["name"], st["lines"])

        for c in self.connections:
            src, dst = c.get("source"), c.get("dest")
            line = c.get("line", "")
            dist = c.get("distance")
            if src is None or dst is None:
                self.load_warnings.append(f"Connection missing endpoint: {c}")
                continue
            for name in (src, dst):
                if name not in self.station_to_number:
                    self.load_warnings.append(
                        f"Station '{name}' referenced by a connection but not defined"
                    )
                    register(name, [line] if line else [])
            try:
                edge = Edge(self.station_to_number[src], self.station_to_number[dst],
                            dist, line)
            except (ValueError, TypeError) as exc:
                self.load_warnings.append(f"Invalid connection {src}-{dst}: {exc}")
                continue
            self.graph.add_edge(edge)

        self.lines = self._build_line_sequences()
        self._build_name_index()

    def _build_name_index(self):
        self._name_index = {}
        compact_map = defaultdict(set)
        for name in self.station_to_number:
            norm = normalize_station_name(name)
            self._name_index.setdefault(norm, name)
            compact_map[_compact(norm)].add(name)
        self._compact_index = {
            key: next(iter(names)) for key, names in compact_map.items()
            if len(names) == 1
        }
        self._line_index = {}
        for line in self.all_lines():
            self._line_index[normalize_line_name(line)] = line

    def _build_line_sequences(self):
        """Derive ordered station sequences for each line from connections."""
        adjacency = defaultdict(lambda: defaultdict(list))
        for c in self.connections:
            line = c.get("line", "")
            src, dst = c.get("source"), c.get("dest")
            if src is None or dst is None:
                continue
            adjacency[line][src].append(dst)
            adjacency[line][dst].append(src)
        sequences = {}
        for line, adj in adjacency.items():
            visited = set()
            order = []
            # Prefer starting from terminals (degree 1), then any station.
            starts = [s for s in adj if len(adj[s]) == 1] + list(adj.keys())
            for start in starts:
                if start in visited:
                    continue
                stack = [start]
                while stack:
                    node = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    order.append(node)
                    for nxt in reversed(adj[node]):
                        if nxt not in visited:
                            stack.append(nxt)
            sequences[line] = order
        for st in self.stations:
            for line in st["lines"]:
                sequences.setdefault(line, [])
                if st["name"] not in sequences[line]:
                    sequences[line].append(st["name"])
        return sequences

    # --------------------------------------------------------------- lookup
    def all_lines(self):
        lines = set(self.lines.keys()) if hasattr(self, "lines") else set()
        for names in self.graph.station_lines.values():
            lines.update(names)
        lines.discard("")
        return sorted(lines, key=_line_sort_key)

    def resolve_station(self, name):
        """Return the canonical station name for user input, or None."""
        if name is None:
            return None
        if name in self.station_to_number:
            return name
        norm = normalize_station_name(name)
        if not norm:
            return None
        if norm in self._name_index:
            return self._name_index[norm]
        return self._compact_index.get(_compact(norm))

    def resolve_line(self, name):
        """Return the canonical line name for user input, or None."""
        if name in self._line_index.values():
            return name
        key = normalize_line_name(name)
        if key in self._line_index:
            return self._line_index[key]
        if key.isdigit():
            return self._line_index.get("line" + key) or self._line_index.get(
                key + "号线")
        return None

    # ---------------------------------------------------------------- route
    def plan_route(self, start, end, config=None):
        """Plan a route and compute all summary information.

        :return: dict with query, path, segments, distance, fare, etc.
        :raises RouteError subclasses on failure.
        """
        config = config or PathfindingConfig()
        start_name = self.resolve_station(start)
        if start_name is None:
            raise StationNotFoundError(
                f"Starting station '{start}' does not exist, please check the station name"
            )
        end_name = self.resolve_station(end)
        if end_name is None:
            raise StationNotFoundError(
                f"Ending station '{end}' does not exist, please check the station name"
            )
        if start_name == end_name:
            raise SameStationError(
                "Starting station cannot be the same as the ending station"
            )

        source = self.station_to_number[start_name]
        target = self.station_to_number[end_name]
        try:
            sp = ShortestPath(self.graph, source, config)
        except Exception as exc:  # defensive: report as path error
            raise PathCalculationError(f"Path calculation failed: {exc}") from exc
        if not sp.has_path_to(target):
            if config.max_transfers is not None:
                raise PathCalculationError(
                    f"No route from '{start_name}' to '{end_name}' within "
                    f"{config.max_transfers} transfer(s)"
                )
            raise PathCalculationError(
                f"No route found from '{start_name}' to '{end_name}'"
            )

        nodes, edges = sp.path_with_edges(target)
        names = [self.number_to_station[n] for n in nodes]
        distance = sp.dist_to[target]
        transfer_count = sp.get_transfer_count(target)
        transfer_stations = [self.number_to_station[n]
                             for n in sp.get_transfer_stations(target)]

        segments = []
        for i, edge in enumerate(edges):
            frm, to = names[i], names[i + 1]
            if segments and segments[-1]["line"] == edge.line:
                seg = segments[-1]
                seg["to"] = to
                seg["stations"].append(to)
                seg["stops"] += 1
                seg["distance"] += edge.weight
            else:
                segments.append({"line": edge.line, "from": frm, "to": to,
                                 "stations": [frm, to], "stops": 1,
                                 "distance": edge.weight})
        lines = []
        for seg in segments:
            if seg["line"] not in lines:
                lines.append(seg["line"])

        try:
            fare = Sum_money(distance)
        except (TypeError, ValueError) as exc:
            raise FareError(f"Fare calculation failed: {exc}") from exc
        try:
            est_time = calculate_estimated_time(distance, transfer_count)
        except (TypeError, ValueError):
            est_time = None

        return {
            "query": {
                "start": start_name,
                "end": end_name,
                "mode": config.mode,
                "max_transfers": config.max_transfers,
                "line_preference": list(config.preferred_lines),
            },
            "path": names,
            "station_count": len(names),
            "segments": segments,
            "distance": {"meters": distance,
                         "kilometers": round(distance / 1000.0, 2)},
            "fare": fare,
            "fare_text": f"Fare: {fare} yuan",
            "estimated_time_minutes": est_time,
            "transfer_count": transfer_count,
            "transfer_stations": transfer_stations,
            "lines": lines,
        }

    # ------------------------------------------------------------ integrity
    def check_integrity(self):
        """Run data integrity checks.

        :return: dict with keys ok, errors, warnings, info.
        """
        errors, warnings, info = [], [], []
        names = [st["name"] for st in self.stations]
        defined = set(names)
        seen = set()
        for name in names:
            if name in seen:
                errors.append(f"Duplicate station definition: '{name}'")
            seen.add(name)
        for st in self.stations:
            if not st["lines"]:
                warnings.append(f"Station '{st['name']}' has no line affiliation")

        pair_seen = {}
        connected = set()
        line_has_conn = defaultdict(set)
        for idx, c in enumerate(self.connections):
            src, dst = c.get("source"), c.get("dest")
            line, dist = c.get("line"), c.get("distance")
            label = f"Connection #{idx} ({src} - {dst}, {line})"
            if src not in defined:
                errors.append(f"{label}: source station not defined")
            if dst not in defined:
                errors.append(f"{label}: destination station not defined")
            if src == dst:
                errors.append(f"{label}: connects a station to itself")
            if not line:
                warnings.append(f"{label}: missing line name")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append(f"{label}: distance is not a number ({dist!r})")
            elif dist <= 0:
                errors.append(f"{label}: distance must be positive ({dist})")
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append(f"{label}: suspicious distance {dist} m")
            for name in (src, dst):
                if name in defined and line:
                    lines = self.graph.station_lines.get(name, [])
                    if line not in lines:
                        warnings.append(
                            f"{label}: station '{name}' is not listed on line '{line}'"
                        )
            if src is not None and dst is not None:
                connected.update((src, dst))
                line_has_conn[line].update((src, dst))
                key = (frozenset((src, dst)), line)
                if key in pair_seen:
                    if pair_seen[key] != dist:
                        errors.append(
                            f"{label}: conflicting duplicate distances "
                            f"({pair_seen[key]} vs {dist})")
                    else:
                        warnings.append(f"{label}: duplicate connection")
                else:
                    pair_seen[key] = dist

        for name in names:
            if name not in connected:
                warnings.append(f"Station '{name}' has no connections")
        for st in self.stations:
            for line in st["lines"]:
                if st["name"] in connected and st["name"] not in line_has_conn.get(line, ()):
                    warnings.append(
                        f"Station '{st['name']}' lists line '{line}' but has no "
                        f"connection on that line")

        # Connectivity
        components = self._components()
        if len(components) > 1:
            sizes = sorted((len(c) for c in components), reverse=True)
            warnings.append(
                f"Network has {len(components)} disconnected components (sizes: "
                f"{', '.join(map(str, sizes[:10]))})")

        # Main line coverage
        data_lines = {normalize_line_name(l): l for l in self.all_lines()}
        for main_line, aliases in MAIN_LINES.items():
            keys = {normalize_line_name(main_line)} | {normalize_line_name(a) for a in aliases}
            found = [data_lines[k] for k in keys if k in data_lines]
            if not found:
                warnings.append(f"Main line '{main_line}' not found in data")
                continue
            candidates = REPRESENTATIVE_STATIONS.get(main_line, [])
            if candidates and not any(self.resolve_station(c) for c in candidates):
                warnings.append(
                    f"No representative station found for '{main_line}' "
                    f"(checked: {', '.join(candidates)})")
            else:
                info.append(f"Main line '{main_line}' present as '{found[0]}'")

        for w in self.load_warnings:
            if w not in warnings:
                warnings.append(w)

        info.insert(0, f"Stations: {len(self.station_to_number)}")
        info.insert(1, f"Connections: {len(self.connections)}")
        info.insert(2, f"Lines: {len(self.all_lines())}")
        transfer_count = sum(1 for n in self.station_to_number
                             if self.graph.is_transfer_station(n))
        info.insert(3, f"Transfer stations: {transfer_count}")
        return {"ok": not errors, "errors": errors, "warnings": warnings, "info": info}

    def _components(self):
        seen = set()
        comps = []
        for v in self.graph.vertices():
            if v in seen:
                continue
            comp = []
            queue = deque([v])
            seen.add(v)
            while queue:
                u = queue.popleft()
                comp.append(u)
                for e in self.graph.adjacent(u):
                    w = e.other(u)
                    if w not in seen:
                        seen.add(w)
                        queue.append(w)
            comps.append(comp)
        return comps

    # --------------------------------------------------------------- update
    def _find_station_record(self, name):
        for st in self.stations:
            if st["name"] == name:
                return st
        return None

    def add_station(self, name, lines=None):
        if self._find_station_record(name) is not None:
            raise ValueError(f"Station '{name}' already exists")
        self.stations.append({"name": name, "lines": list(lines or [])})
        self.build()

    def add_line(self, line_name, station_sequence, distances):
        """Add a new line given an ordered station list and segment distances."""
        if len(station_sequence) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("distances must have len(station_sequence) - 1 items")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance {d!r}")
        for name in station_sequence:
            record = self._find_station_record(name)
            if record is None:
                self.stations.append({"name": name, "lines": [line_name]})
            elif line_name not in record["lines"]:
                record["lines"].append(line_name)
        for i, d in enumerate(distances):
            self.connections.append({"source": station_sequence[i],
                                     "dest": station_sequence[i + 1],
                                     "distance": d, "line": line_name})
        self.build()

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        record = self._find_station_record(name)
        if record is None:
            raise ValueError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self._find_station_record(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            record["name"] = new_name
            for c in self.connections:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            record["lines"] = list(lines)
        self.build()

    def update_distance(self, source, dest, distance, line=None):
        """Update distance of connections between two stations.

        :return: number of connections updated.
        """
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) \
                or distance <= 0:
            raise ValueError(f"Invalid distance {distance!r}")
        count = 0
        for c in self.connections:
            if {c.get("source"), c.get("dest")} == {source, dest} and (
                    line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise ValueError(f"No connection between '{source}' and '{dest}'")
        self.build()
        return count

    def to_dict(self):
        return {"stations": [dict(s) for s in self.stations],
                "connections": [dict(c) for c in self.connections]}

    def save(self, path=None):
        save_subway_data(self.to_dict(), path or self.data_path)


def _line_sort_key(name):
    match = re.search(r"\d+", name)
    return (0, int(match.group()), name) if match else (1, 0, name)


def format_integrity_report(report):
    lines = ["Data integrity check", "=" * 50]
    for item in report["info"]:
        lines.append(f"[INFO] {item}")
    for item in report["warnings"]:
        lines.append(f"[WARN] {item}")
    for item in report["errors"]:
        lines.append(f"[ERROR] {item}")
    lines.append("-" * 50)
    lines.append(
        f"Result: {'PASSED' if report['ok'] else 'FAILED'} "
        f"({len(report['errors'])} error(s), {len(report['warnings'])} warning(s))")
    return "\n".join(lines)
