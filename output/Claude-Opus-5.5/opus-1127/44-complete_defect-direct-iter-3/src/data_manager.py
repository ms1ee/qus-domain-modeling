"""Subway network data management: graph building, integrity checks, updates."""

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations (English name, Chinese name)
REPRESENTATIVE_STATIONS = [
    ("Xidan", "西单"), ("Tian'anmen East", "天安门东"), ("Guomao", "国贸"),
    ("Dongzhimen", "东直门"), ("Xizhimen", "西直门"), ("Beijing Railway Station", "北京站"),
    ("Zhongguancun", "中关村"), ("Yonghegong", "雍和宫"), ("Sanyuanqiao", "三元桥"),
]

MIN_DISTANCE = 50
MAX_DISTANCE = 40000


def _normalize_line(name):
    s = str(name).lower().replace(" ", "").replace("号线", "").replace("line", "")
    return s


_CN_LINE_ALIASES = {
    "changpingline": "昌平", "yizhuangline": "亦庄", "fangshanline": "房山", "airportline": "机场",
}


class SubwayDataManager:
    """Holds subway data, builds the graph and supports updates/checks."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = None
        self.build()

    # ------------------------------------------------------------------ #
    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        g = Graph()
        for st in self.data.get("stations", []):
            name = st.get("name")
            if not name or name in self.station_to_number:
                continue
            self._assign(name)
            g.add_vertex(self.station_to_number[name])
            g.set_station_lines(name, st.get("lines", []))
        for c in self.data.get("connections", []):
            src, dst = c.get("source"), c.get("dest")
            if not src or not dst:
                continue
            for n in (src, dst):
                if n not in self.station_to_number:
                    self._assign(n)
                    g.add_vertex(self.station_to_number[n])
                    g.set_station_lines(n, [c.get("line")] if c.get("line") else [])
            try:
                dist = int(c.get("distance", 0))
            except (TypeError, ValueError):
                continue
            if dist < 0:
                continue
            g.add_edge(Edge(self.station_to_number[src], self.station_to_number[dst],
                            dist, c.get("line", "")))
        self.graph = g
        return g

    def _assign(self, name):
        num = len(self.station_to_number)
        self.station_to_number[name] = num
        self.number_to_station[num] = name

    # ------------------------------------------------------------------ #
    def lines(self):
        result = []
        for st in self.data.get("stations", []):
            for line in st.get("lines", []):
                if line not in result:
                    result.append(line)
        for c in self.data.get("connections", []):
            if c.get("line") and c["line"] not in result:
                result.append(c["line"])
        return result

    def line_stations(self, line):
        return [st["name"] for st in self.data.get("stations", []) if line in st.get("lines", [])]

    def transfer_stations(self):
        return [st["name"] for st in self.data.get("stations", []) if len(st.get("lines", [])) > 1]

    def find_station(self, name):
        """Return standardized station name or None."""
        if name is None:
            return None
        name = name.strip()
        if name in self.station_to_number:
            return name
        low = name.lower()
        for s in self.station_to_number:
            if s.lower() == low:
                return s
        compact = low.replace(" ", "")
        for s in self.station_to_number:
            if s.lower().replace(" ", "") == compact:
                return s
        return None

    def suggest(self, name, n=3):
        import difflib
        return difflib.get_close_matches(name, list(self.station_to_number), n=n, cutoff=0.6)

    # ------------------------------------------------------------------ #
    def check_integrity(self):
        """Return a report dict with keys: ok, errors, warnings, stats."""
        errors, warnings = [], []
        stations = self.data.get("stations", [])
        conns = self.data.get("connections", [])
        names = set()
        for st in stations:
            name = st.get("name")
            if not name:
                errors.append("Station entry without name")
                continue
            if name in names:
                warnings.append(f"Duplicate station entry: {name}")
            names.add(name)
            if not st.get("lines"):
                warnings.append(f"Station '{name}' has no line information")

        # Coverage of main lines
        all_lines = self.lines()
        norm = [_normalize_line(l) for l in all_lines]
        missing_lines = []
        for ml in MAIN_LINES:
            key = _normalize_line(ml)
            cn = _CN_LINE_ALIASES.get(key)
            found = any(n == key or (cn and cn in n) for n in norm)
            if not found:
                missing_lines.append(ml)
        if missing_lines:
            warnings.append("Main lines not found in data: " + ", ".join(missing_lines))
        missing_rep = [en for en, cn in REPRESENTATIVE_STATIONS if en not in names and cn not in names]
        if missing_rep and len(missing_rep) == len(REPRESENTATIVE_STATIONS):
            warnings.append("No representative stations found in data")
        elif missing_rep:
            warnings.append("Representative stations missing: " + ", ".join(missing_rep))

        # Connection integrity and distance accuracy
        seen = set()
        connected = set()
        for i, c in enumerate(conns):
            src, dst, line = c.get("source"), c.get("dest"), c.get("line")
            if src not in names:
                errors.append(f"Connection #{i}: unknown source station '{src}'")
            if dst not in names:
                errors.append(f"Connection #{i}: unknown dest station '{dst}'")
            if src == dst:
                errors.append(f"Connection #{i}: self loop at '{src}'")
            connected.update([src, dst])
            key = (frozenset((src, dst)), line)
            if key in seen:
                warnings.append(f"Duplicate connection {src} - {dst} ({line})")
            seen.add(key)
            d = c.get("distance")
            if not isinstance(d, (int, float)) or isinstance(d, bool):
                errors.append(f"Connection {src} - {dst}: invalid distance {d!r}")
            elif d <= 0:
                errors.append(f"Connection {src} - {dst}: non-positive distance {d}")
            elif d < MIN_DISTANCE or d > MAX_DISTANCE:
                warnings.append(f"Connection {src} - {dst}: suspicious distance {d} m")
            for n in (src, dst):
                st_lines = self.graph.station_lines.get(n)
                if st_lines and line and line not in st_lines:
                    warnings.append(f"Connection {src} - {dst}: line '{line}' not listed for station '{n}'")
        isolated = sorted(names - connected)
        for n in isolated:
            warnings.append(f"Station '{n}' has no connections")

        # Connectivity
        components = self._component_count()
        if components > 1:
            warnings.append(f"Network has {components} disconnected components")

        stats = {
            "stations": len(names),
            "connections": len(conns),
            "lines": len(all_lines),
            "transfer_stations": len(self.transfer_stations()),
            "components": components,
        }
        return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    def _component_count(self):
        seen = set()
        count = 0
        for v in self.graph.vertices():
            if v in seen:
                continue
            count += 1
            stack = [v]
            seen.add(v)
            while stack:
                u = stack.pop()
                for e in self.graph.adj(u):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        stack.append(e.dest)
        return count

    # ------------------------------------------------------------------ #
    # Update mechanisms
    def add_line(self, line_name, station_names, distances):
        """Add a new line given ordered station names and inter-station distances."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        if any(d <= 0 for d in distances):
            raise ValueError("Distances must be positive")
        by_name = {st["name"]: st for st in self.data["stations"]}
        for name in station_names:
            if name in by_name:
                if line_name not in by_name[name].setdefault("lines", []):
                    by_name[name]["lines"].append(line_name)
            else:
                st = {"name": name, "lines": [line_name]}
                self.data["stations"].append(st)
                by_name[name] = st
        for i, d in enumerate(distances):
            self.data["connections"].append({
                "source": station_names[i], "dest": station_names[i + 1],
                "distance": int(d), "line": line_name,
            })
        self.build()

    def modify_station(self, name, new_name=None, lines=None):
        found = False
        for st in self.data["stations"]:
            if st["name"] == name:
                found = True
                if new_name:
                    st["name"] = new_name
                if lines is not None:
                    st["lines"] = list(lines)
        if not found:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name:
            for c in self.data["connections"]:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name
        self.build()

    def update_distance(self, a, b, distance, line=None):
        if distance <= 0:
            raise ValueError("Distance must be positive")
        updated = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                updated = True
        if not updated:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        self.build()

    def save(self, path=None):
        save_subway_data(self.data, path or self.path)
