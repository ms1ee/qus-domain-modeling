"""Path calculation: Dijkstra-based shortest path search over the subway graph.

The search runs over states ``(station, line of last edge, transfers so far)``
so that transfers can be counted, limited and optimized. Each state is
ordered in a ``MinPQ`` (binary heap), which gives the O((V+E) log V) bound
for the usual case.

Query modes:
    shortest_distance  minimize the total distance in meters
    least_transfer     minimize the number of transfers, then the distance
    comprehensive      minimize distance plus a penalty per transfer
"""

from fare_calculator import Sum_money, calculate_estimated_time
from min_pq import MinPQ


MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) charged for each transfer in comprehensive mode.
TRANSFER_PENALTY_M = 1500.0
# Extra cost (meters) charged for riding a line outside the preferred lines.
LINE_PREFERENCE_PENALTY_M = 1000.0
# Safety limit on transfers when no maximum is configured.
MAX_TRANSFER_CAP = 20


class NoPathError(Exception):
    """Raised when no route exists under the given constraints."""


class PathfindingConfig:
    """Configuration of a path query.

    Attributes:
        mode: one of VALID_MODES.
        max_transfers: maximum number of transfers, or None for no limit.
        preferred_lines: list of preferred line names (may be empty).
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"unsupported mode '{mode}'")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [
            str(line).strip() for line in (preferred_lines or []) if str(line).strip()
        ]

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, "
                f"max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Dijkstra's algorithm from a single source station.

    Attributes:
        dist_to: dict station number -> physical distance (meters) along the
            selected path from the source.
    """

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError(f"source {source!r} is not a vertex of the graph")
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {}
        self._vertex_state = {}   # station number -> best finalized state
        self._parent = {}         # finalized state -> (parent state, edge)
        self._run()

    # ----- cost model ---------------------------------------------------
    def _key(self, cost, transfers):
        """Return the priority key for a state according to the query mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, cost)
        if mode == MODE_COMPREHENSIVE:
            return (cost + TRANSFER_PENALTY_M * transfers,)
        return (cost,)

    # ----- Dijkstra -----------------------------------------------------
    def _run(self):
        cfg = self.config
        pq = MinPQ()
        start = (self.source, None, 0)
        start_key = self._key(0.0, 0)
        # best[state] = (key, distance, cost, parent state, edge used)
        best = {start: (start_key, 0.0, 0.0, None, None)}
        pq.insert(start_key, start)
        done = set()

        while not pq.is_empty():
            _, state = pq.del_min()
            if state in done:
                continue
            key, dist, cost, parent, edge = best[state]
            done.add(state)
            self._parent[state] = (parent, edge)

            vertex, line, transfers = state
            if vertex not in self._vertex_state:
                self._vertex_state[vertex] = state
                self.dist_to[vertex] = dist

            for e in self.graph.adj.get(vertex, ()):
                nxt = e.other(vertex)
                new_transfers = transfers
                if line is not None and e.line != line:
                    new_transfers = transfers + 1
                if cfg.max_transfers is not None and new_transfers > cfg.max_transfers:
                    continue
                if new_transfers > MAX_TRANSFER_CAP:
                    continue

                nstate = (nxt, e.line, new_transfers)
                if nstate in done:
                    continue

                penalty = 0.0
                if cfg.preferred_lines and e.line not in cfg.preferred_lines:
                    penalty = LINE_PREFERENCE_PENALTY_M
                ncost = cost + e.distance + penalty
                ndist = dist + e.distance
                nkey = self._key(ncost, new_transfers)

                old = best.get(nstate)
                if old is None or nkey < old[0]:
                    best[nstate] = (nkey, ndist, ncost, state, e)
                    pq.insert(nkey, nstate)

    # ----- queries ------------------------------------------------------
    def has_path_to(self, target):
        """Return True if ``target`` is reachable from the source."""
        return target in self._vertex_state

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` of the best path from source to target.

        ``stations`` is the list of station numbers from source to target and
        ``edges`` the list of Edge objects traversed between them.
        Raises NoPathError if the target is unreachable under the constraints.
        """
        if target not in self._vertex_state:
            raise NoPathError(f"no path to station {target!r}")
        state = self._vertex_state[target]
        vertices = []
        edges = []
        while True:
            vertices.append(state[0])
            parent, edge = self._parent[state]
            if parent is None:
                break
            edges.append(edge)
            state = parent
        vertices.reverse()
        edges.reverse()
        return vertices, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the best path to target."""
        if target not in self._vertex_state:
            raise NoPathError(f"no path to station {target!r}")
        return self._vertex_state[target][2]


class Route:
    """A computed route with all information needed for reporting.

    Attributes:
        start, end: official station names.
        config: the PathfindingConfig used.
        station_names: ordered list of station names from start to end.
        edges: list of Edge objects along the route.
        segments: list of dicts with keys line, from, to, stations, distance_m.
        transfer_stations: list of dicts with keys station, from_line, to_line.
        distance_m: total distance in meters.
        fare: fare in yuan.
        estimated_minutes: estimated travel time in minutes.
    """

    def __init__(self, start, end, config, station_names, edges, segments,
                 transfer_stations, distance_m, fare, estimated_minutes):
        self.start = start
        self.end = end
        self.config = config
        self.station_names = list(station_names)
        self.edges = list(edges)
        self.segments = list(segments)
        self.transfer_stations = list(transfer_stations)
        self.distance_m = distance_m
        self.fare = fare
        self.estimated_minutes = estimated_minutes

    @property
    def distance_km(self):
        return self.distance_m / 1000.0

    @property
    def transfer_count(self):
        return len(self.transfer_stations)

    @property
    def lines(self):
        """Unique line names involved, in the order they are ridden."""
        result = []
        for segment in self.segments:
            if segment["line"] not in result:
                result.append(segment["line"])
        return result


def plan_route(network, start_name, end_name, config=None):
    """Compute the route, fare and time estimate between two official stations.

    Raises ValueError for invalid stations or identical endpoints and
    NoPathError when no route satisfies the constraints.
    """
    cfg = config if config is not None else PathfindingConfig()
    if start_name == end_name:
        raise ValueError("starting station cannot be the same as the ending station")

    src = network.get_station_number(start_name)
    dst = network.get_station_number(end_name)
    sp = ShortestPath(network.graph, src, cfg)
    if not sp.has_path_to(dst):
        if cfg.max_transfers is not None:
            raise NoPathError(
                f"no route from '{start_name}' to '{end_name}' within "
                f"{cfg.max_transfers} transfer(s)"
            )
        raise NoPathError(f"no route from '{start_name}' to '{end_name}'")

    numbers, edges = sp.path_with_edges(dst)
    names = [network.get_station_name(num) for num in numbers]

    segments = []
    transfer_stations = []
    for i, edge in enumerate(edges):
        if i == 0 or edges[i - 1].line != edge.line:
            if i > 0:
                transfer_stations.append({
                    "station": names[i],
                    "from_line": edges[i - 1].line,
                    "to_line": edge.line,
                })
            segments.append({
                "line": edge.line,
                "from": names[i],
                "to": names[i + 1],
                "stations": 2,
                "distance_m": edge.distance,
            })
        else:
            segment = segments[-1]
            segment["to"] = names[i + 1]
            segment["stations"] += 1
            segment["distance_m"] += edge.distance

    distance_m = sum(edge.distance for edge in edges)
    transfer_count = sp.get_transfer_count(dst)
    fare = Sum_money(distance_m)
    estimated = calculate_estimated_time(distance_m, transfer_count)

    return Route(
        start=start_name,
        end=end_name,
        config=cfg,
        station_names=names,
        edges=edges,
        segments=segments,
        transfer_stations=transfer_stations,
        distance_m=distance_m,
        fare=fare,
        estimated_minutes=estimated,
    )
