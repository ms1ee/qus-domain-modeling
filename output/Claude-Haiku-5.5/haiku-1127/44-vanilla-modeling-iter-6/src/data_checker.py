"""Data integrity checks for the subway network (--check_data)."""

from collections import deque

# Representative main lines that must be covered by the dataset.
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

# Plausible range for a single inter-station distance (meters).
MIN_DISTANCE_M = 50
MAX_DISTANCE_M = 10000


class DataChecker:
    """Runs coverage, connection and distance checks over a Graph.

    Attributes:
        coverage_valid, connection_valid, distance_valid: check results.
        messages: list of (level, text) tuples with level in
            {"ERROR", "WARNING", "INFO"}.
    """

    def __init__(self, graph, raw_data=None):
        self.graph = graph
        self.raw_data = raw_data or {}
        self.coverage_valid = False
        self.connection_valid = False
        self.distance_valid = False
        self.messages = []

    def _report(self, level, text):
        self.messages.append((level, text))

    def check_coverage(self):
        """Verify that representative stations of the main lines exist."""
        if self.graph.station_count == 0:
            self._report("ERROR", "no stations found in dataset")
            self.coverage_valid = False
            return False
        lines = set(self.graph.all_lines())
        missing = [line for line in REQUIRED_MAIN_LINES if line not in lines]
        for line in missing:
            self._report("WARNING", f"main line not covered by dataset: {line}")
        self.coverage_valid = not missing
        return self.coverage_valid

    def _is_connected_component_count(self):
        """Return the number of connected components of the station graph."""
        seen = set()
        components = 0
        for number in self.graph.number_to_station:
            if number in seen:
                continue
            components += 1
            queue = deque([number])
            seen.add(number)
            while queue:
                node = queue.popleft()
                for edge in self.graph.get_edges(node):
                    nxt = edge.other(node)
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
        return components

    def check_connections(self):
        """Verify structural integrity of connections and the raw dataset."""
        ok = True
        graph = self.graph
        for edge in graph.iter_edges():
            if edge.source not in graph.number_to_station or \
                    edge.dest not in graph.number_to_station:
                self._report("ERROR", f"edge references unknown station: {edge!r}")
                ok = False
            if edge.source == edge.dest:
                self._report("ERROR", f"self loop: {edge!r}")
                ok = False
            # Bidirectional consistency: the edge must appear on both endpoints.
            if not any(e is edge for e in graph.get_edges(edge.source)) or \
                    not any(e is edge for e in graph.get_edges(edge.dest)):
                self._report("ERROR", f"asymmetric adjacency for edge: {edge!r}")
                ok = False

        seen_pairs = {}
        for conn in self.raw_data.get("connections", []):
            key = frozenset((conn.get("source"), conn.get("dest")))
            if key in seen_pairs:
                if seen_pairs[key] != conn.get("distance"):
                    self._report(
                        "ERROR",
                        f"conflicting distances for {conn.get('source')} - "
                        f"{conn.get('dest')}: {seen_pairs[key]} vs {conn.get('distance')}")
                    ok = False
                else:
                    self._report("INFO", f"duplicate connection ignored: "
                                 f"{conn.get('source')} - {conn.get('dest')}")
            else:
                seen_pairs[key] = conn.get("distance")

        for name in graph.station_names():
            if not graph.get_edges(graph.number_of(name)):
                self._report("WARNING", f"station has no connections: {name}")

        components = self._is_connected_component_count()
        if components > 1:
            self._report("WARNING",
                         f"network has {components} disconnected components")

        self.connection_valid = ok
        return ok

    def check_distances(self):
        """Verify that every distance lies within the plausible range."""
        ok = True
        for edge in self.graph.iter_edges():
            if not (MIN_DISTANCE_M <= edge.distance <= MAX_DISTANCE_M):
                self._report(
                    "ERROR",
                    f"distance out of range ({MIN_DISTANCE_M}-{MAX_DISTANCE_M} m) "
                    f"for {self.graph.name_of(edge.source)} - "
                    f"{self.graph.name_of(edge.dest)}: {edge.distance} m")
                ok = False
        for conn in self.raw_data.get("connections", []):
            distance = conn.get("distance")
            if not isinstance(distance, (int, float)) or isinstance(distance, bool) \
                    or distance <= 0:
                self._report("ERROR", f"invalid raw distance: {distance!r}")
                ok = False
        self.distance_valid = ok
        return ok

    def run_all(self):
        """Run every check and return True only if all of them pass."""
        self.messages = []
        self.check_coverage()
        self.check_connections()
        self.check_distances()
        return self.coverage_valid and self.connection_valid and self.distance_valid

    def format_report(self):
        """Return a human-readable summary of the last check run."""
        lines = [
            "Data integrity check",
            f"  Station coverage : {'PASS' if self.coverage_valid else 'FAIL'}",
            f"  Connections      : {'PASS' if self.connection_valid else 'FAIL'}",
            f"  Distances        : {'PASS' if self.distance_valid else 'FAIL'}",
            f"  Stations: {self.graph.station_count}, "
            f"connections: {self.graph.edge_count}",
        ]
        for level, text in self.messages:
            lines.append(f"  [{level}] {text}")
        return "\n".join(lines)
