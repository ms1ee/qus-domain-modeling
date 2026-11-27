"""Data integrity checks and data update mechanisms."""

import json
import re

from data_loader import DATA_FILE_PATH

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

_NAMED_ALIASES = {
    "Changping Line": ["changping", "昌平"],
    "Yizhuang Line": ["yizhuang", "亦庄"],
    "Fangshan Line": ["fangshan", "房山"],
    "Airport Line": ["airport", "机场"],
}

# Representative stations of main lines (checked leniently, reported as warnings).
REPRESENTATIVE_STATIONS = [
    "Xidan", "Dongdan", "Xizhimen", "Dongzhimen", "Guomao", "Jianguomen",
    "Fuxingmen", "Beijing Railway Station", "Beijing South Railway Station",
]

MAX_REASONABLE_DISTANCE = 30000


def _line_matches(target, actual):
    a = actual.strip().lower()
    m = re.fullmatch(r"line (\d+)", target.lower())
    if m:
        num = m.group(1)
        return bool(re.match(rf"^line\s*{num}(\b|$)", a)) or a.startswith(f"{num}号线")
    return any(alias in a for alias in _NAMED_ALIASES.get(target, [target.lower()]))


def _norm(name):
    return re.sub(r"[\s'\-]", "", name).lower()


def check_data_integrity(data):
    """Validate coverage, connections and distances.

    :return: dict with ``coverage_valid``, ``connection_valid``,
             ``distance_valid``, ``valid``, ``errors``, ``warnings`` and
             ``stats``.
    """
    errors, warnings = [], []
    stations = data.get("stations", []) or []
    connections = data.get("connections", []) or []

    station_lines = {}
    for st in stations:
        name = st.get("name")
        if not name:
            errors.append("Station entry without a name")
            continue
        if name in station_lines:
            warnings.append(f"Duplicate station entry: {name}")
        station_lines.setdefault(name, set()).update(st.get("lines", []) or [])

    all_lines = set()
    for lines in station_lines.values():
        all_lines.update(lines)
    for c in connections:
        if c.get("line"):
            all_lines.add(c["line"])

    # ----- coverage -----
    coverage_valid = bool(station_lines)
    if not station_lines:
        errors.append("No stations defined")
    for main in MAIN_LINES:
        if not any(_line_matches(main, line) for line in all_lines):
            coverage_valid = False
            errors.append(f"Main line missing from data: {main}")
    normalized = {_norm(n) for n in station_lines}
    for rep in REPRESENTATIVE_STATIONS:
        if _norm(rep) not in normalized:
            warnings.append(f"Representative station not found: {rep}")

    # ----- connections -----
    connection_valid = bool(connections)
    if not connections:
        errors.append("No connections defined")
    adjacency = {name: set() for name in station_lines}
    for i, c in enumerate(connections):
        src, dst, line = c.get("source"), c.get("dest"), c.get("line")
        if not src or not dst:
            connection_valid = False
            errors.append(f"Connection #{i} missing source/dest")
            continue
        if src == dst:
            connection_valid = False
            errors.append(f"Connection #{i} is a self loop at {src}")
        for s in (src, dst):
            if s not in station_lines:
                connection_valid = False
                errors.append(f"Connection #{i} references unknown station '{s}'")
        if line:
            for s in (src, dst):
                if s in station_lines and station_lines[s] and line not in station_lines[s]:
                    warnings.append(f"Station '{s}' is not listed on line '{line}' used by connection #{i}")
        else:
            warnings.append(f"Connection #{i} ({src}-{dst}) has no line")
        adjacency.setdefault(src, set()).add(dst)
        adjacency.setdefault(dst, set()).add(src)

    isolated = [n for n, nb in adjacency.items() if not nb]
    for n in isolated:
        warnings.append(f"Station '{n}' has no connections")
    # connectivity check (ignoring isolated stations)
    nodes = [n for n, nb in adjacency.items() if nb]
    if nodes:
        seen = {nodes[0]}
        stack = [nodes[0]]
        while stack:
            cur = stack.pop()
            for nb in adjacency[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if len(seen) != len(nodes):
            warnings.append(f"Network is not fully connected: {len(nodes) - len(seen)} stations unreachable from '{nodes[0]}'")

    # ----- distances -----
    distance_valid = True
    pair_dist = {}
    for i, c in enumerate(connections):
        d = c.get("distance")
        if isinstance(d, bool) or not isinstance(d, (int, float)):
            distance_valid = False
            errors.append(f"Connection #{i} has invalid distance {d!r}")
            continue
        if d <= 0:
            distance_valid = False
            errors.append(f"Connection #{i} ({c.get('source')}-{c.get('dest')}) has non-positive distance {d}")
        elif d > MAX_REASONABLE_DISTANCE:
            warnings.append(f"Connection #{i} ({c.get('source')}-{c.get('dest')}) has unusually large distance {d} m")
        key = (frozenset((c.get("source"), c.get("dest"))), c.get("line"))
        if key in pair_dist and pair_dist[key] != d:
            distance_valid = False
            errors.append(f"Inconsistent distances for {c.get('source')}-{c.get('dest')} on {c.get('line')}: {pair_dist[key]} vs {d}")
        pair_dist.setdefault(key, d)

    return {
        "coverage_valid": coverage_valid,
        "connection_valid": connection_valid,
        "distance_valid": distance_valid,
        "valid": coverage_valid and connection_valid and distance_valid,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "stations": len(station_lines),
            "connections": len(connections),
            "lines": len(all_lines),
        },
    }


def format_integrity_report(result):
    """Human readable integrity report."""
    ok = lambda b: "PASS" if b else "FAIL"
    lines = [
        "Data integrity check",
        "=" * 40,
        f"Stations: {result['stats']['stations']}, Connections: {result['stats']['connections']}, Lines: {result['stats']['lines']}",
        f"Station coverage check:  {ok(result['coverage_valid'])}",
        f"Connection check:        {ok(result['connection_valid'])}",
        f"Distance data check:     {ok(result['distance_valid'])}",
    ]
    if result["errors"]:
        lines.append("Errors:")
        lines.extend(f"  - {e}" for e in result["errors"])
    if result["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in result["warnings"])
    lines.append(f"Overall: {'PASS' if result['valid'] else 'FAIL'}")
    return "\n".join(lines)


class SubwayDataManager:
    """Update mechanisms for the raw subway data dictionary."""

    def __init__(self, data):
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_station(self, name, lines=None):
        st = self._station(name)
        if st is None:
            st = {"name": name, "lines": []}
            self.data["stations"].append(st)
        for line in lines or []:
            if line not in st["lines"]:
                st["lines"].append(line)
        return st

    def add_line(self, line_name, station_names, distances):
        """Add a new line: ordered stations and len-1 inter-station distances."""
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have exactly len(stations) - 1 entries")
        for d in distances:
            if d <= 0:
                raise ValueError("Distances must be positive")
        for name in station_names:
            self.add_station(name, [line_name])
        for (a, b), d in zip(zip(station_names, station_names[1:]), distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name}
            )

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        st = self._station(name)
        if st is None:
            raise KeyError(f"Station '{name}' does not exist")
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != name:
            if self._station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        return st

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations (both directions)."""
        if distance <= 0:
            raise ValueError("Distance must be positive")
        updated = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {source, dest} and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return updated

    def save(self, path=DATA_FILE_PATH):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
