"""Data management: loading, saving and integrity checking of the network data."""

from src.data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from src.network import SubwayNetwork

# Main lines expected to be present in the dataset (PRD section 4.1).
MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
MIN_STATIONS_PER_MAIN_LINE = 2
# Plausible range for a single inter-station distance, in meters.
DISTANCE_MIN_METERS = 50
DISTANCE_MAX_METERS = 15000


class DataManager:
    """Manages the source dataset of the subway network.

    Attributes:
        sourceFile: path of the dataset file.
        is_integrity_valid: result of the last integrity check.
    """

    def __init__(self, source_file: str = DATA_FILE_PATH):
        self.sourceFile = source_file
        self.is_integrity_valid = False
        self.data = None

    def load_network(self) -> SubwayNetwork:
        """Load the dataset file and build a ``SubwayNetwork`` from it."""
        self.data = load_subway_data(self.sourceFile)
        return SubwayNetwork(self.data)

    def save_network(self, network: SubwayNetwork, path: str = None) -> str:
        """Save the (possibly updated) network to a JSON file. Returns the path used."""
        target = path or self.sourceFile
        save_subway_data(network.to_data(), target)
        return target

    def check_integrity(self, network: SubwayNetwork) -> list[str]:
        """Run all integrity checks. Returns a list of problems (empty if valid)."""
        issues: list[str] = []
        issues += self._check_line_coverage(network)
        issues += self._check_stations(network)
        issues += self._check_connections(network)
        issues += self._check_distances(network)
        issues += self._check_connectivity(network)
        self.is_integrity_valid = not issues
        return issues

    # ----- individual checks ------------------------------------------------
    @staticmethod
    def _check_line_coverage(network: SubwayNetwork) -> list[str]:
        issues = []
        for line in MAIN_LINES:
            official = network.resolve_line(line)
            if official is None:
                issues.append(f"Main line '{line}' is missing from the network data")
            elif len(network.stations_on_line(official)) < MIN_STATIONS_PER_MAIN_LINE:
                issues.append(f"Main line '{line}' has fewer than {MIN_STATIONS_PER_MAIN_LINE} stations")
        return issues

    @staticmethod
    def _check_stations(network: SubwayNetwork) -> list[str]:
        issues = []
        for name in network.station_names():
            if not network.graph.station_lines.get(name):
                issues.append(f"Station '{name}' has no line information")
        return issues

    @staticmethod
    def _check_connections(network: SubwayNetwork) -> list[str]:
        issues = []
        seen = set()
        for edge in network.graph.edges():
            a = network.number_to_station[edge.source]
            b = network.number_to_station[edge.dest]
            if edge.source == edge.dest:
                issues.append(f"Connection on '{edge.line}' links station '{a}' to itself")
                continue
            key = (min(a, b), max(a, b), edge.line)
            if key in seen:
                issues.append(f"Duplicate connection '{a}' - '{b}' on '{edge.line}'")
            seen.add(key)
            for name in (a, b):
                if edge.line not in network.graph.station_lines.get(name, []):
                    issues.append(f"Station '{name}' is connected on '{edge.line}' but not listed on that line")
        return issues

    @staticmethod
    def _check_distances(network: SubwayNetwork) -> list[str]:
        issues = []
        for edge in network.graph.edges():
            a = network.number_to_station[edge.source]
            b = network.number_to_station[edge.dest]
            if not isinstance(edge.distance, (int, float)) or edge.distance != int(edge.distance):
                issues.append(f"Distance {a} - {b} ({edge.line}) must be an integer number of meters")
            elif not DISTANCE_MIN_METERS <= edge.distance <= DISTANCE_MAX_METERS:
                issues.append(
                    f"Suspicious distance {edge.distance} m between '{a}' and '{b}' ({edge.line})"
                )
        return issues

    @staticmethod
    def _check_connectivity(network: SubwayNetwork) -> list[str]:
        if network.graph.node_count == 0:
            return ["Network contains no stations"]
        reachable = network.connected_component_size(0)
        if reachable == network.graph.node_count:
            return []
        return [
            f"Network is disconnected: only {reachable} of {network.graph.node_count} stations reachable from "
            f"'{network.number_to_station[0]}'"
        ]
