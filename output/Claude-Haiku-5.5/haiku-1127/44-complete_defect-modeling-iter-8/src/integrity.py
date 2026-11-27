"""Data integrity checks for the subway network dataset."""

from collections import deque

MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 10000

# Representative stations of the main lines used for coverage checking.
MAIN_LINE_REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "西单", "天安门东", "国贸", "四惠"],
    "Line 2": ["西直门", "建国门", "东直门", "车公庄"],
    "Line 4": ["圆明园", "北京南站"],
    "Line 5": ["宋家庄", "东单"],
    "Line 6": ["海淀五路居", "东大桥"],
    "Line 8": ["鼓楼大街"],
    "Line 10": ["国贸", "宋家庄"],
    "Line 13": ["回龙观", "西直门"],
    "Line 14": ["张郭庄"],
    "Line 15": ["望京西"],
    "Changping Line": ["西二旗"],
    "Yizhuang Line": ["亦庄火车站"],
    "Fangshan Line": ["郭公庄"],
    "Airport Line": ["T3航站楼"],
}


class DataIntegrityChecker:
    """Validates station coverage, connection integrity and distance accuracy.

    Attributes:
        coverage_rate: Fraction (0..1) of representative stations present.
        errors: List of error messages.
        warnings: List of non-fatal warning messages.
        passed: True if no errors were found.
    """

    def __init__(self, data_manager):
        self.manager = data_manager
        self.coverage_rate = 0.0
        self.errors = []
        self.warnings = []
        self.passed = False

    def run(self):
        """Run all checks and return self."""
        self.coverage_rate = 0.0
        self.errors = []
        self.warnings = []
        self.check_station_coverage()
        self.check_connections()
        self.check_distances()
        self.passed = not self.errors
        return self

    def check_station_coverage(self):
        """Verify that representative stations of the main lines are present."""
        known = set(self.manager.station_names())
        total = 0
        found = 0
        for line, names in MAIN_LINE_REPRESENTATIVE_STATIONS.items():
            for name in names:
                total += 1
                if name in known:
                    found += 1
                else:
                    self.errors.append(f"Representative station '{name}' of {line} is missing")
        self.coverage_rate = found / total if total else 0.0

    def check_connections(self):
        """Verify connection endpoints, line consistency, duplicates and connectivity."""
        data = self.manager.data
        declared = {}
        for record in data.get("stations", []):
            declared.setdefault(record["name"], set()).update(record.get("lines", []))

        seen = set()
        for conn in data.get("connections", []):
            src = conn.get("source")
            dst = conn.get("dest")
            line = conn.get("line")
            label = f"{src} - {dst} ({line})"

            if src == dst:
                self.errors.append(f"Connection {label} is a self-loop")
            for name in (src, dst):
                if name not in declared:
                    self.errors.append(f"Connection {label} references undeclared station '{name}'")
            if src in declared and dst in declared:
                if line not in declared[src] or line not in declared[dst]:
                    self.errors.append(f"Connection {label}: line not served by both stations")

            key = (frozenset((src, dst)), line)
            if key in seen:
                self.errors.append(f"Duplicate connection {label}")
            seen.add(key)

        graph = self.manager.graph
        for name, number in self.manager.station_numbers.items():
            if not graph.adjacent(number):
                self.errors.append(f"Station '{name}' has no connections")

        nodes = graph.nodes()
        if nodes:
            visited = set()
            components = 0
            for start in nodes:
                if start in visited:
                    continue
                components += 1
                queue = deque([start])
                visited.add(start)
                while queue:
                    node = queue.popleft()
                    for edge in graph.adjacent(node):
                        nxt = edge.other_end(node)
                        if nxt not in visited:
                            visited.add(nxt)
                            queue.append(nxt)
            if components > 1:
                self.errors.append(f"Network is disconnected: {components} separate components")

    def check_distances(self):
        """Verify that every connection distance is a plausible positive integer."""
        for conn in self.manager.data.get("connections", []):
            distance = conn.get("distance")
            label = f"{conn.get('source')} - {conn.get('dest')}"
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                self.errors.append(f"Connection {label} has a non-numeric distance")
            elif distance <= 0:
                self.errors.append(f"Connection {label} has non-positive distance {distance}")
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M):
                self.errors.append(
                    f"Connection {label} distance {distance} m is outside the plausible range "
                    f"{MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
                )
            elif isinstance(distance, float) and not distance.is_integer():
                self.warnings.append(f"Connection {label} distance {distance} is not an integer")

    def format_report(self):
        """Return a human-readable summary of the check results."""
        lines = [
            f"Data integrity check: {'PASSED' if self.passed else 'FAILED'}",
            f"Station coverage of main lines: {self.coverage_rate * 100:.1f}%",
        ]
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            lines.extend(f"  - {message}" for message in self.errors)
        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            lines.extend(f"  - {message}" for message in self.warnings)
        return "\n".join(lines) + "\n"
