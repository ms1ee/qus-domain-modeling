"""Data integrity checking for the subway network data."""

MAIN_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8",
              "Line 10", "Line 13", "Line 14", "Line 15", "Changping Line",
              "Yizhuang Line", "Fangshan Line", "Airport Line"]

_CN = {"Line 1": "1号线", "Line 2": "2号线", "Line 4": "4号线", "Line 5": "5号线",
       "Line 6": "6号线", "Line 8": "8号线", "Line 10": "10号线",
       "Line 13": "13号线", "Line 14": "14号线", "Line 15": "15号线",
       "Changping Line": "昌平线", "Yizhuang Line": "亦庄线",
       "Fangshan Line": "房山线", "Airport Line": "首都机场线"}

MAX_REASONABLE_DISTANCE = 50000


def _norm(s):
    return "".join(str(s).split()).lower()


class DataIntegrityChecker:
    """Checks station coverage, connection integrity and distance accuracy."""

    def __init__(self, data):
        self.data = data
        self.station_coverage_valid = False
        self.connection_integrity_valid = False
        self.distance_accuracy_valid = False
        self.errors = []
        self.warnings = []

    def check_station_coverage(self):
        all_lines = set()
        for s in self.data.get("stations", []):
            for l in s.get("lines", []):
                all_lines.add(_norm(l))
        for c in self.data.get("connections", []):
            if c.get("line"):
                all_lines.add(_norm(c["line"]))
        missing = []
        for line in MAIN_LINES:
            cands = {_norm(line), _norm(_CN.get(line, line))}
            if not any(any(cd == l or cd in l for l in all_lines) for cd in cands):
                missing.append(line)
        if not self.data.get("stations"):
            self.errors.append("No station data present")
            self.station_coverage_valid = False
        else:
            self.station_coverage_valid = True
        for m in missing:
            self.warnings.append(f"Main line '{m}' not found in data")
        return self.station_coverage_valid

    def check_connection_integrity(self):
        ok = True
        names = {}
        for s in self.data.get("stations", []):
            nm = s.get("name")
            if not nm:
                self.errors.append("Station without name")
                ok = False
                continue
            if nm in names:
                self.warnings.append(f"Duplicate station '{nm}'")
            names[nm] = set(s.get("lines", []))
        connected = set()
        for i, c in enumerate(self.data.get("connections", [])):
            src, dst = c.get("source"), c.get("dest")
            for nm in (src, dst):
                if nm not in names:
                    self.errors.append(f"Connection #{i} references unknown station '{nm}'")
                    ok = False
            if src == dst:
                self.errors.append(f"Connection #{i} is a self-loop at '{src}'")
                ok = False
            line = c.get("line")
            for nm in (src, dst):
                if nm in names and line and line not in names[nm]:
                    self.warnings.append(
                        f"Station '{nm}' not listed on line '{line}' used by connection #{i}")
            connected.add(src)
            connected.add(dst)
        for nm in names:
            if nm not in connected:
                self.warnings.append(f"Station '{nm}' has no connections")
        self.connection_integrity_valid = ok
        return ok

    def check_distance_accuracy(self):
        ok = True
        for i, c in enumerate(self.data.get("connections", [])):
            d = c.get("distance")
            if isinstance(d, bool) or not isinstance(d, (int, float)):
                self.errors.append(f"Connection #{i} has invalid distance {d!r}")
                ok = False
            elif d <= 0:
                self.errors.append(f"Connection #{i} has non-positive distance {d}")
                ok = False
            elif d > MAX_REASONABLE_DISTANCE:
                self.errors.append(f"Connection #{i} has unrealistic distance {d}")
                ok = False
        self.distance_accuracy_valid = ok
        return ok

    def run(self):
        self.check_station_coverage()
        self.check_connection_integrity()
        self.check_distance_accuracy()
        return self.is_valid()

    def is_valid(self):
        return (self.station_coverage_valid and self.connection_integrity_valid
                and self.distance_accuracy_valid)

    def report(self):
        lines = ["Data integrity check:",
                 f"  Stations: {len(self.data.get('stations', []))}",
                 f"  Connections: {len(self.data.get('connections', []))}",
                 f"  Station coverage: {'OK' if self.station_coverage_valid else 'FAILED'}",
                 f"  Connection integrity: {'OK' if self.connection_integrity_valid else 'FAILED'}",
                 f"  Distance accuracy: {'OK' if self.distance_accuracy_valid else 'FAILED'}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        lines.append("Result: " + ("PASSED" if self.is_valid() else "FAILED"))
        return "\n".join(lines)
