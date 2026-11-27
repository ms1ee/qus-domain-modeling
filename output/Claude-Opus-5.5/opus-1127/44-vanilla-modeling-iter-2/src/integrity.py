"""
Data integrity checks of the subway network data.
"""

import re

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

_NAMED_LINE_KEYWORDS = {
    "Changping Line": ("changping", "昌平"),
    "Yizhuang Line": ("yizhuang", "亦庄"),
    "Fangshan Line": ("fangshan", "房山"),
    "Airport Line": ("airport", "机场"),
}

#: Representative stations (official English names) of the main lines.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "Wangfujing", "Guomao"],
    "Line 2": ["Xizhimen", "Dongzhimen", "Beijing Railway Station"],
    "Line 4": ["Zhongguancun", "Xidan", "Beijing South Railway Station"],
    "Line 5": ["Dongdan", "Yonghegong Lama Temple", "Songjiazhuang"],
    "Line 6": ["Chaoyangmen", "Ping'anli"],
    "Line 8": ["Gulou Dajie", "Olympic Green"],
    "Line 10": ["Guomao", "Sanyuanqiao", "Haidian Huangzhuang"],
    "Line 13": ["Xizhimen", "Huilongguan", "Dongzhimen"],
    "Line 14": ["Wangjing", "Jintai Lu"],
    "Line 15": ["Wangjing", "Olympic Green"],
    "Changping Line": ["Xi'erqi"],
    "Yizhuang Line": ["Songjiazhuang"],
    "Fangshan Line": ["Guogongzhuang"],
    "Airport Line": ["Sanyuanqiao", "Dongzhimen"],
}

MAX_REASONABLE_DISTANCE = 30000
MIN_TYPICAL_DISTANCE = 300


def line_matches(required, actual):
    """Lenient comparison between a required main line and an actual line name."""
    a = str(actual).strip().lower()
    m = re.fullmatch(r"line (\d+)", required.lower())
    if m:
        n = m.group(1)
        return bool(re.match(rf"^line\s*{n}(?!\d)", a) or re.match(rf"^{n}\s*号线", a) or a == n)
    return any(k in a for k in _NAMED_LINE_KEYWORDS.get(required, (required.lower(),)))


def _key(name):
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", str(name).lower())


class DataIntegrityCheck:
    def __init__(self, network):
        self.network = network
        self.station_coverage_valid = False
        self.connection_integrity_valid = False
        self.distance_accuracy_valid = False
        self.errors = []
        self.warnings = []
        self.info = []

    @property
    def is_valid(self):
        return self.station_coverage_valid and self.connection_integrity_valid and self.distance_accuracy_valid

    def run(self):
        self.errors, self.warnings, self.info = [], [], []
        self.station_coverage_valid = self._check_coverage()
        self.connection_integrity_valid = self._check_connections()
        self.distance_accuracy_valid = self._check_distances()
        return self

    # ----------------------------------------------------------- coverage
    def _check_coverage(self):
        net = self.network
        ok = True
        if not net.station_to_number:
            self.errors.append("No stations found in data")
            return False
        self.info.append(f"Stations: {len(net.station_to_number)}, lines: {len(net.lines)}, "
                         f"transfer stations: {len(net.transfer_stations())}")
        station_keys = {_key(n) for n in net.station_to_number}
        for required in MAIN_LINES:
            matches = [l for l in net.lines if line_matches(required, l)]
            if not matches:
                self.errors.append(f"Main line '{required}' is missing")
                ok = False
                continue
            count = sum(len(net.lines[l]) for l in matches)
            if count < 2:
                self.errors.append(f"Main line '{required}' has fewer than 2 stations")
                ok = False
            else:
                self.info.append(f"Main line '{required}' found ({', '.join(matches)}; {count} stations)")
            for rep in REPRESENTATIVE_STATIONS.get(required, []):
                if _key(rep) not in station_keys:
                    self.warnings.append(f"Representative station '{rep}' of '{required}' not found")
        return ok

    # -------------------------------------------------------- connections
    def _check_connections(self):
        net = self.network
        ok = True
        stations = set(net.station_to_number)
        declared = set()
        for st in net.data.get("stations", []):
            if isinstance(st, dict) and str(st.get("name", "")).strip():
                declared.add(str(st["name"]).strip())
        connected = set()
        for i, conn in enumerate(net.data.get("connections", [])):
            if not isinstance(conn, dict):
                self.errors.append(f"Connection #{i} is not an object")
                ok = False
                continue
            s = str(conn.get("source", "")).strip()
            d = str(conn.get("dest", "")).strip()
            line = conn.get("line")
            if not s or not d:
                self.errors.append(f"Connection #{i} has an empty endpoint")
                ok = False
                continue
            if s == d:
                self.errors.append(f"Connection #{i} links '{s}' to itself")
                ok = False
            for n in (s, d):
                if n not in declared:
                    self.errors.append(f"Connection #{i} references undeclared station '{n}'")
                    ok = False
                elif line and line not in self._declared_lines(n):
                    self.warnings.append(f"Station '{n}' is not declared on line '{line}' (connection #{i})")
            if not line:
                self.warnings.append(f"Connection #{i} ({s} - {d}) has no line")
            connected.update((s, d))
        isolated = sorted(stations - connected)
        for n in isolated:
            self.errors.append(f"Station '{n}' has no connections")
            ok = False
        # graph connectivity
        if net.station_to_number:
            start = next(iter(net.station_to_number.values()))
            seen = {start}
            stack = [start]
            while stack:
                v = stack.pop()
                for e in net.graph.adj(v):
                    w = e.other(v)
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            unreachable = len(net.station_to_number) - len(seen)
            if unreachable:
                self.errors.append(f"Network is not connected: {unreachable} station(s) unreachable")
                ok = False
        return ok

    def _declared_lines(self, name):
        for st in self.network.data.get("stations", []):
            if isinstance(st, dict) and str(st.get("name", "")).strip() == name:
                return st.get("lines", []) or []
        return []

    # ---------------------------------------------------------- distances
    def _check_distances(self):
        ok = True
        seen = {}
        for i, conn in enumerate(self.network.data.get("connections", [])):
            if not isinstance(conn, dict):
                continue
            dist = conn.get("distance")
            s = str(conn.get("source", "")).strip()
            d = str(conn.get("dest", "")).strip()
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                self.errors.append(f"Connection #{i} ({s} - {d}) has invalid distance {dist!r}")
                ok = False
                continue
            if dist <= 0:
                self.errors.append(f"Connection #{i} ({s} - {d}) has non-positive distance {dist}")
                ok = False
                continue
            if dist > MAX_REASONABLE_DISTANCE:
                self.errors.append(f"Connection #{i} ({s} - {d}) has unrealistic distance {dist} m")
                ok = False
            elif dist < MIN_TYPICAL_DISTANCE:
                self.warnings.append(f"Connection #{i} ({s} - {d}) has unusually short distance {dist} m")
            key = (frozenset((s, d)), conn.get("line"))
            if key in seen and seen[key] != dist:
                self.errors.append(f"Inconsistent distances for {s} - {d} on {conn.get('line')}: "
                                   f"{seen[key]} vs {dist}")
                ok = False
            seen.setdefault(key, dist)
        return ok

    # ------------------------------------------------------------- report
    def format_report(self):
        def mark(flag):
            return "PASS" if flag else "FAIL"
        out = ["Data integrity check report", "=" * 40]
        out.append(f"Station coverage:      {mark(self.station_coverage_valid)}")
        out.append(f"Connection integrity:  {mark(self.connection_integrity_valid)}")
        out.append(f"Distance accuracy:     {mark(self.distance_accuracy_valid)}")
        out.append("-" * 40)
        for msg in self.info:
            out.append(f"[INFO] {msg}")
        for msg in self.warnings:
            out.append(f"[WARN] {msg}")
        for msg in self.errors:
            out.append(f"[ERROR] {msg}")
        out.append("=" * 40)
        out.append("Overall: " + ("VALID" if self.is_valid else "INVALID"))
        return "\n".join(out)
