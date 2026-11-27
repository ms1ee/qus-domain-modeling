"""
Path calculation using Dijkstra's algorithm with a heap-based priority queue.

The search runs over a state space (station, current line[, transfers]) so
that transfers between lines can be counted and constrained correctly at
multi-line interchange stations.

Modes:
  * shortest_distance - minimise total distance (ties: preferred lines, fewer transfers)
  * least_transfer    - minimise number of transfers, then distance
  * comprehensive     - minimise distance + transfer penalty (composite score)
"""

from models import MinPQ

INF = float("inf")

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance cost (meters) of one transfer in comprehensive mode.
# A transfer takes about 5 minutes; at ~1.5 min/km that is ~3.3 km.
DEFAULT_TRANSFER_PENALTY = 3000
# Weight multiplier applied to edges on preferred lines (comprehensive / least_transfer).
DEFAULT_PREFERENCE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None,
                 transfer_penalty=DEFAULT_TRANSFER_PENALTY,
                 preference_factor=DEFAULT_PREFERENCE_FACTOR):
        if mode not in VALID_MODES:
            raise ValueError("Invalid mode %r, expected one of %s" % (mode, ", ".join(VALID_MODES)))
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise TypeError("max_transfers must be an integer or None")
            if max_transfers < 0:
                raise ValueError("max_transfers must be non-negative")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [l for l in preferred_lines if l]
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return ("PathfindingConfig(mode=%r, max_transfers=%r, preferred_lines=%r)"
                % (self.mode, self.max_transfers, self.preferred_lines))


class ShortestPath:
    """Dijkstra shortest path from a single source station number."""

    def __init__(self, graph, source, config=None):
        if not graph.has_vertex(source):
            raise ValueError("Source station %r is not in the graph" % (source,))
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.dist_to = {v: INF for v in graph.vertices()}
        self._best_state = {}
        self._parent = {}
        self._state_info = {}
        self._run()

    # ------------------------------------------------------------------
    def _cost(self, dist, transfers, weighted, nonpref):
        mode = self.config.mode
        if mode == MODE_SHORTEST_DISTANCE:
            return (dist, nonpref, transfers)
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, weighted, dist)
        return (weighted + self.config.transfer_penalty * transfers, transfers, dist)

    def _run(self):
        cfg = self.config
        preferred = set(cfg.preferred_lines)
        track_transfers = cfg.max_transfers is not None
        start = (self.source, None, 0)
        # state -> (dist, transfers, weighted, nonpref)
        self._state_info[start] = (0, 0, 0, 0)
        best_cost = {start: self._cost(0, 0, 0, 0)}
        pq = MinPQ()
        pq.insert(best_cost[start], start)
        settled = set()

        while not pq.is_empty():
            cost, state = pq.del_min()
            if state in settled or cost != best_cost.get(state):
                continue
            settled.add(state)
            node, line, _ = state
            dist, transfers, weighted, nonpref = self._state_info[state]
            if node not in self._best_state:
                self._best_state[node] = state
                self.dist_to[node] = dist

            for edge in self.graph.neighbors(node):
                w = edge.other(node)
                is_transfer = line is not None and edge.line != line
                new_t = transfers + (1 if is_transfer else 0)
                if track_transfers and new_t > cfg.max_transfers:
                    continue
                new_state = (w, edge.line, new_t if track_transfers else 0)
                if new_state in settled:
                    continue
                on_pref = edge.line in preferred
                new_dist = dist + edge.weight
                new_weighted = weighted + (edge.weight * cfg.preference_factor if on_pref else edge.weight)
                new_nonpref = nonpref + (0 if on_pref or not preferred else edge.weight)
                new_cost = self._cost(new_dist, new_t, new_weighted, new_nonpref)
                old = best_cost.get(new_state)
                if old is None or new_cost < old:
                    best_cost[new_state] = new_cost
                    self._state_info[new_state] = (new_dist, new_t, new_weighted, new_nonpref)
                    self._parent[new_state] = (state, edge)
                    pq.insert(new_cost, new_state)

    # ------------------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best_state

    def distance_to(self, target):
        return self.dist_to.get(target, INF)

    def path_with_edges(self, target):
        """Return (station number list, edge list) from source to target.

        Returns ([], []) when the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        nodes = [state[0]]
        edges = []
        while state in self._parent:
            prev, edge = self._parent[state]
            edges.append(edge)
            nodes.append(prev[0])
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Number of line changes along the path to target (0 if unreachable)."""
        _, edges = self.path_with_edges(target)
        return count_transfers(edges)


def count_transfers(edges):
    count = 0
    for prev, cur in zip(edges, edges[1:]):
        if prev.line != cur.line:
            count += 1
    return count
