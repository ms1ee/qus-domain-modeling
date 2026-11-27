"""
Dijkstra-based path computation on the subway graph.

The search runs on an expanded state space ``(station, current line[,
transfers])`` so that line changes (transfers) at interchange stations can be
counted and optimised exactly.  Three modes are supported:

* ``shortest_distance`` - minimise distance (ties broken by fewer transfers)
* ``least_transfer``    - minimise transfers, then distance
* ``comprehensive``     - minimise distance + a per-transfer penalty

A maximum number of transfers and a list of preferred lines can also be
configured.  Complexity is O((V+E) log V) on the expanded graph thanks to the
heap-based ``MinPQ``.
"""

from models import MinPQ, Edge, Graph  # noqa: F401  (re-exported)

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

#: Equivalent distance (meters) of one transfer in comprehensive mode.
DEFAULT_TRANSFER_PENALTY = 4000
#: Weight multiplier applied to edges on preferred lines.
DEFAULT_PREFERENCE_FACTOR = 0.7

INF = float("inf")


class PathfindingConfig:
    """Configuration for a path query.

    Attributes:
        mode:            one of ``VALID_MODES``
        max_transfers:   maximum allowed transfers or ``None`` (unlimited)
        preferred_lines: list of line names to favour
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None,
                 preferred_lines=None,
                 transfer_penalty=DEFAULT_TRANSFER_PENALTY,
                 preference_factor=DEFAULT_PREFERENCE_FACTOR):
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            max_transfers = int(max_transfers)
            if max_transfers < 0:
                raise ValueError("max_transfers cannot be negative")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines)
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, "
                f"max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class ShortestPath:
    """Single-source shortest paths (Dijkstra) from ``source``.

    Attributes:
        source:  source station number
        dist_to: dict[station number, distance in meters of the chosen path]
                 (``inf`` for unreachable stations)
    """

    def __init__(self, graph, source, config=None):
        if config is None:
            config = PathfindingConfig()
        self.graph = graph
        self.source = source
        self.config = config
        self._preferred = set(config.preferred_lines or [])
        self._track_transfers = config.max_transfers is not None

        self.dist_to = {v: INF for v in graph.vertices()}
        self._edge_to = {}          # state -> (previous state, Edge)
        self._station_state = {}    # station -> best settled state

        if not graph.has_vertex(source):
            raise ValueError(f"Source station {source!r} is not in the graph")
        self._run()

    # ------------------------------------------------------------ helpers
    def _key(self, eff, transfers, dist):
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, eff, dist)
        if mode == MODE_COMPREHENSIVE:
            return (eff + self.config.transfer_penalty * transfers, transfers, dist)
        return (eff, transfers, dist)

    def _effective_weight(self, edge):
        if self._preferred and edge.line in self._preferred:
            return edge.weight * self.config.preference_factor
        return edge.weight

    # --------------------------------------------------------- algorithm
    def _run(self):
        start = (self.source, None, 0 if self._track_transfers else None)
        info = {start: (0, 0, 0)}  # state -> (effective, actual distance, transfers)
        best_key = {start: self._key(0, 0, 0)}
        settled = set()
        pq = MinPQ()
        pq.insert(best_key[start], start)
        max_t = self.config.max_transfers

        while not pq.is_empty():
            key, state = pq.del_min()
            if state in settled or key != best_key.get(state):
                continue
            settled.add(state)
            v, line, _ = state
            eff, dist, transfers = info[state]
            if v not in self._station_state:
                self._station_state[v] = state
                self.dist_to[v] = dist

            for edge in self.graph.adj(v):
                w = edge.other(v)
                changed = line is not None and edge.line != line
                new_t = transfers + (1 if changed else 0)
                if max_t is not None and new_t > max_t:
                    continue
                new_state = (w, edge.line, new_t if self._track_transfers else None)
                if new_state in settled:
                    continue
                new_eff = eff + self._effective_weight(edge)
                new_dist = dist + edge.weight
                new_key = self._key(new_eff, new_t, new_dist)
                old = best_key.get(new_state)
                if old is None or new_key < old:
                    best_key[new_state] = new_key
                    info[new_state] = (new_eff, new_dist, new_t)
                    self._edge_to[new_state] = (state, edge)
                    pq.insert(new_key, new_state)

    # ------------------------------------------------------------ queries
    def has_path_to(self, target):
        return target in self._station_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` of the chosen path to ``target``.

        ``stations`` is the ordered list of station numbers from the source to
        the target; ``edges`` the list of traversed ``Edge`` objects.  Both are
        empty if the target is unreachable.
        """
        if target not in self._station_state:
            return [], []
        state = self._station_state[target]
        stations = [state[0]]
        edges = []
        while state in self._edge_to:
            prev, edge = self._edge_to[state]
            edges.append(edge)
            stations.append(prev[0])
            state = prev
        stations.reverse()
        edges.reverse()
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    @staticmethod
    def count_transfers(edges):
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count

    def get_transfer_count(self, target):
        """Number of line changes along the path to ``target`` (0 if none)."""
        _, edges = self.path_with_edges(target)
        return self.count_transfers(edges)

    def get_transfer_stations(self, target):
        """Station numbers where a line change happens along the path."""
        stations, edges = self.path_with_edges(target)
        result = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                result.append(stations[i])
        return result

    def get_lines(self, target):
        """Ordered list of distinct lines used along the path."""
        _, edges = self.path_with_edges(target)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        return lines
