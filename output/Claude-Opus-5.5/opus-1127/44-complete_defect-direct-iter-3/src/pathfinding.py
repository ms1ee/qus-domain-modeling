"""Dijkstra-based path finding with transfer awareness.

The search runs over states ``(station, arriving line[, transfers])`` so that
transfers at interchange stations are counted correctly.  Costs are tuples
that are added component-wise, which keeps Dijkstra correct while allowing
different optimisation modes.
"""

from models import MinPQ

VALID_MODES = ("shortest_distance", "least_transfer", "comprehensive")
TRANSFER_PENALTY_METERS = 3000      # comprehensive mode penalty per transfer
PREFERENCE_FACTOR = 0.8             # cost factor for preferred lines


class PathfindingConfig:
    """Configuration for path queries."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines) if preferred_lines else []


class ShortestPath:
    """Single-source shortest path computation using Dijkstra's algorithm."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: float("inf") for v in graph.vertices()}
        self._transfers_to = {}
        self._parent = {}         # state -> (prev_state, edge)
        self._node_state = {}     # node -> best final state
        if source not in graph.graph:
            raise ValueError(f"Source station {source} is not in the graph")
        self._run()

    # ------------------------------------------------------------------ #
    def _cost(self, wdist, transfers, dist):
        mode = self.config.mode
        if mode == "least_transfer":
            return (transfers, wdist, dist)
        if mode == "comprehensive":
            return (wdist + TRANSFER_PENALTY_METERS * transfers, transfers, dist)
        return (wdist, transfers, dist)

    def _run(self):
        cfg = self.config
        limit = cfg.max_transfers
        preferred = set(cfg.preferred_lines)
        start = (self.source, None, 0 if limit is not None else None)
        # state -> (wdist, transfers, dist)
        values = {start: (0.0, 0, 0)}
        best_cost = {start: self._cost(0.0, 0, 0)}
        done = set()
        pq = MinPQ()
        pq.insert(best_cost[start], start)

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in done or cost != best_cost.get(state):
                continue
            done.add(state)
            node, line, _ = state
            wdist, transfers, dist = values[state]
            if node not in self._node_state:
                self._node_state[node] = state
                self.dist_to[node] = dist
                self._transfers_to[node] = transfers
            for edge in self.graph.adj(node):
                new_t = transfers + (1 if line is not None and edge.line != line else 0)
                if limit is not None and new_t > limit:
                    continue
                factor = PREFERENCE_FACTOR if edge.line in preferred else 1.0
                new_w = wdist + edge.weight * factor
                new_d = dist + edge.weight
                new_state = (edge.dest, edge.line, new_t if limit is not None else None)
                if new_state in done:
                    continue
                new_cost = self._cost(new_w, new_t, new_d)
                old = best_cost.get(new_state)
                if old is None or new_cost < old:
                    best_cost[new_state] = new_cost
                    values[new_state] = (new_w, new_t, new_d)
                    self._parent[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

    # ------------------------------------------------------------------ #
    def has_path_to(self, target):
        return target in self._node_state

    def distance_to(self, target):
        return self.dist_to.get(target, float("inf"))

    def path_with_edges(self, target):
        """Return (list of station numbers, list of Edge) from source to target."""
        if target not in self._node_state:
            return [], []
        edges = []
        state = self._node_state[target]
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            state = prev
        edges.reverse()
        path = [self.source] + [e.dest for e in edges]
        return path, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                count += 1
        return count
