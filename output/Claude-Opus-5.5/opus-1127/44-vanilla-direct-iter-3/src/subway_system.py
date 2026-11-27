"""High-level service combining station resolution, routing and fares."""

import difflib

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath
from report import build_route_info

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class InputValidationError(Exception):
    pass


class PathCalculationError(Exception):
    pass


class FareCalculationError(Exception):
    pass


def _normalize(name):
    s = str(name).strip().casefold()
    for suffix in (" station", "站"):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
    for ch in " \t'’`-_·":
        s = s.replace(ch, "")
    return s


class SubwayFareSystem:
    def __init__(self, graph, config=None):
        self.graph = graph
        self.config = config or PathfindingConfig()
        self._norm_map = {}
        for name in graph.station_to_number:
            self._norm_map.setdefault(_normalize(name), name)

    # ---- input ----------------------------------------------------------
    def resolve_station(self, name):
        name = " ".join(str(name).split())
        if name in self.graph.station_to_number:
            return name
        return self._norm_map.get(_normalize(name))

    def suggest(self, name, n=3):
        return difflib.get_close_matches(name, list(self.graph.station_to_number), n=n, cutoff=0.6)

    def resolve_lines(self, lines):
        known = set()
        for ls in self.graph.station_lines.values():
            known.update(ls)
        for e in self.graph.edges():
            known.add(e.line)
        lookup = {"".join(str(l).lower().split()): l for l in known if l is not None}
        resolved, unknown = [], []
        for l in lines:
            r = lookup.get("".join(l.lower().split()))
            if r is None:
                unknown.append(l)
            elif r not in resolved:
                resolved.append(r)
        return resolved, unknown

    def parse_query(self, raw):
        text = (raw or "").replace("；", ";").strip()
        parts = text.split(";")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise InputValidationError(FORMAT_ERROR)
        start_raw, end_raw = parts[0].strip(), parts[1].strip()
        start = self.resolve_station(start_raw)
        if start is None:
            raise InputValidationError(self._missing_msg("Starting", start_raw))
        end = self.resolve_station(end_raw)
        if end is None:
            raise InputValidationError(self._missing_msg("Ending", end_raw))
        if start == end:
            raise InputValidationError("Starting station cannot be the same as the ending station")
        return start, end

    def _missing_msg(self, kind, name):
        msg = "%s station '%s' does not exist, please check the station name" % (kind, name)
        sugg = self.suggest(name)
        if sugg:
            msg += " (did you mean: %s?)" % ", ".join(sugg)
        return msg

    # ---- routing --------------------------------------------------------
    def find_route(self, start, end):
        s = self.graph.station_to_number[start]
        t = self.graph.station_to_number[end]
        try:
            sp = ShortestPath(self.graph, s, self.config)
        except Exception as exc:
            raise PathCalculationError("Path calculation failed: %s" % exc) from exc
        if not sp.has_path_to(t):
            msg = "No route found from '%s' to '%s'" % (start, end)
            if self.config.max_transfers is not None:
                msg += " within a maximum of %d transfer(s)" % self.config.max_transfers
            raise PathCalculationError(msg)
        try:
            stations, edges = sp.path_with_edges(t)
            distance = sp.dist_to[t]
            transfers = sp.get_transfer_count(t)
        except Exception as exc:
            raise PathCalculationError("Path calculation failed: %s" % exc) from exc
        try:
            fare = Sum_money(distance)
            est = calculate_estimated_time(distance, transfers)
        except (TypeError, ValueError) as exc:
            raise FareCalculationError("Fare calculation failed: %s" % exc) from exc
        return build_route_info(start, end, self.config.mode, stations, edges, distance,
                                fare, est, transfers, self.graph, self.config)

    def query(self, raw):
        start, end = self.parse_query(raw)
        return self.find_route(start, end)
