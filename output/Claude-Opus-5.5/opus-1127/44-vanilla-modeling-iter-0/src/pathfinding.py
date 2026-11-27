"""
Path calculation based on Dijkstra's algorithm.

The search runs on an expanded state space ``(station, current line,
transfers)`` so that transfers can be counted exactly, limited by
``max_transfers`` and minimised in the ``least_transfer`` mode.

Modes:
  * ``shortest_distance`` - minimise total distance (ties: fewer transfers)
  * ``least_transfer``    - minimise transfers (ties: shorter distance)
  * ``comprehensive``     - minimise distance + transfers * transfer penalty
"""

import math

from models import MinPQ

MODES = ("shortest_distance", "least_transfer", "comprehensive")

#: Distance-equivalent penalty (meters) of one transfer in comprehensive mode.
TRANSFER_PENALTY = 3000
#: Cost multiplier applied to edges on preferred lines.
PREFERRED_LINE_FACTOR = 0.8


class PathfindingConfig:
    """Configuration of a path query."""

    def __init__(self, mode="shortest_distance", max_transfers=None, preferred_lines=None,
                 transfer_penalty=TRANSFER_PENALTY, preference_factor=PREFERRED_LINE_FACTOR):
        if mode not in MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {', '.join(MODES)}")
        if max_transfers is not None and max_transfers < 0:
            raise ValueError("max_transfers must be non-negative")
        if isinstance(preferred_lines, str):
            preferred_lines = [preferred_lines]
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [l for l in (preferred_lines or []) if l]
        self.transfer_penalty = transfer_penalty
        self.preference_factor = preference_factor

    def __repr__(self):
        return (f"PathfindingConfig(mode={self.mode!r}, max_transfers={self.max_transfers!r}, "
                f"preferred_lines={self.preferred_lines!r})")


class _State:
    __slots__ = ("cost", "dist", "eff", "transfers", "parent", "edge")

    def __init__(self, cost, dist, eff, transfers, parent, edge):
        self.cost = cost
        self.dist = dist
        self.eff = eff
        self.transfers = transfers
        self.parent = parent
        self.edge = edge


class ShortestPath:
    """Single-source optimal paths on a ``Graph`` according to a config."""

    def __init__(self, graph, source, config=None):
        self.graph = graph
        self.source = source
        self.config = config if config is not None else PathfindingConfig()
        self.mode = self.config.mode
        self.max_transfers = self.config.max_transfers
        self.preferred_lines = set(self.config.preferred_lines)
        self.dist_to = {}
        self._states = {}
        self._best = {}
        self._run()

    # ----- internals ----------------------------------------------------
    def _cost(self, eff, transfers):
        if self.mode == "least_transfer":
            return (transfers, eff)
        if self.mode == "comprehensive":
            return (eff + transfers * self.config.transfer_penalty, transfers)
        return (eff, transfers)

    def _run(self):
        limit = self.max_transfers
        start = (self.source, None, 0)
        self._states[start] = _State(self._cost(0, 0), 0, 0, 0, None, None)
        pq = MinPQ()
        pq.push(self._states[start].cost, start)
        settled = set()
        adj = self.graph.adj

        while pq:
            _, key = pq.pop()
            if key in settled:
                continue
            settled.add(key)
            rec = self._states[key]
            v, line, _t = key
            for e in adj.get(v, []):
                w = e.other(v)
                nt = rec.transfers + (1 if (line is not None and e.line != line) else 0)
                if limit is not None and nt > limit:
                    continue
                nkey = (w, e.line, nt if limit is not None else 0)
                if nkey in settled:
                    continue
                factor = self.config.preference_factor if e.line in self.preferred_lines else 1
                neff = rec.eff + e.weight * factor
                ncost = self._cost(neff, nt)
                old = self._states.get(nkey)
                if old is None or ncost < old.cost:
                    self._states[nkey] = _State(ncost, rec.dist + e.weight, neff, nt, key, e)
                    pq.push(ncost, nkey)

        for key, rec in self._states.items():
            v = key[0]
            cur = self._best.get(v)
            if cur is None or rec.cost < self._states[cur].cost:
                self._best[v] = key
        self._best[self.source] = start
        for v, key in self._best.items():
            self.dist_to[v] = self._states[key].dist

    # ----- queries --------------------------------------------------------
    def has_path_to(self, target):
        return target in self._best

    def distance_to(self, target):
        return self.dist_to.get(target, math.inf)

    def path_with_edges(self, target):
        """Return ``(stations, edges)`` from source to target, or ``([], [])``."""
        if target not in self._best:
            return [], []
        edges = []
        key = self._best[target]
        while key is not None:
            rec = self._states[key]
            if rec.edge is not None:
                edges.append(rec.edge)
            key = rec.parent
        edges.reverse()
        stations = [self.source]
        cur = self.source
        for e in edges:
            cur = e.other(cur)
            stations.append(cur)
        return stations, edges

    def path_to(self, target):
        return self.path_with_edges(target)[0]

    def get_transfer_count(self, target):
        """Transfers on the chosen path to ``target`` (-1 if unreachable)."""
        if target not in self._best:
            return -1
        return self._states[self._best[target]].transfers

    def get_lines(self, target):
        """Ordered list of distinct lines used on the path to ``target``."""
        _, edges = self.path_with_edges(target)
        return list(dict.fromkeys(e.line for e in edges))
