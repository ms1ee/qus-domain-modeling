"""Query validation and route planning (combines path search and fares)."""

from fare_calculator import Sum_money, calculate_estimated_time, FareCalculationError
from pathfinding import PathfindingConfig, ShortestPath

FORMAT_ERROR_MSG = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryValidationError(ValueError):
    """Raised when user input is invalid."""


class PathCalculationError(RuntimeError):
    """Raised when no route can be calculated."""


def split_query(text):
    """Split 'Start; End' input into two stripped parts."""
    if text is None:
        raise QueryValidationError(FORMAT_ERROR_MSG)
    normalized = text.replace("；", ";")
    parts = normalized.split(";")
    if len(parts) != 2:
        raise QueryValidationError(FORMAT_ERROR_MSG)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryValidationError(FORMAT_ERROR_MSG)
    return start, end


class RoutePlanner:
    """Validates queries and computes route results."""

    def __init__(self, network, config=None):
        self.network = network
        self.config = config if config is not None else PathfindingConfig()

    def parse_query(self, text):
        """Validate input text and return official (start, end) names."""
        start_raw, end_raw = split_query(text)
        start = self.network.resolve_station(start_raw)
        if start is None:
            raise QueryValidationError(
                "Starting station '{}' does not exist, please check the station name"
                .format(start_raw))
        end = self.network.resolve_station(end_raw)
        if end is None:
            raise QueryValidationError(
                "Ending station '{}' does not exist, please check the station name"
                .format(end_raw))
        if start == end:
            raise QueryValidationError("Starting station cannot be the same as the ending station")
        return start, end

    def plan(self, start, end):
        """Compute the route result dictionary between two official names."""
        net = self.network
        s_num = net.station_to_number[start]
        e_num = net.station_to_number[end]
        try:
            sp = ShortestPath(net.graph, s_num, self.config)
            path, edges = sp.path_with_edges(e_num)
        except (ValueError, KeyError, IndexError) as exc:
            raise PathCalculationError("Path calculation failed: {}".format(exc)) from exc
        if not path:
            msg = "No route found from '{}' to '{}'".format(start, end)
            if self.config.max_transfers is not None:
                msg += " within {} transfer(s)".format(self.config.max_transfers)
            raise PathCalculationError(msg)

        names = [net.number_to_station[n] for n in path]
        distance = sum(e.weight for e in edges)
        transfer_count = sp.get_transfer_count(e_num)

        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)

        transfers = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                transfers.append({"station": names[i],
                                  "from_line": edges[i - 1].line,
                                  "to_line": edges[i].line})

        segments = []
        for i, e in enumerate(edges):
            if segments and segments[-1]["line"] == e.line:
                seg = segments[-1]
                seg["stations"].append(names[i + 1])
                seg["to"] = names[i + 1]
                seg["distance"] += e.weight
            else:
                segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                                 "stations": [names[i], names[i + 1]],
                                 "distance": e.weight})

        try:
            fare = Sum_money(distance)
            est_time = calculate_estimated_time(distance, transfer_count)
        except FareCalculationError as exc:
            raise FareCalculationError("Fare calculation failed: {}".format(exc)) from exc

        return {
            "query": {
                "start": start,
                "end": end,
                "mode": self.config.mode,
                "max_transfers": self.config.max_transfers,
                "line_preference": list(self.config.preferred_lines),
            },
            "path": names,
            "station_count": len(names),
            "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
            "fare": fare,
            "estimated_time": round(est_time, 1),
            "transfer_count": transfer_count,
            "lines": lines,
            "transfers": transfers,
            "segments": segments,
        }

    def query(self, text):
        start, end = self.parse_query(text)
        return self.plan(start, end)
