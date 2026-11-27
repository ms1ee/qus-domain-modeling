"""
Subway network data management: building the graph, integrity checks and
data update operations.
"""

from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

MAIN_LINES = {
    "Line 1": ["Line 1", "1号线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线", "4号线大兴线", "Line 4 Daxing Line"],
    "Line 5": ["Line 5", "5号线"],
    "Line 6": ["Line 6", "6号线"],
    "Line 8": ["Line 8", "8号线"],
    "Line 10": ["Line 10", "10号线"],
    "Line 13": ["Line 13", "13号线"],
    "Line 14": ["Line 14", "14号线"],
    "Line 15": ["Line 15", "15号线"],
    "Changping Line": ["Changping Line", "昌平线"],
    "Yizhuang Line": ["Yizhuang Line", "亦庄线"],
    "Fangshan Line": ["Fangshan Line", "房山线"],
    "Airport Line": ["Airport Line", "Capital Airport Express", "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = [
    ["Xidan", "西单"],
    ["Guomao", "国贸"],
    ["Xizhimen", "西直门"],
    ["Dongzhimen", "东直门"],
    ["Jianguomen", "建国门"],
    ["Fuxingmen", "复兴门"],
    ["Wangfujing", "王府井"],
    ["Haidian Huangzhuang", "海淀黄庄"],
]

MIN_REASONABLE_DISTANCE = 100       # meters
MAX_REASONABLE_DISTANCE = 30000     # meters


def _norm(text):
    return "".join(str(text).split()).lower()


class SubwayNetwork:
    """Holds subway data and the derived graph structures."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.rebuild()

    # ------------------------------------------------------------------
    def rebuild(self):
        """(Re)build station mappings, graph and line data from raw data."""
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self._name_lookup = {}
        for st in self.data["stations"]:
            name = st.get("name")
            if not name or name in self.station_to_number:
                continue
            num = len(self.station_to_number)
            self.station_to_number[name] = num
            self.number_to_station[num] = name
            self.graph.add_vertex(num)
            self.graph.set_station_lines(name, st.get("lines", []))
            self._name_lookup.setdefault(_norm(name), name)
        for c in self.data["connections"]:
            s = self.station_to_number.get(c.get("source"))
            d = self.station_to_number.get(c.get("dest"))
            dist = c.get("distance")
            if s is None or d is None or not isinstance(dist, (int, float)) or dist < 0:
                continue
            self.graph.add_edge(Edge(s, d, dist, c.get("line")))
        self.lines = self._build_lines()

    def _build_lines(self):
        """Derive line -> ordered station sequence from connections."""
        adj = defaultdict(lambda: defaultdict(set))
        for c in self.data["connections"]:
            line = c.get("line")
            a, b = c.get("source"), c.get("dest")
            if line is None or a is None or b is None:
                continue
            adj[line][a].add(b)
            adj[line][b].add(a)
        lines = {}
        for line, nbrs in adj.items():
            ends = [s for s, n in nbrs.items() if len(n) == 1]
            start = ends[0] if ends else next(iter(nbrs))
            order, visited, cur, prev = [], set(), start, None
            while cur is not None and cur not in visited:
                order.append(cur)
                visited.add(cur)
                nxt = [n for n in sorted(nbrs[cur]) if n != prev and n not in visited]
                prev, cur = cur, (nxt[0] if nxt else None)
            for s in nbrs:  # branches not reachable by simple walk
                if s not in visited:
                    order.append(s)
            lines[line] = order
        # include lines declared on stations but without connections
        for st in self.data["stations"]:
            for ln in st.get("lines", []):
                lines.setdefault(ln, [])
        return lines

    # ------------------------------------------------------------------
    def all_lines(self):
        return sorted(self.lines.keys())

    def resolve_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        name = name.strip()
        if name in self.station_to_number:
            return name
        return self._name_lookup.get(_norm(name))

    def resolve_line(self, name):
        """Resolve a user-supplied line name to an official line name, or None."""
        if not name:
            return None
        key = _norm(name)
        for ln in self.lines:
            if _norm(ln) == key:
                return ln
        for ln in self.lines:
            if _norm(ln) == "line" + key or _norm(ln) == key + "号线":
                return ln
        return None

    def transfer_stations(self):
        return sorted(n for n, ls in self.graph.station_lines.items() if len(ls) > 1)

    # ------------------------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks. Returns dict with errors/warnings/info."""
        errors, warnings, info = [], [], []
        stations = self.data["stations"]
        conns = self.data["connections"]
        info.append(f"Stations: {len(stations)}")
        info.append(f"Connections: {len(conns)}")
        info.append(f"Lines: {len(self.lines)}")
        info.append(f"Transfer stations: {len(self.transfer_stations())}")

        # station records
        seen = set()
        for i, st in enumerate(stations):
            name = st.get("name")
            if not name:
                errors.append(f"Station record #{i} has no name")
                continue
            if name in seen:
                errors.append(f"Duplicate station name: {name}")
            seen.add(name)
            if not st.get("lines"):
                warnings.append(f"Station '{name}' has no line information")

        # coverage of main lines
        norm_lines = {_norm(l) for l in self.lines}
        for main, aliases in MAIN_LINES.items():
            if not any(_norm(a) in norm_lines for a in aliases):
                warnings.append(f"Main line '{main}' not found in data")
        for aliases in REPRESENTATIVE_STATIONS:
            if not any(self.resolve_station(a) for a in aliases):
                warnings.append(f"Representative station '{aliases[0]}' not found in data")

        # connections
        pair_dist = {}
        for i, c in enumerate(conns):
            s, d, line, dist = c.get("source"), c.get("dest"), c.get("line"), c.get("distance")
            label = f"Connection #{i} ({s} - {d}, {line})"
            if s not in self.station_to_number:
                errors.append(f"{label}: unknown source station '{s}'")
            if d not in self.station_to_number:
                errors.append(f"{label}: unknown destination station '{d}'")
            if s == d:
                errors.append(f"{label}: self-loop")
            if not line:
                errors.append(f"{label}: missing line")
            else:
                for st in (s, d):
                    if st in self.graph.station_lines and line not in self.graph.station_lines[st]:
                        warnings.append(f"{label}: station '{st}' is not marked as on line '{line}'")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append(f"{label}: invalid distance {dist!r}")
                continue
            if dist <= 0:
                errors.append(f"{label}: non-positive distance {dist}")
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append(f"{label}: suspicious distance {dist} m")
            key = (frozenset((s, d)), line)
            if key in pair_dist and pair_dist[key] != dist:
                warnings.append(f"{label}: inconsistent duplicate distance "
                                f"({pair_dist[key]} vs {dist})")
            pair_dist[key] = dist

        # connectivity
        isolated = [self.number_to_station[v] for v in self.graph.vertices() if not self.graph.adj(v)]
        for name in isolated:
            warnings.append(f"Station '{name}' has no connections")
        verts = [v for v in self.graph.vertices() if self.graph.adj(v)]
        if verts:
            visited = {verts[0]}
            q = deque([verts[0]])
            while q:
                v = q.popleft()
                for e in self.graph.adj(v):
                    if e.dest not in visited:
                        visited.add(e.dest)
                        q.append(e.dest)
            unreachable = len(verts) - len(visited)
            if unreachable:
                warnings.append(f"Network is not fully connected: {unreachable} stations unreachable")
            else:
                info.append("Network connectivity: OK")
        return {"errors": errors, "warnings": warnings, "info": info, "ok": not errors}

    @staticmethod
    def format_integrity_report(report):
        lines = ["Data integrity check report", "=" * 40]
        for item in report["info"]:
            lines.append(f"[INFO] {item}")
        for item in report["warnings"]:
            lines.append(f"[WARNING] {item}")
        for item in report["errors"]:
            lines.append(f"[ERROR] {item}")
        lines.append("=" * 40)
        lines.append(f"Result: {'PASSED' if report['ok'] else 'FAILED'} "
                     f"({len(report['errors'])} errors, {len(report['warnings'])} warnings)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Data update mechanisms
    def add_line(self, line_name, stations, distances):
        """Add a new line given ordered stations and inter-station distances."""
        if len(stations) < 2 or len(distances) != len(stations) - 1:
            raise ValueError("A line needs >=2 stations and len(stations)-1 distances")
        for dist in distances:
            if not isinstance(dist, (int, float)) or dist <= 0:
                raise ValueError(f"Invalid distance: {dist!r}")
        by_name = {st["name"]: st for st in self.data["stations"]}
        for name in stations:
            if name in by_name:
                ls = by_name[name].setdefault("lines", [])
                if line_name not in ls:
                    ls.append(line_name)
            else:
                rec = {"name": name, "lines": [line_name]}
                self.data["stations"].append(rec)
                by_name[name] = rec
        for i, dist in enumerate(distances):
            self.data["connections"].append({"source": stations[i], "dest": stations[i + 1],
                                             "distance": dist, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or change its line list."""
        rec = next((s for s in self.data["stations"] if s.get("name") == name), None)
        if rec is None:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            rec["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            rec["lines"] = list(lines)
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update distance between two adjacent stations. Returns count updated."""
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Invalid distance: {distance!r}")
        count = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        self.rebuild()
        return count

    def save(self, path=None):
        save_subway_data(self.data, path or self.path)
