"""Grid-based path planning.

Paths are computed with Dijkstra's algorithm on the 50-unit lattice. Edges
that lie on streets are cheap; off-street edges are only usable when they
touch the start or goal location, which keeps riders on roads except for the
last metre into a restaurant or customer cell. Occupied nodes add a penalty so
that riders spread out instead of queuing on the same point.
"""

import heapq
import logging

from grid import MAP_SIZE, LATTICE_STEP, CELL_SIZE

logger = logging.getLogger("dispatch.path_planner")

_DIRECTIONS = ((LATTICE_STEP, 0), (-LATTICE_STEP, 0), (0, LATTICE_STEP), (0, -LATTICE_STEP))
_INF = float("inf")


class PathPlanner:
    """Plans street-prioritising routes between two points on the map.

    Attributes:
        prioritize_streets (bool): When True, street edges are much cheaper
            than off-street edges.
    """

    STREET_COST = 1
    OFF_STREET_COST = 4
    OCCUPIED_PENALTY = 2

    def __init__(self, prioritize_streets=True):
        """Create a planner.

        Args:
            prioritize_streets: Whether street edges should be preferred.
        """
        self.prioritize_streets = prioritize_streets

    @staticmethod
    def is_street_edge(a, b):
        """Return True if the lattice edge a-b lies on a street.

        Args:
            a: First lattice node (x, y).
            b: Second adjacent lattice node (x, y).

        Returns:
            bool: True for horizontal edges on a y grid line or vertical edges
            on an x grid line.
        """
        if a[1] == b[1]:
            return a[1] % CELL_SIZE == 0
        return a[0] % CELL_SIZE == 0

    def _edge_cost(self, a, b, occupied, goal):
        """Compute the traversal cost of moving from a to b.

        Args:
            a: Source node.
            b: Destination node.
            occupied: Set of points currently occupied by other riders.
            goal: The planning goal (never penalised).

        Returns:
            int: Cost of the edge.
        """
        if self.prioritize_streets and not self.is_street_edge(a, b):
            cost = self.OFF_STREET_COST
        elif self.prioritize_streets:
            cost = self.STREET_COST
        else:
            cost = 1
        if b in occupied and b != goal:
            cost += self.OCCUPIED_PENALTY
        return cost

    def plan(self, start, goal, occupied=None):
        """Compute a route from ``start`` to ``goal``.

        Args:
            start: Starting (x, y) point.
            goal: Target (x, y) point.
            occupied: Optional iterable of (x, y) points used by other riders.

        Returns:
            list[tuple]: Ordered list of points from start to goal, inclusive.
            If no route is found a direct two-point fallback is returned.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return [start]
        occupied = set(occupied or ())
        specials = {start, goal}
        dist = {start: 0}
        prev = {}
        heap = [(0, start)]
        while heap:
            cost, node = heapq.heappop(heap)
            if node == goal:
                break
            if cost > dist.get(node, _INF):
                continue
            for dx, dy in _DIRECTIONS:
                nb = (node[0] + dx, node[1] + dy)
                if not (0 <= nb[0] <= MAP_SIZE and 0 <= nb[1] <= MAP_SIZE):
                    continue
                street = self.is_street_edge(node, nb)
                if not street and node not in specials and nb not in specials:
                    continue
                new_cost = cost + self._edge_cost(node, nb, occupied, goal)
                if new_cost < dist.get(nb, _INF):
                    dist[nb] = new_cost
                    prev[nb] = node
                    heapq.heappush(heap, (new_cost, nb))
        if goal not in prev:
            logger.warning("no route found from %s to %s; using direct fallback", start, goal)
            return [start, goal]
        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path
