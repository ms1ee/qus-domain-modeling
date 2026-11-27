"""Subway network data management: graph construction, station lookup,
data integrity checks and data update mechanisms."""

import json
import re
import unicodedata
from collections import deque

from models import Edge, Graph

MAIN_LINES = {
    "Line 1": ["Line 1", "1号线", "Line 1/Batong Line", "1号线/八通线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线", "Line 4/Daxing Line", "4号线/大兴线"],
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
    "Airport Line": ["Airport Line", "Capital Airport Line", "首都机场线", "机场线"],
}

REPRESENTATIVE_STATIONS = [
    ("Xidan", "西单"),
    ("Dongzhimen", "东直门"),
    ("Xizhimen", "西直门"),
    ("Guomao", "国贸"),
    ("Sanyuanqiao", "三元桥"),
    ("Zhongguancun", "中关村"),
    ("Songjiazhuang", "宋家庄"),
    ("Beijing Railway Station", "北京站"),
    ("Dongdan", "东单"),
    ("Jianguomen", "建国门"),
]

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 40000
MAX_VALID_DISTANCE = 100000


def normalize_name(name):
    """Normalized key used for tolerant station/line name matching."""
    if not isinstance(name, str):
        return ""
    text = unicodedata.normalize("NFKC", name).strip().casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    text = re.sub(r"\s+", "", text)
    for suffix in ("subwaystation", "station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    return text


class SubwayNetwork:
    """Holds the raw data plus derived graph and station mappings."""

    def __init__(self, data):
        self.data = {
            "stations": [dict(s) for s in data.get("stations", [])],
            "connections": [dict(c) for c in data.get("connections", [])],
        }
        self.rebuild()

    # ------------------------------------------------------------ building
    def rebuild(self):
        """(Re)build the graph and lookup structures from ``self.data``."""
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        declared_lines = {}

        for station in self.data["stations"]:
            name = station.get("name")
            if not isinstance(name, str) or not name:
                continue
            if name not in self.station_to_number:
                number = len(self.station_to_number)
                self.station_to_number[name] = number
                self.number_to_station[number] = name
                declared_lines[name] = []
            declared_lines[name].extend(station.get("lines") or [])

        connection_lines = {}
        for conn in self.data["connections"]:
            for key in ("source", "dest"):
                name = conn.get(key)
                if not isinstance(name, str) or not name:
                    continue
                if name not in self.station_to_number:
                    number = len(self.station_to_number)
                    self.station_to_number[name] = number
                    self.number_to_station[number] = name
                    declared_lines.setdefault(name, [])
                connection_lines.setdefault(name, []).append(conn.get("line"))

        for name, number in self.station_to_number.items():
            self.graph.add_vertex(number)
            lines = declared_lines.get(name) or [l for l in connection_lines.get(name, []) if l]
            self.graph.set_station_lines(name, lines)

        for conn in self.data["connections"]:
            src, dst = conn.get("source"), conn.get("dest")
            dist = conn.get("distance")
            if src not in self.station_to_number or dst not in self.station_to_number:
                continue
            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
                continue
            self.graph.add_edge(Edge(self.station_to_number[src], self.station_to_number[dst],
                                     dist, conn.get("line")))

        self._alias = {}
        for name in self.station_to_number:
            self._alias.setdefault(normalize_name(name), name)
        self._line_alias = {}
        for line in self.all_lines():
            self._line_alias.setdefault(normalize_name(line), line)

    # ------------------------------------------------------------- lookups
    def all_lines(self):
        return self.graph.all_lines()

    def resolve_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if not isinstance(name, str):
            return None
        stripped = name.strip()
        if stripped in self.station_to_number:
            return stripped
        return self._alias.get(normalize_name(stripped))

    def resolve_line(self, line):
        if not isinstance(line, str):
            return None
        if line.strip() in self._line_alias.values():
            return line.strip()
        key = normalize_name(line)
        if key in self._line_alias:
            return self._line_alias[key]
        alt = normalize_name("Line " + line.strip())
        return self._line_alias.get(alt)

    def station_name(self, number):
        return self.number_to_station[number]

    def station_number(self, name):
        return self.station_to_number[name]

    def is_transfer_station(self, name):
        return self.graph.is_transfer_station(name)

    def stations_on_line(self, line):
        return [n for n, lines in self.graph.station_lines.items() if line in lines]

    # ------------------------------------------------------------- updates
    def _ensure_station(self, name, line=None):
        for station in self.data["stations"]:
            if station.get("name") == name:
                lines = station.setdefault("lines", [])
                if line and line not in lines:
                    lines.append(line)
                return
        self.data["stations"].append({"name": name, "lines": [line] if line else []})

    def add_station(self, name, lines=None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Station name must be a non-empty string")
        name = name.strip()
        if name in self.station_to_number:
            raise ValueError("Station '%s' already exists" % name)
        self.data["stations"].append({"name": name, "lines": list(lines or [])})
        self.rebuild()

    def add_line(self, line_name, stations, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if not isinstance(line_name, str) or not line_name.strip():
            raise ValueError("Line name must be a non-empty string")
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in stations:
            self._ensure_station(name, line_name)
        for (a, b), d in zip(zip(stations, stations[1:]), distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        official = self.resolve_station(name)
        if official is None:
            raise KeyError("Station '%s' does not exist" % name)
        if new_name is not None:
            new_name = new_name.strip()
            if not new_name:
                raise ValueError("New station name cannot be empty")
            if new_name != official and new_name in self.station_to_number:
                raise ValueError("Station '%s' already exists" % new_name)
        for station in self.data["stations"]:
            if station.get("name") == official:
                if new_name:
                    station["name"] = new_name
                if lines is not None:
                    station["lines"] = list(lines)
        if new_name:
            for conn in self.data["connections"]:
                if conn.get("source") == official:
                    conn["source"] = new_name
                if conn.get("dest") == official:
                    conn["dest"] = new_name
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations.

        If no connection exists and ``line`` is given, a new one is added.
        Returns the number of connections updated/added.
        """
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        a, b = self.resolve_station(source), self.resolve_station(dest)
        if a is None:
            raise KeyError("Station '%s' does not exist" % source)
        if b is None:
            raise KeyError("Station '%s' does not exist" % dest)
        count = 0
        for conn in self.data["connections"]:
            if {conn.get("source"), conn.get("dest")} == {a, b} and (line is None or conn.get("line") == line):
                conn["distance"] = distance
                count += 1
        if count == 0:
            if line is None:
                raise KeyError("No connection between '%s' and '%s'" % (a, b))
            self._ensure_station(a, line)
            self._ensure_station(b, line)
            self.data["connections"].append({"source": a, "dest": b, "distance": distance, "line": line})
            count = 1
        self.rebuild()
        return count

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    # ----------------------------------------------------- integrity check
    def check_integrity(self):
        """Run data integrity checks; returns a report dict."""
        errors, warnings = [], []
        declared = {}
        for i, station in enumerate(self.data["stations"]):
            name = station.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append("Station #%d has an invalid name" % i)
                continue
            if name in declared:
                warnings.append("Duplicate station entry: '%s'" % name)
            lines = station.get("lines")
            if not isinstance(lines, list) or not lines:
                warnings.append("Station '%s' has no line information" % name)
            declared[name] = set(lines or [])

        seen_pairs = set()
        connected = set()
        for i, conn in enumerate(self.data["connections"]):
            src, dst, dist, line = conn.get("source"), conn.get("dest"), conn.get("distance"), conn.get("line")
            label = "Connection #%d (%s - %s)" % (i, src, dst)
            if src not in declared:
                errors.append("%s: unknown source station '%s'" % (label, src))
            if dst not in declared:
                errors.append("%s: unknown destination station '%s'" % (label, dst))
            if src == dst:
                errors.append("%s: connects a station to itself" % label)
            if not line:
                errors.append("%s: missing line name" % label)
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append("%s: distance is not a number" % label)
            elif dist <= 0 or dist > MAX_VALID_DISTANCE:
                errors.append("%s: invalid distance %s m" % (label, dist))
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append("%s: unusual distance %s m" % (label, dist))
            if src in declared and line and line not in declared[src]:
                warnings.append("%s: station '%s' is not declared on %s" % (label, src, line))
            if dst in declared and line and line not in declared[dst]:
                warnings.append("%s: station '%s' is not declared on %s" % (label, dst, line))
            key = (frozenset((src, dst)), line)
            if key in seen_pairs:
                warnings.append("%s: duplicate connection on %s" % (label, line))
            seen_pairs.add(key)
            connected.add(src)
            connected.add(dst)

        for name in declared:
            if name not in connected:
                warnings.append("Station '%s' has no connections" % name)

        # Connectivity
        components = self._count_components()
        if components > 1:
            warnings.append("Network is not fully connected (%d components)" % components)

        # Coverage of main lines
        line_keys = {normalize_name(l) for l in self.all_lines()}
        missing_lines = []
        for main, aliases in MAIN_LINES.items():
            if not any(normalize_name(a) in line_keys for a in aliases):
                missing_lines.append(main)
        if missing_lines:
            warnings.append("Main lines not found: %s" % ", ".join(missing_lines))
        missing_stations = []
        for names in REPRESENTATIVE_STATIONS:
            if not any(self.resolve_station(n) for n in names):
                missing_stations.append(names[0])
        if missing_stations:
            warnings.append("Representative stations not found: %s" % ", ".join(missing_stations))

        stats = {
            "stations": len(self.station_to_number),
            "connections": len(self.data["connections"]),
            "lines": len(self.all_lines()),
            "transfer_stations": sum(1 for n in self.graph.station_lines if self.graph.is_transfer_station(n)),
            "components": components,
            "main_lines_covered": len(MAIN_LINES) - len(missing_lines),
            "main_lines_total": len(MAIN_LINES),
        }
        return {"valid": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    def _count_components(self):
        seen = set()
        components = 0
        for v in self.graph.vertices():
            if v in seen:
                continue
            components += 1
            queue = deque([v])
            seen.add(v)
            while queue:
                u = queue.popleft()
                for e in self.graph.adj(u):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        queue.append(e.dest)
        return components


def format_integrity_report(report):
    lines = ["Data integrity check report", "=" * 30]
    stats = report["stats"]
    lines.append("Stations: %d" % stats["stations"])
    lines.append("Connections: %d" % stats["connections"])
    lines.append("Lines: %d" % stats["lines"])
    lines.append("Transfer stations: %d" % stats["transfer_stations"])
    lines.append("Connected components: %d" % stats["components"])
    lines.append("Main lines covered: %d/%d" % (stats["main_lines_covered"], stats["main_lines_total"]))
    lines.append("Errors: %d" % len(report["errors"]))
    for err in report["errors"]:
        lines.append("  [ERROR] " + err)
    lines.append("Warnings: %d" % len(report["warnings"]))
    for warn in report["warnings"]:
        lines.append("  [WARNING] " + warn)
    lines.append("Result: %s" % ("PASSED" if report["valid"] else "FAILED"))
    return "\n".join(lines)
