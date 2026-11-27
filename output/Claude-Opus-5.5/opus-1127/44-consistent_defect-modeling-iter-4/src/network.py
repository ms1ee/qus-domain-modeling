"""
SubwayNetwork: data management (stations, lines, connections), graph
construction, route calculation and data integrity checks.
"""

import difflib

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time

MAIN_LINES = ["1", "2", "4", "5", "6", "8", "10", "13", "14", "15",
              "Changping", "Yizhuang", "Fangshan", "Airport"]
MAIN_LINE_ALIASES = {
    "Changping": ["changping", "昌平"],
    "Yizhuang": ["yizhuang", "亦庄"],
    "Fangshan": ["fangshan", "房山"],
    "Airport": ["airport", "机场", "首都机场"],
}


def normalize_name(name):
    if name is None:
        return ""
    name = str(name).strip()
    name = " ".join(name.split())
    return name


class RouteNotFoundError(Exception):
    pass


class SubwayNetwork:
    def __init__(self, data_file=DATA_FILE_PATH, data=None):
        self.data_file = data_file
        if data is None:
            data = load_subway_data(data_file)
        self.data = data
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.build()

    # ------------------------------------------------------------------
    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        lines_of = {}
        for st in self.data.get("stations", []):
            name = normalize_name(st.get("name"))
            if not name:
                continue
            self._number(name)
            lines_of.setdefault(name, [])
            for ln in st.get("lines", []) or []:
                if ln not in lines_of[name]:
                    lines_of[name].append(ln)
        for c in self.data.get("connections", []):
            s = normalize_name(c.get("source"))
            d = normalize_name(c.get("dest"))
            if not s or not d:
                continue
            line = c.get("line")
            for n in (s, d):
                self._number(n)
                lines_of.setdefault(n, [])
                if line and line not in lines_of[n]:
                    lines_of[n].append(line)
            self.graph.add_edge(Edge(self.station_to_number[s], self.station_to_number[d],
                                     c.get("distance", 0), line))
        for name, lines in lines_of.items():
            self.graph.set_station_lines(name, lines)
            self.graph.add_vertex(self.station_to_number[name])

    def _number(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
        return self.station_to_number[name]

    # ------------------------------------------------------------------
    def find_station(self, name):
        """Return the canonical station name, or None if not found."""
        name = normalize_name(name)
        if not name:
            return None
        if name in self.station_to_number:
            return name
        lowered = {k.lower(): k for k in self.station_to_number}
        if name.lower() in lowered:
            return lowered[name.lower()]
        for suffix in ("站", " Station", " station"):
            if name.endswith(suffix):
                base = name[: -len(suffix)].strip()
                if base in self.station_to_number:
                    return base
        return None

    def suggest(self, name, n=3):
        return difflib.get_close_matches(normalize_name(name), list(self.station_to_number), n=n, cutoff=0.5)

    def is_transfer_station(self, name):
        return self.graph.is_transfer_station(name)

    # ------------------------------------------------------------------
    def find_route(self, start, end, config=None):
        """Compute a route; returns a dict describing it."""
        config = config or PathfindingConfig()
        s = self.find_station(start)
        e = self.find_station(end)
        if s is None:
            raise KeyError(f"Starting station '{start}' does not exist, please check the station name")
        if e is None:
            raise KeyError(f"Ending station '{end}' does not exist, please check the station name")
        if s == e:
            raise ValueError("Starting station cannot be the same as the ending station")
        sn, en = self.station_to_number[s], self.station_to_number[e]
        sp = ShortestPath(self.graph, sn, config)
        if not sp.has_path_to(en):
            msg = f"No route found from '{s}' to '{e}'"
            if config.max_transfers is not None:
                msg += f" within {config.max_transfers} transfer(s)"
            raise RouteNotFoundError(msg)
        nums, edges = sp.path_with_edges(en)
        names = [self.number_to_station[n] for n in nums]
        total = sp.dist_to[en]
        transfer_count = sp.get_transfer_count(en)

        segments = []
        transfers = []
        lines = []
        for edge in edges:
            fname = self.number_to_station[edge.source]
            tname = self.number_to_station[edge.dest]
            if edge.line not in lines:
                lines.append(edge.line)
            if segments and segments[-1]["line"] == edge.line:
                seg = segments[-1]
                seg["stations"].append(tname)
                seg["distance"] += edge.weight
            else:
                if segments:
                    transfers.append({"station": fname, "from_line": segments[-1]["line"],
                                      "to_line": edge.line})
                segments.append({"line": edge.line, "stations": [fname, tname],
                                 "distance": edge.weight})
        fare = Sum_money(total)
        est = calculate_estimated_time(total, transfer_count)
        return {
            "start": s,
            "end": e,
            "mode": config.mode,
            "path": names,
            "segments": segments,
            "transfers": transfers,
            "transfer_count": transfer_count,
            "lines": lines,
            "distance": total,
            "fare": fare,
            "estimated_time": est,
        }

    # ------------------------------------------------------------------
    # Data update mechanisms
    def add_line(self, line_name, station_names, distances):
        """Add a new line given ordered stations and inter-station distances."""
        if len(station_names) < 2 or len(distances) != len(station_names) - 1:
            raise ValueError("A line needs >=2 stations and len(distances) == len(stations) - 1")
        existing = {normalize_name(s["name"]): s for s in self.data["stations"]}
        for name in station_names:
            name = normalize_name(name)
            if name in existing:
                if line_name not in existing[name].setdefault("lines", []):
                    existing[name]["lines"].append(line_name)
            else:
                st = {"name": name, "lines": [line_name]}
                self.data["stations"].append(st)
                existing[name] = st
        for a, b, d in zip(station_names, station_names[1:], distances):
            if d <= 0:
                raise ValueError("Distances must be positive")
            self.data["connections"].append({"source": normalize_name(a), "dest": normalize_name(b),
                                             "distance": int(d), "line": line_name})
        self.build()

    def update_station(self, old_name, new_name=None, lines=None):
        old_name = normalize_name(old_name)
        found = False
        for st in self.data["stations"]:
            if normalize_name(st["name"]) == old_name:
                found = True
                if new_name:
                    st["name"] = normalize_name(new_name)
                if lines is not None:
                    st["lines"] = list(lines)
        if not found:
            raise KeyError(f"Station '{old_name}' does not exist")
        if new_name:
            for c in self.data["connections"]:
                if normalize_name(c["source"]) == old_name:
                    c["source"] = normalize_name(new_name)
                if normalize_name(c["dest"]) == old_name:
                    c["dest"] = normalize_name(new_name)
        self.build()

    def update_distance(self, a, b, distance, line=None):
        if distance <= 0:
            raise ValueError("Distance must be positive")
        a, b = normalize_name(a), normalize_name(b)
        count = 0
        for c in self.data["connections"]:
            if {normalize_name(c["source"]), normalize_name(c["dest"])} == {a, b} and \
                    (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        self.build()
        return count

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_file)

    # ------------------------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks; returns a result dict."""
        messages = []
        # Station coverage of main lines
        all_lines = set()
        for st in self.data.get("stations", []):
            all_lines.update(st.get("lines", []) or [])
        for c in self.data.get("connections", []):
            if c.get("line"):
                all_lines.add(c["line"])
        lowered = [str(l).lower() for l in all_lines]
        missing_lines = []
        for ml in MAIN_LINES:
            if ml.isdigit():
                cands = [f"line {ml}", f"{ml}号线"]
                ok = any(l == c or l.startswith(c + " ") or l.startswith(c + "(") for l in lowered for c in cands)
                ok = ok or any(l == ml for l in lowered)
            else:
                aliases = MAIN_LINE_ALIASES.get(ml, [ml.lower()])
                ok = any(a in l for l in lowered for a in aliases)
            if not ok:
                missing_lines.append(ml)
        coverage_ok = bool(self.station_to_number) and not missing_lines
        if missing_lines:
            messages.append("Main lines not covered: " + ", ".join(missing_lines))
        stations_without_lines = [s.get("name") for s in self.data.get("stations", []) if not s.get("lines")]
        if stations_without_lines:
            coverage_ok = False
            messages.append(f"{len(stations_without_lines)} station(s) without line info: "
                            + ", ".join(map(str, stations_without_lines[:10])))

        # Connection integrity
        declared = {normalize_name(s.get("name")) for s in self.data.get("stations", [])}
        conn_ok = True
        for c in self.data.get("connections", []):
            for key in ("source", "dest"):
                if normalize_name(c.get(key)) not in declared:
                    conn_ok = False
                    messages.append(f"Connection references unknown station '{c.get(key)}'")
            if normalize_name(c.get("source")) == normalize_name(c.get("dest")):
                conn_ok = False
                messages.append(f"Self-loop connection at '{c.get('source')}'")
        isolated = [self.number_to_station[v] for v in self.graph.vertices() if not self.graph.adj(v)]
        if isolated:
            conn_ok = False
            messages.append(f"{len(isolated)} isolated station(s): " + ", ".join(isolated[:10]))
        if self.graph.vertex_count:
            first = next(iter(self.graph.vertices()))
            sp = ShortestPath(self.graph, first)
            if len(sp.dist_to) < self.graph.vertex_count:
                conn_ok = False
                messages.append(f"Network is not fully connected: {len(sp.dist_to)}/"
                                f"{self.graph.vertex_count} stations reachable")

        # Distance accuracy
        dist_ok = True
        for c in self.data.get("connections", []):
            d = c.get("distance")
            if not isinstance(d, (int, float)) or isinstance(d, bool) or d <= 0:
                dist_ok = False
                messages.append(f"Invalid distance {d!r} between '{c.get('source')}' and '{c.get('dest')}'")
            elif d > 20000 or d < 100:
                messages.append(f"Warning: unusual distance {d} m between '{c.get('source')}' "
                                f"and '{c.get('dest')}'")
        return {
            "station_count": len(self.station_to_number),
            "connection_count": len(self.data.get("connections", [])),
            "line_count": len(all_lines),
            "station_coverage_valid": coverage_ok,
            "connection_integrity_valid": conn_ok,
            "distance_accuracy_valid": dist_ok,
            "valid": coverage_ok and conn_ok and dist_ok,
            "messages": messages,
        }
