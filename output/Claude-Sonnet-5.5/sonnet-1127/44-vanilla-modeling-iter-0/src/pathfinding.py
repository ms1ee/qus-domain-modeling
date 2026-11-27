"""Dijkstra shortest path with distance / transfer / comprehensive modes."""
import heapq
import itertools

from models import Edge

TRANSFER_PENALTY = 1000  # meters-equivalent per transfer (comprehensive mode)
PREFERRED_DISCOUNT = 0.9


class MinPQ:
    """Binary-heap based min priority queue."""

    def __init__(self):
        self.heap = []
        self._counter = itertools.count()

    def push(self, priority, item):
        heapq.heappush(self.heap, (priority, next(self._counter), item))

    def pop(self):
        priority, _, item = heapq.heappop(self.heap)
        return priority, item

    def is_empty(self):
        return not self.heap

    def __len__(self):
        return len(self.heap)


class PathfindingConfig:
    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None):
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = list(preferred_lines or [])


class ShortestPath:
    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._best_state = {}
        self._info = {}  # state -> (prev_state, edge, dist, transfers)
        self._run()

    def _mode(self):
        m = self.config.mode
        return getattr(m, "value", m)

    def _edge_cost(self, edge, is_transfer):
        mode = self._mode()
        pref = [p.lower() for p in self.config.preferred_lines]
        w = edge.distance
        if pref and edge.line and edge.line.lower() in pref:
            w = w * PREFERRED_DISCOUNT
        t = 1 if is_transfer else 0
        if mode == "least_transfer":
            return (t, w)
        if mode == "comprehensive":
            return (w + t * TRANSFER_PENALTY, 0)
        return (w, t)

    def _run(self):
        limit = self.config.max_transfers
        start = (self.source, None, 0)
        costs = {start: (0, 0)}
        self._info[start] = (None, None, 0, 0)
        pq = MinPQ()
        pq.push((0, 0), start)
        done = set()
        best_cost = {}
        while not pq.is_empty():
            cost, state = pq.pop()
            if state in done:
                continue
            done.add(state)
            node, line, _ = state
            _, _, dist, trans = self._info[state]
            if node not in best_cost or cost < best_cost[node]:
                best_cost[node] = cost
                self._best_state[node] = state
                self.dist_to[node] = dist
            for e in self.graph.neighbors(node):
                tr = line is not None and e.line != line
                nt = trans + (1 if tr else 0)
                if limit is not None and nt > limit:
                    continue
                key = (e.dest, e.line, nt if limit is not None else 0)
                if key in done:
                    continue
                c = self._edge_cost(e, tr)
                nc = (cost[0] + c[0], cost[1] + c[1])
                if key not in costs or nc < costs[key]:
                    costs[key] = nc
                    self._info[key] = (state, e, dist + e.distance, nt)
                    pq.push(nc, key)

    def has_path_to(self, target):
        return target in self._best_state

    def path_with_edges(self, target):
        if target not in self._best_state:
            return [], []
        state = self._best_state[target]
        nodes, edges = [], []
        while state is not None:
            prev, edge, _, _ = self._info[state]
            nodes.append(state[0])
            if edge is not None:
                edges.append(Edge(edge.source, edge.dest, edge.distance, edge.line))
            state = prev
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        _, edges = self.path_with_edges(target)
        count = 0
        for a, b in zip(edges, edges[1:]):
            if a.line != b.line:
                count += 1
        return count
