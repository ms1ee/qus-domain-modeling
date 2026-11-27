"""
Subway network model: station numbering, graph construction, route
computation, data integrity checks and data update mechanisms.
"""

import difflib
from collections import OrderedDict, deque

try:
    from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
    from models import Edge, Graph, Route, TransferDetail, Station, Line
    from pathfinding import ShortestPath, PathfindingConfig, INF
    from fare_calculator import Sum_money, calculate_estimated_time
except ImportError:  # pragma: no cover
    from .data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
    from .models import Edge, Graph, Route, TransferDetail, Station, Line
    from .pathfinding import ShortestPath, PathfindingConfig, INF
    from .fare_calculator import Sum_money, calculate_estimated_time


class StationNotFoundError(Exception):
    pass


class RouteNotFoundError(Exception):
    pass


# Main lines expected in the network (with name aliases).
MAIN_LINES = [
    ["Line 1", "1号线"], ["Line 2", "2号线"], ["Line 4", "4号线", "4号线大兴线"],
    ["Line 5", "5号线"], ["Line 6", "6号线"], ["Line 8", "8号线"],
    ["Line 10", "10号线"], ["Line 13", "13号线"], ["Line 14", "14号线"],
    ["Line 15", "15号线"], ["Changping Line", "昌平线"], ["Yizhuang Line", "亦庄线"],
    ["Fangshan Line", "房山线"], ["Airport Line", "Airport Express", "首都机场线", "机场线"],
]

MIN_REASONABLE_DISTANCE = 100      # meters
MAX_REASONABLE_DISTANCE = 50000    # meters


class SubwayNetwork:
    """Beijing subway network built from subway_data.json."""

    def __init__(self, data_source=DATA_FILE_PATH, data=None):
        self.data_source = data_source
        self.data = data if data is not None else load_subway_data(data_source)
        self._build()

    # ---- construction ----------------------------------------------
    def _build(self):
        self.station_to_number = OrderedDict()
        self.number_to_station = {}
        self.station_lines = {}
        for st in self.data.get("stations", []):
            name = st["name"]
            if name not in self.station_to_number:
                n = len(self.station_to_number)
                self.station_to_number[name] = n
                self.number_to_station[n] = name
            self.station_lines[name] = list(st.get("lines", []))
        for c in self.data.get("connections", []):
            for name in (c["source"], c["dest"]):
                if name not in self.station_to_number:
                    n = len(self.station_to_number)
                    self.station_to_number[name] = n
                    self.number_to_station[n] = name
                    self.station_lines.setdefault(name, [])
        self.graph_obj = Graph()
        self.graph = {}  # number -> list of (neighbor, distance, line)
        for name, n in self.station_to_number.items():
            self.graph_obj.add_vertex(n)
            self.graph_obj.set_station_lines(name, self.station_lines.get(name, []))
            self.graph[n] = []
        for c in self.data.get("connections", []):
            s = self.station_to_number[c["source"]]
            d = self.station_to_number[c["dest"]]
            self.graph_obj.add_edge(Edge(s, d, c["distance"], c.get("line")))
            self.graph[s].append((d, c["distance"], c.get("line")))

    @property
    def stations(self):
        return [Station(name, n, self.station_lines.get(name, []))
                for name, n in self.station_to_number.items()]

    @property
    def lines(self):
        """Line name -> Line with station sequence (connection order)."""
        result = OrderedDict()
        for c in self.data.get("connections", []):
            ln = c.get("line")
            if ln is None:
                continue
            seq = result.setdefault(ln, Line(ln, [])).station_sequence
            for name in (c["source"], c["dest"]):
                if name not in seq:
                    seq.append(name)
        for name, lns in self.station_lines.items():
            for ln in lns:
                seq = result.setdefault(ln, Line(ln, [])).station_sequence
                if name not in seq:
                    seq.append(name)
        return result

    def transfer_stations(self):
        return [n for n, l in self.station_lines.items() if len(l) > 1]

    # ---- station lookup --------------------------------------------
    def find_station(self, name):
        """Return the matching official station name or None.

        Unknown names are matched to the nearest known station when possible.
        """
        if name is None:
            return None
        name = name.strip()
        if not name:
            return None
        if name in self.station_to_number:
            return name
        lowered = {s.lower(): s for s in self.station_to_number}
        candidates = [name, name.rstrip("站"), name.replace(" Station", "").replace(" station", "")]
        for cand in candidates:
            cand = cand.strip()
            if cand in self.station_to_number:
                return cand
            if cand.lower() in lowered:
                return lowered[cand.lower()]
        matches = difflib.get_close_matches(name, list(self.station_to_number), n=1, cutoff=0.6)
        if matches:
            return matches[0]
        lower_matches = difflib.get_close_matches(name.lower(), list(lowered), n=1, cutoff=0.6)
        if lower_matches:
            return lowered[lower_matches[0]]
        contained = [s for s in self.station_to_number if name in s or (len(s) > 1 and s in name)]
        if contained:
            return min(contained, key=lambda s: abs(len(s) - len(name)))
        return None

    # ---- routing ---------------------------------------------------
    def compute_route(self, start_name, end_name, config=None):
        config = config or PathfindingConfig()
        if start_name not in self.station_to_number:
            raise StationNotFoundError(f"Starting station '{start_name}' does not exist, please check the station name")
        if end_name not in self.station_to_number:
            raise StationNotFoundError(f"Ending station '{end_name}' does not exist, please check the station name")
        s = self.station_to_number[start_name]
        e = self.station_to_number[end_name]
        sp = ShortestPath(self.graph_obj, s, config)
        if sp.dist_to.get(e, INF) == INF:
            raise RouteNotFoundError(f"No route found from '{start_name}' to '{end_name}'")
        nodes, edges = sp.path_with_edges(e)
        names = [self.number_to_station[n] for n in nodes]
        distance = int(round(sp.dist_to[e]))
        segments = []
        transfers = []
        involved = []
        for edge in edges:
            src = self.number_to_station[edge.source]
            dst = self.number_to_station[edge.dest]
            if segments and segments[-1]["line"] == edge.line:
                segments[-1]["stations"].append(dst)
                segments[-1]["distance"] += edge.distance
            else:
                if segments:
                    transfers.append(TransferDetail(src, segments[-1]["line"], edge.line))
                segments.append({"line": edge.line, "stations": [src, dst], "distance": edge.distance})
            if edge.line is not None and edge.line not in involved:
                involved.append(edge.line)
        transfer_count = len(transfers)
        return Route(
            start=start_name, end=end_name, station_sequence=names,
            total_distance=distance, transfer_count=transfer_count,
            estimated_time=calculate_estimated_time(distance, transfer_count),
            involved_lines=involved, transfers=transfers, segments=segments,
            fare=Sum_money(distance), mode=config.mode,
        )

    # ---- integrity checks ------------------------------------------
    def check_integrity(self):
        """Run data integrity checks; returns a dict of results and messages."""
        messages = []
        # station coverage
        all_lines = set()
        for lns in self.station_lines.values():
            all_lines.update(lns)
        for c in self.data.get("connections", []):
            if c.get("line"):
                all_lines.add(c["line"])
        missing = [aliases[0] for aliases in MAIN_LINES if not any(a in all_lines for a in aliases)]
        coverage_ok = not missing and len(self.station_to_number) > 0
        if missing:
            messages.append("Missing main lines: " + ", ".join(missing))
        if not self.station_to_number:
            messages.append("No stations defined")

        # connection integrity
        conn_ok = True
        declared = {st["name"] for st in self.data.get("stations", [])}
        for c in self.data.get("connections", []):
            for key in ("source", "dest"):
                if c.get(key) not in declared:
                    conn_ok = False
                    messages.append(f"Connection references unknown station '{c.get(key)}'")
            if c.get("source") == c.get("dest"):
                conn_ok = False
                messages.append(f"Self-loop connection at '{c.get('source')}'")
            ln = c.get("line")
            for key in ("source", "dest"):
                lns = self.station_lines.get(c.get(key), [])
                if ln and lns and ln not in lns:
                    messages.append(f"Warning: station '{c.get(key)}' not declared on line '{ln}'")
        isolated = [n for n, num in self.station_to_number.items()
                    if not self.graph.get(num) and not any(num == d for lst in self.graph.values() for d, _, _ in lst)]
        if isolated:
            conn_ok = False
            messages.append("Isolated stations: " + ", ".join(isolated[:20]))
        # connectivity (undirected view)
        if self.station_to_number:
            und = {n: set() for n in self.graph}
            for s, lst in self.graph.items():
                for d, _, _ in lst:
                    und[s].add(d)
                    und[d].add(s)
            start = next(iter(und))
            seen = {start}
            dq = deque([start])
            while dq:
                v = dq.popleft()
                for w in und[v]:
                    if w not in seen:
                        seen.add(w)
                        dq.append(w)
            if len(seen) != len(und):
                messages.append(f"Warning: network is not fully connected ({len(und) - len(seen)} stations unreachable)")

        # distance accuracy
        dist_ok = True
        pairs = {}
        for c in self.data.get("connections", []):
            d = c.get("distance")
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                dist_ok = False
                messages.append(f"Invalid distance {d!r} between '{c.get('source')}' and '{c.get('dest')}'")
                continue
            if d < MIN_REASONABLE_DISTANCE or d > MAX_REASONABLE_DISTANCE:
                messages.append(f"Warning: unusual distance {d}m between '{c.get('source')}' and '{c.get('dest')}'")
            pairs[(c.get("source"), c.get("dest"), c.get("line"))] = d
        for (s, t, ln), d in pairs.items():
            rev = pairs.get((t, s, ln))
            if rev is not None and rev != d:
                messages.append(f"Warning: asymmetric distance {s}<->{t} on {ln}: {d} vs {rev}")

        return {
            "station_coverage_valid": coverage_ok,
            "connection_integrity_valid": conn_ok,
            "distance_accuracy_valid": dist_ok,
            "station_count": len(self.station_to_number),
            "connection_count": len(self.data.get("connections", [])),
            "line_count": len(all_lines),
            "messages": messages,
            "valid": coverage_ok and conn_ok and dist_ok,
        }

    # ---- data updates ----------------------------------------------
    def _station_entry(self, name):
        for st in self.data["stations"]:
            if st["name"] == name:
                return st
        return None

    def add_line(self, line_name, station_names, distances, bidirectional=True):
        if len(station_names) < 2 or len(distances) != len(station_names) - 1:
            raise ValueError("A line needs >= 2 stations and len(distances) == len(stations) - 1")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in station_names:
            st = self._station_entry(name)
            if st is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in st.setdefault("lines", []):
                st["lines"].append(line_name)
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
            if bidirectional:
                self.data["connections"].append({"source": b, "dest": a, "distance": d, "line": line_name})
        self._build()

    def modify_station(self, name, new_name=None, lines=None):
        st = self._station_entry(name)
        if st is None:
            raise StationNotFoundError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if self._station_entry(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            st["name"] = new_name
            for c in self.data["connections"]:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)
        self._build()

    def update_distance(self, source, dest, distance, line=None, bidirectional=True):
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        for name in (source, dest):
            if name not in self.station_to_number:
                raise StationNotFoundError(f"Station '{name}' does not exist")
        pairs = [(source, dest)] + ([(dest, source)] if bidirectional else [])
        updated = False
        for c in self.data["connections"]:
            if (c["source"], c["dest"]) in pairs and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated = True
        if not updated:
            if line is None:
                common = set(self.station_lines.get(source, [])) & set(self.station_lines.get(dest, []))
                line = sorted(common)[0] if common else None
            for a, b in pairs:
                self.data["connections"].append({"source": a, "dest": b, "distance": distance, "line": line})
        self._build()

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_source)
