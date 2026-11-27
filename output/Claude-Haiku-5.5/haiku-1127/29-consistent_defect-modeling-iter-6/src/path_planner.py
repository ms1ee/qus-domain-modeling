"""Grid-based path planning along city streets."""

import logging
import math
from collections import deque
from typing import Dict, List, Optional, Tuple

from grid_map import GridMap

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


class PathPlanner:
    """Plans street-following routes on the intersection lattice.

    Every route is a sequence of intersections where consecutive points are
    adjacent along a street, so riders only ever move horizontally or
    vertically and make right-angle turns at intersections.
    """

    def __init__(self, grid_map: Optional[GridMap] = None) -> None:
        """Create a planner.

        Args:
            grid_map: Map geometry to plan on. A default 800x800 map is used
                when omitted.
        """
        self.grid_map = grid_map if grid_map is not None else GridMap()
        self.grid_size = self.grid_map.grid_dimension

    def _floor_node(self, point: Point) -> Point:
        """Map a point to the intersection at or below-left of it."""
        x, y = point
        cell = self.grid_map.cell_size
        max_v = self.grid_map.map_size
        x = min(max(int(x), 0), max_v)
        y = min(max(int(y), 0), max_v)
        return ((x // cell) * cell, (y // cell) * cell)

    def is_straight(self, a: Point, b: Point) -> bool:
        """Return True when two points share a column or row.

        This is the special case where the rider moves in a straight line
        directly above or below (or beside) the target.
        """
        return a[0] == b[0] or a[1] == b[1]

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Compute a shortest street route from ``start`` to ``goal``.

        A breadth-first search over the intersection lattice is used. Because
        all moves follow streets, the route is always a valid right-angle path.

        Args:
            start: Starting point (rider location).
            goal: Destination point (restaurant or customer).

        Returns:
            List of intersections from start to goal, both included. A single
            element list is returned when start and goal coincide.

        Raises:
            ValueError: If no route exists (should not happen on the full grid).
        """
        s = self._floor_node(start)
        g = self._floor_node(goal)
        if s == g:
            return [s]

        parent: Dict[Point, Optional[Point]] = {s: None}
        queue = deque([s])
        while queue:
            current = queue.popleft()
            if current == g:
                break
            for nxt in self.grid_map.intersection_neighbors(current):
                if nxt not in parent:
                    parent[nxt] = current
                    queue.append(nxt)

        if g not in parent:
            raise ValueError(f"no street route from {s} to {g}")

        path: List[Point] = []
        node: Optional[Point] = g
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        logger.debug("planned route %s -> %s: %s", start, goal, path)
        return path

    def route_for_order(self, start: Point, restaurant: Point, customer: Point) -> List[Point]:
        """Return a continuous route: start -> restaurant -> customer.

        This is the multi-destination path used for pickup and delivery.
        The shared restaurant point is included only once.
        """
        leg1 = self.plan(start, restaurant)
        leg2 = self.plan(restaurant, customer)
        return leg1 + leg2[1:]

    def route_length(self, route: List[Point]) -> int:
        """Return the total street length of a route in units."""
        total = 0
        for (x1, y1), (x2, y2) in zip(route, route[1:]):
            total += abs(x2 - x1) + abs(y2 - y1)
        return total

    def estimate_ticks(self, route: List[Point], speed: int) -> int:
        """Estimate how many ticks a rider at ``speed`` needs to finish a route.

        Raises:
            ValueError: If speed is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        return math.ceil(self.route_length(route) / speed)
