"""
SubwayNetwork: data management (stations, connections, lines) on top of
the raw JSON data, including data update mechanisms.
"""

import difflib
import json
import re

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data


def _normalize(name):
    return re.sub(r"\s+", " ", str(name).strip()).casefold()


def _natural_key(s):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", str(s))]


class SubwayNetwork:
    """The Beijing Subway network, modelled as a weighted graph."""

    def __init__(self, data=None, data_source=DATA_FILE_PATH):
        self.data_source = data_source
        if data is None:
            data = load_subway_data(data_source)
        self.stations = {}  # name -> list of lines (ordered)
        for st in data.get("stations", []):
            name = st.get("name")
            if name:
                self.stations.setdefault(name, [])
                for ln in st.get("lines") or []:
                    if ln not in self.stations[name]:
                        self.stations[name].append(ln)
        self.connections = [dict(c) for c in data.get("connections", [])]
        self.rebuild()

    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "stations": [{"name": n, "lines": list(l)} for n, l in self.stations.items()],
            "connections": [dict(c) for c in self.connections],
        }

    def rebuild(self):
        """(Re)build the graph and station mapping from current data."""
        self.graph, self.station_to_number, self.number_to_station = build_graph(self.to_dict())
        self._normalized = {_normalize(n): n for n in self.station_to_number}

    def save(self, path=None):
        path = path or self.data_source
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    def resolve_station(self, name):
        """Return the official station name for user input, or None."""
        if name is None:
            return None
        name = str(name).strip()
        if name in self.station_to_number:
            return name
        return self._normalized.get(_normalize(name))

    def suggest_stations(self, name, n=3):
        return difflib.get_close_matches(str(name).strip(), list(self.station_to_number), n=n, cutoff=0.6)

    def station_number(self, name):
        return self.station_to_number[name]

    def station_name(self, number):
        return self.number_to_station[number]

    def lines_of(self, station_name):
        return list(self.graph.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return self.graph.is_transfer_station(station_name)

    def transfer_stations(self):
        return [n for n in self.number_to_station if self.is_transfer_station(n)]

    def line_names(self):
        names = set()
        for lines in self.stations.values():
            names.update(lines)
        for c in self.connections:
            if c.get("line"):
                names.add(c["line"])
        return sorted(names, key=_natural_key)

    def resolve_line(self, name):
        if not name:
            return None
        name = str(name).strip()
        lines = self.line_names()
        if name in lines:
            return name
        norm = _normalize(name)
        for ln in lines:
            if _normalize(ln) == norm:
                return ln
        if name.isdigit():
            for cand in (f"Line {name}", f"{name}号线"):
                if cand in lines:
                    return cand
        return None

    def get_line_sequence(self, line):
        """Return the ordered station sequence of a line (best effort)."""
        adj = {}
        for c in self.connections:
            if c.get("line") != line:
                continue
            adj.setdefault(c["source"], [])
            adj.setdefault(c["dest"], [])
            if c["dest"] not in adj[c["source"]]:
                adj[c["source"]].append(c["dest"])
            if c["source"] not in adj[c["dest"]]:
                adj[c["dest"]].append(c["source"])
        if not adj:
            return [n for n, ls in self.stations.items() if line in ls]
        ends = [n for n, nb in adj.items() if len(nb) == 1]
        start = ends[0] if ends else next(iter(adj))
        seq, seen, stack = [], set(), [start]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            seq.append(v)
            for w in reversed(adj[v]):
                if w not in seen:
                    stack.append(w)
        return seq

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_sequence, distances):
        """Add a new line given its station sequence and segment distances (m)."""
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if len(station_sequence) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("Number of distances must be number of stations - 1")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in station_sequence:
            lines = self.stations.setdefault(name, [])
            if line_name not in lines:
                lines.append(line_name)
        for a, b, d in zip(station_sequence, station_sequence[1:], distances):
            self.connections.append({"source": a, "dest": b, "distance": int(d), "line": line_name})
        self.rebuild()

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        if name not in self.stations:
            raise KeyError(f"Station '{name}' does not exist")
        if new_name and new_name != name:
            if new_name in self.stations:
                raise ValueError(f"Station '{new_name}' already exists")
            self.stations = {(new_name if k == name else k): v for k, v in self.stations.items()}
            for c in self.connections:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
            name = new_name
        if lines is not None:
            self.stations[name] = list(dict.fromkeys(lines))
        self.rebuild()

    def update_distance(self, station_a, station_b, distance, line=None):
        """Update the distance between two adjacent stations."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        updated = 0
        for c in self.connections:
            pair = {c.get("source"), c.get("dest")}
            if pair == {station_a, station_b} and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{station_a}' and '{station_b}'")
        self.rebuild()
        return updated
