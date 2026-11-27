"""
Subway network data management: modelling, querying, updating and checking.
"""

import difflib
import re
from collections import deque

try:
    from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
    from models import Edge, Graph, Line, Route, Transfer
    from pathfinding import ShortestPath, PathfindingConfig
    from fare_calculator import Sum_money, calculate_estimated_time
except ImportError:  # pragma: no cover - package-style import
    from .data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
    from .models import Edge, Graph, Line, Route, Transfer
    from .pathfinding import ShortestPath, PathfindingConfig
    from .fare_calculator import Sum_money, calculate_estimated_time


def _normalize_name(name):
    n = str(name).strip().casefold()
    n = re.sub(r"[\s'’`\-_.·]", "", n)
    if n.endswith("station") and len(n) > len("station"):
        n = n[: -len("station")]
    if n.endswith("站") and len(n) > 1:
        n = n[:-1]
    return n


class SubwayNetwork:
    """Holds stations, connections, lines and the graph model of the network."""

    def __init__(self, data_file=DATA_FILE_PATH, data=None):
        self.data_source_file = data_file
        if data is None:
            data = load_subway_data(data_file)
        self.stations = [dict(s) for s in data.get("stations", [])]
        self.connections = [dict(c) for c in data.get("connections", [])]
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        station_lines = {}

        def register(name):
            if name not in self.station_to_number:
                num = len(self.station_to_number)
                self.station_to_number[name] = num
                self.number_to_station[num] = name
                station_lines[name] = []

        for st in self.stations:
            name = st.get("name")
            if not name:
                continue
            register(name)
            for ln in st.get("lines", []) or []:
                if ln not in station_lines[name]:
                    station_lines[name].append(ln)

        for c in self.connections:
            for key in ("source", "dest"):
                name = c.get(key)
                if not name:
                    continue
                register(name)
                ln = c.get("line")
                if ln and ln not in station_lines[name]:
                    station_lines[name].append(ln)

        self.station_lines = station_lines
        self.graph = {name: [] for name in self.station_to_number}
        self.network_graph = Graph()
        for name, num in self.station_to_number.items():
            self.network_graph.add_station(name, num, station_lines[name])

        for c in self.connections:
            s, d = c.get("source"), c.get("dest")
            dist = c.get("distance")
            if not s or not d or s == d:
                continue
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
                continue
            line = c.get("line")
            self.network_graph.add_edge(Edge(self.station_to_number[s], self.station_to_number[d], dist, line))
            self.graph[s].append({"station": d, "distance": dist, "line": line})
            self.graph[d].append({"station": s, "distance": dist, "line": line})

        self._normalized = {}
        for name in self.station_to_number:
            self._normalized.setdefault(_normalize_name(name), name)

    # ---- queries -----------------------------------------------------
    def station_names(self):
        return list(self.station_to_number.keys())

    def line_names(self):
        names = []
        for lines in self.station_lines.values():
            for ln in lines:
                if ln not in names:
                    names.append(ln)
        return names

    def transfer_stations(self):
        return [n for n, lines in self.station_lines.items() if len(lines) > 1]

    def resolve_station(self, name):
        """Return the official station name matching the input, or None."""
        if name is None:
            return None
        n = str(name).strip()
        if n in self.station_to_number:
            return n
        return self._normalized.get(_normalize_name(n))

    def suggest_stations(self, name, n=3):
        return difflib.get_close_matches(str(name).strip(), self.station_names(), n=n, cutoff=0.6)

    def get_line_stations(self, line):
        """Ordered station sequence of a line, derived from its connections."""
        adj = {}
        order = []
        for c in self.connections:
            if c.get("line") != line:
                continue
            s, d = c.get("source"), c.get("dest")
            for a, b in ((s, d), (d, s)):
                if a not in adj:
                    adj[a] = []
                    order.append(a)
                if b not in adj[a]:
                    adj[a].append(b)
        if not adj:
            return [n for n, lines in self.station_lines.items() if line in lines]
        start = next((n for n in order if len(adj[n]) == 1), order[0])
        result, visited = [], set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            result.append(node)
            for nb in reversed(adj[node]):
                if nb not in visited:
                    stack.append(nb)
        for n in order:
            if n not in visited:
                result.append(n)
        return result

    def get_lines(self):
        lines = []
        for ln in self.line_names():
            seq = self.get_line_stations(ln)
            transfers = [s for s in seq if len(self.station_lines.get(s, [])) > 1]
            lines.append(Line(ln, seq, ", ".join(transfers)))
        return lines

    # ---- route finding ------------------------------------------------
    def find_route(self, start, end, config=None):
        """Compute a Route between two (official) station names, or None."""
        config = config or PathfindingConfig()
        if start not in self.station_to_number:
            raise KeyError(f"Unknown station: {start}")
        if end not in self.station_to_number:
            raise KeyError(f"Unknown station: {end}")
        sp = ShortestPath(self.network_graph, self.station_to_number[start], config)
        target = self.station_to_number[end]
        nodes, edges = sp.path_with_edges(target)
        if not nodes:
            return None
        names = [self.number_to_station[n] for n in nodes]

        segments = []
        for e in edges:
            a, b = self.number_to_station[e.source], self.number_to_station[e.dest]
            if segments and segments[-1]["line"] == e.line:
                seg = segments[-1]
                seg["stations"].append(b)
                seg["distance"] += e.weight
            else:
                segments.append({"line": e.line, "stations": [a, b], "distance": e.weight})

        transfers = []
        for prev, nxt in zip(segments, segments[1:]):
            transfers.append(Transfer(prev["stations"][-1], prev["line"], nxt["line"]))

        involved = []
        for seg in segments:
            if seg["line"] is not None and seg["line"] not in involved:
                involved.append(seg["line"])

        total = sum(e.weight for e in edges)
        if isinstance(total, float) and total.is_integer():
            total = int(total)
        transfer_count = len(transfers)
        return Route(
            start=start,
            end=end,
            station_sequence=names,
            total_distance_meters=total,
            transfer_count=transfer_count,
            estimated_time=calculate_estimated_time(total, transfer_count),
            involved_lines=involved,
            transfers=transfers,
            segments=segments,
            fare=Sum_money(total),
            mode=config.mode,
        )

    # ---- data update mechanisms ---------------------------------------
    def add_line(self, line_name, station_sequence, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if len(station_sequence) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("distances must have exactly len(stations) - 1 items")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        existing = {s["name"]: s for s in self.stations}
        for name in station_sequence:
            if name in existing:
                lines = existing[name].setdefault("lines", [])
                if line_name not in lines:
                    lines.append(line_name)
            else:
                st = {"name": name, "lines": [line_name]}
                self.stations.append(st)
                existing[name] = st
        for a, b, d in zip(station_sequence, station_sequence[1:], distances):
            self.connections.append({"source": a, "dest": b, "distance": d, "line": line_name})
        self._build()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station: {name}")
        if new_name and new_name != name and new_name in self.station_to_number:
            raise ValueError(f"Station '{new_name}' already exists")
        found = False
        for st in self.stations:
            if st.get("name") == name:
                found = True
                if new_name:
                    st["name"] = new_name
                if lines is not None:
                    st["lines"] = list(lines)
        if not found:
            self.stations.append({"name": new_name or name, "lines": list(lines or self.station_lines[name])})
        if new_name:
            for c in self.connections:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        self._build()

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance of the connection between two adjacent stations."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        updated = 0
        for c in self.connections:
            if {c.get("source"), c.get("dest")} == {station_a, station_b} and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{station_a}' and '{station_b}'")
        self._build()
        return updated

    def to_dict(self):
        return {"stations": self.stations, "connections": self.connections}

    def save(self, path=None):
        save_subway_data(self.to_dict(), path or self.data_source_file)


# ----------------------------------------------------------------------
MAIN_LINES = {
    "Line 1": ["Line 1", "1号线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线"],
    "Line 5": ["Line 5", "5号线"],
    "Line 6": ["Line 6", "6号线"],
    "Line 8": ["Line 8", "8号线"],
    "Line 10": ["Line 10", "10号线"],
    "Line 13": ["Line 13", "13号线"],
    "Line 14": ["Line 14", "14号线"],
    "Line 15": ["Line 15", "15号线"],
    "Changping Line": ["Changping Line", "Changping", "昌平线"],
    "Yizhuang Line": ["Yizhuang Line", "Yizhuang", "亦庄线"],
    "Fangshan Line": ["Fangshan Line", "Fangshan", "房山线"],
    "Airport Line": ["Airport Line", "Capital Airport Line", "Airport Express", "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "西单"],
    "Line 2": ["Xizhimen", "西直门"],
    "Line 4": ["Zhongguancun", "中关村"],
    "Line 5": ["Dongdan", "东单"],
    "Line 6": ["Chaoyangmen", "朝阳门"],
    "Line 8": ["Gulou Dajie", "鼓楼大街"],
    "Line 10": ["Guomao", "国贸"],
    "Line 13": ["Xierqi", "Xi'erqi", "西二旗"],
    "Line 14": ["Wangjing", "望京"],
    "Line 15": ["Wangjing", "望京"],
    "Changping Line": ["Nanshao", "南邵"],
    "Yizhuang Line": ["Songjiazhuang", "宋家庄"],
    "Fangshan Line": ["Guogongzhuang", "郭公庄"],
    "Airport Line": ["Dongzhimen", "东直门"],
}

MAX_REASONABLE_DISTANCE = 30000
WARN_DISTANCE = 20000
MIN_REASONABLE_DISTANCE = 100


def _line_matches(main_alias, data_line):
    a, b = _normalize_name(main_alias), _normalize_name(data_line)
    if a == b:
        return True
    return b.startswith(a) and not b[len(a):len(a) + 1].isdigit()


class DataIntegrityChecker:
    """Checks coverage, connection integrity and distance accuracy of the data."""

    def __init__(self, network, representative_stations=None):
        self.network = network
        self.representative_stations = representative_stations or REPRESENTATIVE_STATIONS
        self.result = None
        self.errors = []
        self.warnings = []
        self.info = []

    def run(self):
        self.errors, self.warnings, self.info = [], [], []
        self._check_coverage()
        self._check_connections()
        self._check_distances()
        self._check_connectivity()
        self.result = not self.errors
        return self.result

    def _check_coverage(self):
        net = self.network
        data_lines = net.line_names()
        self.info.append(f"Stations: {len(net.station_to_number)}, connections: {len(net.connections)}, "
                         f"lines: {len(data_lines)}, transfer stations: {len(net.transfer_stations())}")
        for main, aliases in MAIN_LINES.items():
            if not any(_line_matches(a, dl) for a in aliases for dl in data_lines):
                self.warnings.append(f"Main line '{main}' not found in data")
        for line, candidates in self.representative_stations.items():
            if not any(net.resolve_station(c) for c in candidates):
                self.warnings.append(f"Representative station of {line} ({candidates[0]}) not found")
        declared = {s.get("name") for s in net.stations}
        if not net.stations:
            self.errors.append("No station data present")
        for s in net.stations:
            if not s.get("name"):
                self.errors.append("Station entry without a name")
            elif not s.get("lines"):
                self.warnings.append(f"Station '{s.get('name')}' has no line information")
        names = [s.get("name") for s in net.stations]
        dups = {n for n in names if names.count(n) > 1}
        for d in sorted(x for x in dups if x):
            self.warnings.append(f"Duplicate station entry '{d}'")
        self._declared = declared

    def _check_connections(self):
        net = self.network
        declared = self._declared
        seen = {}
        connected = set()
        for i, c in enumerate(net.connections):
            s, d, line = c.get("source"), c.get("dest"), c.get("line")
            if not s or not d:
                self.errors.append(f"Connection #{i} is missing source or destination")
                continue
            if s == d:
                self.errors.append(f"Connection #{i} connects '{s}' to itself")
            for name in (s, d):
                if name not in declared:
                    self.errors.append(f"Connection #{i} references undeclared station '{name}'")
            if not line:
                self.warnings.append(f"Connection {s} - {d} has no line")
            else:
                for name in (s, d):
                    st = next((x for x in net.stations if x.get("name") == name), None)
                    if st and line not in (st.get("lines") or []):
                        self.warnings.append(f"Station '{name}' is not declared on {line} but has a {line} connection")
            key = (frozenset((s, d)), line)
            dist = c.get("distance")
            if key in seen and seen[key] != dist:
                self.errors.append(f"Conflicting distances for {s} - {d} on {line}: {seen[key]} vs {dist}")
            seen[key] = dist
            connected.update((s, d))
        for name in declared:
            if name and name not in connected:
                self.warnings.append(f"Station '{name}' has no connections")

    def _check_distances(self):
        for c in self.network.connections:
            dist = c.get("distance")
            label = f"{c.get('source')} - {c.get('dest')}"
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                self.errors.append(f"Distance of {label} is not a number")
            elif dist <= 0:
                self.errors.append(f"Distance of {label} must be positive (got {dist})")
            elif dist > MAX_REASONABLE_DISTANCE:
                self.errors.append(f"Distance of {label} is unrealistically large ({dist} m)")
            elif dist > WARN_DISTANCE:
                self.warnings.append(f"Distance of {label} is unusually large ({dist} m)")
            elif dist < MIN_REASONABLE_DISTANCE:
                self.warnings.append(f"Distance of {label} is unusually small ({dist} m)")

    def _check_connectivity(self):
        graph = self.network.graph
        if not graph:
            return
        start = next(iter(graph))
        seen = {start}
        q = deque([start])
        while q:
            n = q.popleft()
            for nb in graph[n]:
                if nb["station"] not in seen:
                    seen.add(nb["station"])
                    q.append(nb["station"])
        unreachable = [n for n in graph if n not in seen]
        if unreachable:
            sample = ", ".join(unreachable[:10])
            self.warnings.append(f"{len(unreachable)} station(s) not connected to the main network: {sample}")

    def format_report(self):
        if self.result is None:
            self.run()
        lines = ["=== Data Integrity Check ==="]
        lines += [f"[INFO] {m}" for m in self.info]
        lines += [f"[ERROR] {m}" for m in self.errors]
        lines += [f"[WARNING] {m}" for m in self.warnings]
        lines.append(f"Result: {'PASSED' if self.result else 'FAILED'} "
                     f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))")
        return "\n".join(lines)
