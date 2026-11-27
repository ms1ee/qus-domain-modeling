"""Subway network data management: graph building, integrity checks, updates."""

import re
import unicodedata
from collections import defaultdict, deque

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph
from pathfinding import normalize_line_name

REQUIRED_LINES = [
    ["Line 1", "1号线"], ["Line 2", "2号线"], ["Line 4", "4号线"], ["Line 5", "5号线"],
    ["Line 6", "6号线"], ["Line 8", "8号线"], ["Line 10", "10号线"], ["Line 13", "13号线"],
    ["Line 14", "14号线"], ["Line 15", "15号线"], ["Changping Line", "昌平线"],
    ["Yizhuang Line", "亦庄线"], ["Fangshan Line", "房山线"],
    ["Airport Line", "Capital Airport Express", "Airport Express", "首都机场线", "机场线"],
]

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "西单", "Tiananmen East", "Tian'anmen East", "天安门东", "Guomao", "国贸"],
    "Line 2": ["Xizhimen", "西直门", "Dongzhimen", "东直门", "Beijing Railway Station", "北京站"],
    "Line 4": ["Xidan", "西单", "Beijing South Railway Station", "北京南站", "Zhongguancun", "中关村"],
    "Line 5": ["Dongdan", "东单", "Yonghegong", "Yonghegong Lama Temple", "雍和宫"],
    "Line 10": ["Guomao", "国贸", "Haidian Huangzhuang", "海淀黄庄"],
    "Line 13": ["Xizhimen", "西直门", "Shangdi", "上地"],
}


def normalize_station_key(name):
    """Normalise a station name for lenient lookup."""
    if name is None:
        return ""
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    text = re.sub(r"\s+", " ", text)
    if text.endswith(" station") and not text.endswith("railway station"):
        text = text[: -len(" station")]
    if text.endswith("站") and len(text) > 1 and not text.endswith("南站") and not text.endswith("西站") \
            and not text.endswith("北站") and not text.endswith("东站") and text != "北京站":
        text = text[:-1]
    text = re.sub(r"[\s'’`\-]", "", text)
    return text


class SubwayNetwork:
    """Holds subway data and the graph built from it."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.invalid_connections = []
        self._lookup = {}
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.invalid_connections = []
        lines_map = defaultdict(list)

        for st in self.data["stations"]:
            name = st.get("name")
            if not name or name in self.station_to_number:
                continue
            num = len(self.station_to_number)
            self.station_to_number[name] = num
            self.number_to_station[num] = name
            lines_map[name].extend(st.get("lines", []) or [])
            self.graph.add_vertex(num)

        for conn in self.data["connections"]:
            src, dst = conn.get("source"), conn.get("dest")
            dist, line = conn.get("distance"), conn.get("line")
            if src not in self.station_to_number or dst not in self.station_to_number:
                self.invalid_connections.append((conn, "unknown station"))
                continue
            if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
                self.invalid_connections.append((conn, "invalid distance"))
                continue
            if src == dst:
                self.invalid_connections.append((conn, "self loop"))
                continue
            self.graph.add_edge(Edge(self.station_to_number[src], self.station_to_number[dst], dist, line))
            if line and line not in lines_map[src]:
                lines_map[src].append(line)
            if line and line not in lines_map[dst]:
                lines_map[dst].append(line)

        for name in self.station_to_number:
            self.graph.set_station_lines(name, lines_map[name])

        self._lookup = {}
        for name in self.station_to_number:
            self._lookup.setdefault(name, name)
        for name in self.station_to_number:
            self._lookup.setdefault(normalize_station_key(name), name)

    # ------------------------------------------------------------------
    @property
    def station_lines(self):
        return self.graph.station_lines

    def resolve_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name is None:
            return None
        raw = str(name).strip()
        if raw in self.station_to_number:
            return raw
        return self._lookup.get(normalize_station_key(raw))

    def all_lines(self):
        lines = []
        for ls in self.graph.station_lines.values():
            for l in ls:
                if l not in lines:
                    lines.append(l)
        return lines

    def resolve_line(self, line):
        key = normalize_line_name(line)
        for l in self.all_lines():
            if normalize_line_name(l) == key:
                return l
        return None

    def transfer_stations(self):
        return [n for n, ls in self.graph.station_lines.items() if len(ls) > 1]

    def get_line_stations(self, line):
        """Return the station sequence of a line (derived from connections)."""
        adj = defaultdict(list)
        for conn in self.data["connections"]:
            if conn.get("line") != line:
                continue
            s, d = conn.get("source"), conn.get("dest")
            if s in self.station_to_number and d in self.station_to_number:
                if d not in adj[s]:
                    adj[s].append(d)
                if s not in adj[d]:
                    adj[d].append(s)
        if not adj:
            return []
        ends = [s for s in adj if len(adj[s]) == 1]
        order_key = lambda n: self.station_to_number[n]
        start = min(ends, key=order_key) if ends else min(adj, key=order_key)
        result, seen, stack = [], set(), [start]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            result.append(cur)
            for nxt in reversed(adj[cur]):
                if nxt not in seen:
                    stack.append(nxt)
        for s in adj:
            if s not in seen:
                result.append(s)
        return result

    def line_info(self):
        return {line: {"stations": self.get_line_stations(line),
                       "transfer_stations": [s for s in self.get_line_stations(line)
                                             if len(self.graph.station_lines.get(s, [])) > 1]}
                for line in self.all_lines()}

    # ------------------------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks. Returns dict with ok/errors/warnings/stats."""
        errors, warnings = [], []
        names = [st.get("name") for st in self.data["stations"]]
        seen = set()
        for n in names:
            if not n:
                errors.append("Station entry without a name")
            elif n in seen:
                errors.append(f"Duplicate station name: {n}")
            seen.add(n)

        for conn, reason in self.invalid_connections:
            errors.append(f"Invalid connection {conn.get('source')} - {conn.get('dest')} "
                          f"({conn.get('line')}): {reason}")

        pair_dist = {}
        for conn in self.data["connections"]:
            s, d, dist, line = conn.get("source"), conn.get("dest"), conn.get("distance"), conn.get("line")
            if not line:
                warnings.append(f"Connection {s} - {d} has no line")
            key = (frozenset((s, d)), line)
            if key in pair_dist and pair_dist[key] != dist:
                errors.append(f"Conflicting distances for {s} - {d} on {line}: {pair_dist[key]} vs {dist}")
            pair_dist[key] = dist
            if isinstance(dist, (int, float)) and not isinstance(dist, bool) and dist > 0:
                if dist < 300:
                    warnings.append(f"Suspiciously short distance {dist} m between {s} and {d}")
                elif dist > 30000:
                    warnings.append(f"Suspiciously long distance {dist} m between {s} and {d}")
            if s in self.station_to_number and line:
                declared = next((st.get("lines", []) for st in self.data["stations"]
                                 if st.get("name") == s), [])
                if declared and line not in declared:
                    warnings.append(f"Station {s} is not declared on {line}")

        for name, num in self.station_to_number.items():
            if not self.graph.adj(num):
                warnings.append(f"Station {name} has no connections")

        # connectivity
        components = 0
        visited = set()
        for v in self.graph.vertices():
            if v in visited or not self.graph.adj(v):
                continue
            components += 1
            q = deque([v])
            visited.add(v)
            while q:
                u = q.popleft()
                for e in self.graph.adj(u):
                    w = e.other(u)
                    if w not in visited:
                        visited.add(w)
                        q.append(w)
        if components > 1:
            warnings.append(f"Network is split into {components} disconnected components")

        # coverage
        present = {normalize_line_name(l) for l in self.all_lines()}
        for aliases in REQUIRED_LINES:
            if not any(normalize_line_name(a) in present for a in aliases):
                warnings.append(f"Main line missing from data: {aliases[0]}")
        for line, candidates in REPRESENTATIVE_STATIONS.items():
            if not any(self.resolve_station(c) for c in candidates):
                warnings.append(f"No representative station found for {line}")

        stats = {
            "stations": len(self.station_to_number),
            "connections": self.graph.E(),
            "lines": len(self.all_lines()),
            "transfer_stations": len(self.transfer_stations()),
        }
        return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    # ------------------------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if not line_name:
            raise ValueError("Line name required")
        if len(stations) < 2 or len(distances) != len(stations) - 1:
            raise ValueError("Need at least two stations and len(distances) == len(stations) - 1")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        index = {st["name"]: st for st in self.data["stations"]}
        for name in stations:
            if name in index:
                if line_name not in index[name].setdefault("lines", []):
                    index[name]["lines"].append(line_name)
            else:
                entry = {"name": name, "lines": [line_name]}
                self.data["stations"].append(entry)
                index[name] = entry
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self._build()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        entry = next((st for st in self.data["stations"] if st.get("name") == name), None)
        if entry is None:
            raise KeyError(f"Station {name!r} does not exist")
        if new_name and new_name != name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station {new_name!r} already exists")
            entry["name"] = new_name
            for conn in self.data["connections"]:
                if conn.get("source") == name:
                    conn["source"] = new_name
                if conn.get("dest") == name:
                    conn["dest"] = new_name
        if lines is not None:
            entry["lines"] = list(lines)
        self._build()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of an existing connection. Returns count updated."""
        if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        count = 0
        for conn in self.data["connections"]:
            if {conn.get("source"), conn.get("dest")} == {source, dest} and \
                    (line is None or conn.get("line") == line):
                conn["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between {source!r} and {dest!r}")
        self._build()
        return count

    def save(self, path=None):
        save_subway_data(self.data, path or self.path)
