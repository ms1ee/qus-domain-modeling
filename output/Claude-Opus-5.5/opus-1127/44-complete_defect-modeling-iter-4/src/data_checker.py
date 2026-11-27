"""
Data integrity checks for the subway network data.
"""

from collections import Counter

# Main lines expected (with alternative names).
MAIN_LINES = [
    ("Line 1", "1号线"), ("Line 2", "2号线"), ("Line 4", "4号线", "Line 4/Daxing Line"),
    ("Line 5", "5号线"), ("Line 6", "6号线"), ("Line 8", "8号线"), ("Line 10", "10号线"),
    ("Line 13", "13号线"), ("Line 14", "14号线"), ("Line 15", "15号线"),
    ("Changping Line", "昌平线"), ("Yizhuang Line", "亦庄线"), ("Fangshan Line", "房山线"),
    ("Airport Line", "Capital Airport Express", "Airport Express", "首都机场线", "机场线"),
]

# Representative stations of main lines (with alternative names).
REPRESENTATIVE_STATIONS = [
    ("Xidan", "西单"), ("Dongdan", "东单"), ("Wangfujing", "王府井"),
    ("Xizhimen", "西直门"), ("Dongzhimen", "东直门"), ("Guomao", "国贸"),
    ("Beijing Railway Station", "Beijing Station", "北京站"),
    ("Haidian Huangzhuang", "海淀黄庄"), ("Songjiazhuang", "宋家庄"),
    ("Jianguomen", "建国门"), ("Fuxingmen", "复兴门"), ("Xuanwumen", "宣武门"),
]

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 30000


def _norm(s):
    return " ".join(str(s).split()).casefold()


class DataIntegrityChecker:
    """Checks coverage, connection integrity and distance accuracy."""

    def __init__(self, network, representative_stations=None):
        self.network = network
        self.representative_stations = representative_stations or REPRESENTATIVE_STATIONS
        self.result = None

    def run(self):
        net = self.network
        errors, warnings = [], []
        station_names = set(net.stations)
        norm_stations = {_norm(n) for n in net.station_to_number}
        lines = net.line_names()
        norm_lines = {_norm(l) for l in lines}

        # --- coverage ---------------------------------------------------
        missing_lines = [alts[0] for alts in MAIN_LINES if not any(_norm(a) in norm_lines for a in alts)]
        for ln in missing_lines:
            warnings.append(f"Main line '{ln}' not found in data")
        found_rep, missing_rep = [], []
        for alts in self.representative_stations:
            if any(_norm(a) in norm_stations for a in alts):
                found_rep.append(alts[0])
            else:
                missing_rep.append(alts[0])
        for st in missing_rep:
            warnings.append(f"Representative station '{st}' not found in data")
        if not station_names:
            errors.append("No stations defined")

        # --- connections ------------------------------------------------
        seen = Counter()
        dist_by_key = {}
        degree = Counter()
        for i, c in enumerate(net.connections):
            src, dst, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = f"connection #{i} ({src} - {dst})"
            if not src or not dst:
                errors.append(f"{label}: missing source or destination")
                continue
            for s in (src, dst):
                if s not in station_names:
                    errors.append(f"{label}: station '{s}' is not defined in station list")
            if src == dst:
                errors.append(f"{label}: connects a station to itself")
            if not line:
                errors.append(f"{label}: missing line")
            else:
                for s in (src, dst):
                    if s in net.stations and net.stations[s] and line not in net.stations[s]:
                        warnings.append(f"{label}: station '{s}' is not listed on line '{line}'")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append(f"{label}: distance is not a number")
            elif dist <= 0:
                errors.append(f"{label}: distance must be positive (got {dist})")
            elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
                warnings.append(f"{label}: suspicious distance {dist} m")
            key = (frozenset((src, dst)), line)
            seen[key] += 1
            if seen[key] > 1:
                if dist_by_key.get(key) != dist:
                    errors.append(f"{label}: duplicate connection with inconsistent distance")
                else:
                    warnings.append(f"{label}: duplicate connection")
            dist_by_key.setdefault(key, dist)
            degree[src] += 1
            degree[dst] += 1

        for name in net.stations:
            if not net.stations[name]:
                warnings.append(f"Station '{name}' has no line information")
            if degree[name] == 0:
                warnings.append(f"Station '{name}' has no connections")

        # --- connectivity -----------------------------------------------
        components = self._count_components()
        if components > 1:
            warnings.append(f"Network is split into {components} disconnected components")

        stats = {
            "station_count": len(net.station_to_number),
            "connection_count": len(net.connections),
            "line_count": len(lines),
            "transfer_station_count": len(net.transfer_stations()),
            "representative_stations_found": len(found_rep),
            "representative_stations_total": len(self.representative_stations),
            "components": components,
        }
        self.result = {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}
        return self.result

    def _count_components(self):
        g = self.network.graph
        seen, count = set(), 0
        for v in g.vertices():
            if v in seen:
                continue
            count += 1
            stack = [v]
            seen.add(v)
            while stack:
                u = stack.pop()
                for e in g.adjacent(u):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        stack.append(e.dest)
        return count


def format_check_report(result):
    s = result["stats"]
    lines = [
        "===== Data Integrity Check =====",
        f"Stations: {s['station_count']}",
        f"Connections: {s['connection_count']}",
        f"Lines: {s['line_count']}",
        f"Transfer stations: {s['transfer_station_count']}",
        f"Representative stations found: {s['representative_stations_found']}/"
        f"{s['representative_stations_total']}",
        f"Connected components: {s['components']}",
        f"Errors: {len(result['errors'])}",
    ]
    lines += [f"  [ERROR] {e}" for e in result["errors"]]
    lines.append(f"Warnings: {len(result['warnings'])}")
    lines += [f"  [WARN] {w}" for w in result["warnings"]]
    lines.append("Result: " + ("PASSED" if result["ok"] else "FAILED"))
    return "\n".join(lines)
