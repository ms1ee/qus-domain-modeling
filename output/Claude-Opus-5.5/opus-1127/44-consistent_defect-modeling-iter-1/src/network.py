"""Subway network modelling, station lookup, data integrity and updates."""

import difflib

try:
    from data_loader import DATA_FILE_PATH, load_subway_data
    from models import Edge, Graph, Station, Line, DataIntegrityCheck
except ImportError:  # pragma: no cover
    from .data_loader import DATA_FILE_PATH, load_subway_data
    from .models import Edge, Graph, Station, Line, DataIntegrityCheck

MAIN_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8",
              "Line 10", "Line 13", "Line 14", "Line 15", "Changping Line",
              "Yizhuang Line", "Fangshan Line", "Airport Line"]

MAX_REASONABLE_DISTANCE = 30000


def _norm(text):
    return "".join(str(text).lower().split())


class SubwayNetwork:
    """Holds stations, lines, connections and the derived graph."""

    def __init__(self, data=None, data_source=DATA_FILE_PATH):
        self.data_source = data_source
        if data is None:
            data = load_subway_data(data_source)
        self._raw_stations = [dict(s) for s in data.get("stations", [])]
        self.connections = [dict(c) for c in data.get("connections", [])]
        self.rebuild()

    # ------------------------------------------------------------------
    def rebuild(self):
        """(Re)build station mapping, lines and graph from raw data."""
        self.stations = {}
        self.station_to_number = {}
        self.number_to_station = {}
        for s in self._raw_stations:
            name = s.get("name")
            if not name or name in self.stations:
                continue
            self._add_station_internal(name, s.get("lines", []))
        for c in self.connections:
            for key in ("source", "dest"):
                name = c.get(key)
                if name and name not in self.stations:
                    self._add_station_internal(name, [])
                if name and c.get("line") and \
                        c["line"] not in self.stations[name].lines:
                    self.stations[name].lines.append(c["line"])

        self.graph_obj = Graph()
        self.graph = {}  # station number -> list of (neighbor number, distance, line)
        for name, st in self.stations.items():
            self.graph_obj.add_vertex(st.number)
            self.graph_obj.set_station_lines(name, st.lines)
            self.graph[st.number] = []
        for c in self.connections:
            try:
                src = self.station_to_number[c["source"]]
                dst = self.station_to_number[c["dest"]]
                dist = c["distance"]
            except (KeyError, TypeError):
                continue
            if not isinstance(dist, (int, float)) or dist <= 0:
                continue
            self.graph_obj.add_edge(Edge(src, dst, dist, c.get("line")))
            self.graph[src].append((dst, dist, c.get("line")))

        self.lines = {}
        for c in self.connections:
            ln = c.get("line")
            if not ln:
                continue
            line = self.lines.setdefault(ln, Line(ln))
            for key in ("source", "dest"):
                if c.get(key) and c[key] not in line.stations:
                    line.stations.append(c[key])
        for st in self.stations.values():
            for ln in st.lines:
                line = self.lines.setdefault(ln, Line(ln))
                if st.name not in line.stations:
                    line.stations.append(st.name)

    def _add_station_internal(self, name, lines):
        number = len(self.station_to_number)
        st = Station(name, number, list(lines or []))
        self.stations[name] = st
        self.station_to_number[name] = number
        self.number_to_station[number] = name

    # ------------------------------------------------------------------
    def transfer_stations(self):
        return [s.name for s in self.stations.values() if s.is_transfer_station]

    def find_station(self, name):
        """Match a user-entered name to a known station name (or None)."""
        if name is None:
            return None
        name = name.strip()
        if not name:
            return None
        if name in self.stations:
            return name
        n = _norm(name)
        normalized = {_norm(s): s for s in self.stations}
        if n in normalized:
            return normalized[n]
        for suffix in ("station", "站"):
            if n.endswith(suffix) and n[:-len(suffix)] in normalized:
                return normalized[n[:-len(suffix)]]
        subs = [s for k, s in normalized.items() if n in k or (len(k) >= 2 and k in n)]
        if len(subs) == 1:
            return subs[0]
        close = difflib.get_close_matches(n, list(normalized.keys()), n=1, cutoff=0.6)
        if close:
            return normalized[close[0]]
        if subs:
            return sorted(subs, key=len)[0]
        return None

    # ------------------------------------------------------------------
    # Data update mechanisms
    def add_line(self, line_name, station_names, distances):
        """Add a new line: consecutive stations with given distances (meters).

        Connections are added in both directions.
        """
        if len(distances) != max(0, len(station_names) - 1):
            raise ValueError("Need exactly len(stations)-1 distances")
        for name in station_names:
            raw = self._find_raw(name)
            if raw is None:
                self._raw_stations.append({"name": name, "lines": [line_name]})
            elif line_name not in raw.setdefault("lines", []):
                raw["lines"].append(line_name)
        for a, b, d in zip(station_names, station_names[1:], distances):
            if d <= 0:
                raise ValueError("Distance must be positive")
            self.connections.append({"source": a, "dest": b, "distance": d, "line": line_name})
            self.connections.append({"source": b, "dest": a, "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Modify station information (rename and/or set lines)."""
        raw = self._find_raw(name)
        if raw is None and name not in self.stations:
            raise KeyError("Station '%s' does not exist" % name)
        if raw is None:
            raw = {"name": name, "lines": list(self.stations[name].lines)}
            self._raw_stations.append(raw)
        if lines is not None:
            raw["lines"] = list(lines)
        if new_name and new_name != name:
            raw["name"] = new_name
            for c in self.connections:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of existing connection(s) source->dest."""
        if distance <= 0:
            raise ValueError("Distance must be positive")
        found = 0
        for c in self.connections:
            if c.get("source") == source and c.get("dest") == dest and \
                    (line is None or c.get("line") == line):
                c["distance"] = distance
                found += 1
        if not found:
            raise KeyError("Connection %s -> %s not found" % (source, dest))
        self.rebuild()
        return found

    def _find_raw(self, name):
        for s in self._raw_stations:
            if s.get("name") == name:
                return s
        return None

    def to_data(self):
        return {"stations": [{"name": s.name, "lines": list(s.lines)}
                             for s in self.stations.values()],
                "connections": [dict(c) for c in self.connections]}


def check_data_integrity(network):
    """Run data integrity checks and return a DataIntegrityCheck."""
    result = DataIntegrityCheck()
    msgs = result.messages

    # Station coverage of main lines
    known_lines = {_norm(ln) for st in network.stations.values() for ln in st.lines}
    known_lines |= {_norm(ln) for ln in network.lines}
    missing = [ln for ln in MAIN_LINES if _norm(ln) not in known_lines]
    if not network.stations:
        result.station_coverage_valid = False
        msgs.append("No stations found in data")
    if missing:
        result.station_coverage_valid = False
        msgs.append("Main lines missing from data: " + ", ".join(missing))
    else:
        msgs.append("Station coverage: all %d main lines present" % len(MAIN_LINES))
    msgs.append("Total stations: %d, transfer stations: %d"
                % (len(network.stations), len(network.transfer_stations())))

    # Connection integrity
    declared = {s.get("name") for s in network._raw_stations}
    connected = set()
    for i, c in enumerate(network.connections):
        for key in ("source", "dest", "distance", "line"):
            if key not in c:
                result.connection_integrity_valid = False
                msgs.append("Connection #%d missing field '%s'" % (i, key))
        for key in ("source", "dest"):
            if c.get(key) and c[key] not in declared:
                result.connection_integrity_valid = False
                msgs.append("Connection #%d references undeclared station '%s'"
                            % (i, c[key]))
            if c.get(key):
                connected.add(c[key])
        if c.get("source") is not None and c.get("source") == c.get("dest"):
            result.connection_integrity_valid = False
            msgs.append("Connection #%d is a self-loop at '%s'" % (i, c["source"]))
    isolated = [s for s in declared if s and s not in connected]
    if isolated:
        result.connection_integrity_valid = False
        msgs.append("Stations without connections: " + ", ".join(sorted(isolated)))

    # Distance accuracy
    seen = {}
    for i, c in enumerate(network.connections):
        d = c.get("distance")
        if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
            result.distance_accuracy_valid = False
            msgs.append("Connection #%d has invalid distance %r" % (i, d))
            continue
        if d > MAX_REASONABLE_DISTANCE:
            result.distance_accuracy_valid = False
            msgs.append("Connection #%d distance %r exceeds %d m"
                        % (i, d, MAX_REASONABLE_DISTANCE))
        key = (c.get("source"), c.get("dest"), c.get("line"))
        if key in seen and seen[key] != d:
            result.distance_accuracy_valid = False
            msgs.append("Inconsistent distances for %s -> %s (%s): %r vs %r"
                        % (key[0], key[1], key[2], seen[key], d))
        seen[key] = d
    return result
