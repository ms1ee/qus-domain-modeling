"""Grid-based path planning with a preference for streets.

The routing lattice has a node every 50 units. Edges along street lines
(coordinates that are multiples of 100) are cheap. Entering or leaving the
block of a restaurant or customer (the "driveway", i.e. a rider directly above
or below the target) is allowed but costs more, so routes prefer streets.
"""

import heapq
import itertools
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from grid import CELL_SIZE, LATTICE_STEP, MAP_SIZE, GridMap, is_street_point

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


class PathNotFoundError(Exception):
    """Raised when no route exists between two points."""


@dataclass
class Route:
    """A planned route.

    Attributes:
        route_id: Unique identifier of the route.
        points: Ordered lattice points, including start and goal.
        total_distance: Total Manhattan length in units.
        estimated_ticks: Ticks needed at the planned speed.
        has_driveway: True if the route uses a non-street final approach
            (special case: target directly above or below the rider).
    """

    route_id: int
    points: List[Point]
    total_distance: int
    estimated_ticks: int
    has_driveway: bool = False

    @property
    def special_case(self) -> bool:
        """Alias of ``has_driveway`` used by the rider special-case flag."""
        return self.has_driveway


class PathPlanner:
    """Computes street-preferring routes on the 8x8 grid."""

    STREET_COST = 1
    DRIVEWAY_COST = 2

    def __init__(self, grid: Optional[GridMap] = None) -> None:
        """Create a planner.

        Args:
            grid: Grid map to plan on. A default 8x8 map is created if omitted.
        """
        self.grid = grid if grid is not None else GridMap()
        self.grid_size = self.grid.dimension
        self.prefer_streets = True
        self.step = LATTICE_STEP
        self._route_ids = itertools.count(1)

    def nearest_lattice(self, point: Point) -> Point:
        """Snap a point to the nearest routing-lattice node inside the map."""
        x, y = point
        lx = min(max(int(round(x / self.step)) * self.step, 0), self.grid.width)
        ly = min(max(int(round(y / self.step)) * self.step, 0), self.grid.height)
        return lx, ly

    def plan(self, start: Point, goal: Point, speed: int = 1) -> Route:
        """Plan a route from ``start`` to ``goal``.

        Args:
            start: Starting coordinates.
            goal: Destination coordinates (usually a cell centre).
            speed: Rider speed in units per tick, used for the tick estimate.

        Returns:
            A Route describing the path.

        Raises:
            ValueError: If speed is not positive.
            PathNotFoundError: If no route exists.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        start_node = self.nearest_lattice(start)
        goal_node = self.nearest_lattice(goal)
        if start_node == goal_node:
            return Route(next(self._route_ids), [start_node], 0, 0, False)

        previous = self._dijkstra(start_node, goal_node)
        points = [goal_node]
        while points[-1] != start_node:
            points.append(previous[points[-1]])
        points.reverse()

        total = 0
        driveway = False
        for a, b in zip(points, points[1:]):
            total += abs(b[0] - a[0]) + abs(b[1] - a[1])
            if not self._is_street_edge(a, b):
                driveway = True
        ticks = int(math.ceil(total / speed))
        return Route(next(self._route_ids), points, total, ticks, driveway)

    def plan_multi(self, start: Point, destinations: Sequence[Point],
                   speed: int = 1) -> Route:
        """Plan a continuous route through several destinations in order.

        Used for the restaurant-then-customer path of an order.

        Args:
            start: Starting coordinates.
            destinations: Ordered list of waypoints.
            speed: Rider speed in units per tick.

        Returns:
            A single Route covering all legs.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        points: List[Point] = [self.nearest_lattice(start)]
        total = 0
        driveway = False
        for destination in destinations:
            leg = self.plan(points[-1], destination, speed)
            points.extend(leg.points[1:])
            total += leg.total_distance
            driveway = driveway or leg.has_driveway
        ticks = int(math.ceil(total / speed))
        return Route(next(self._route_ids), points, total, ticks, driveway)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _is_street_edge(self, a: Point, b: Point) -> bool:
        """Return True if the lattice edge a-b lies on a street line."""
        if a[1] == b[1]:
            return is_street_point(0, a[1], self.grid.cell_size)
        return is_street_point(a[0], 0, self.grid.cell_size)

    def _neighbors(self, node: Point) -> List[Point]:
        """Return the lattice neighbours of a node that lie inside the map."""
        x, y = node
        result = []
        for dx, dy in ((self.step, 0), (-self.step, 0), (0, self.step), (0, -self.step)):
            nx, ny = x + dx, y + dy
            if self.grid.contains(nx, ny):
                result.append((nx, ny))
        return result

    def _edge_allowed(self, a: Point, b: Point, start: Point, goal: Point) -> bool:
        """Edges are allowed on streets, or as driveways touching start/goal."""
        if self._is_street_edge(a, b):
            return True
        return a in (start, goal) or b in (start, goal)

    def _dijkstra(self, start: Point, goal: Point) -> Dict[Point, Point]:
        """Run Dijkstra's algorithm and return the predecessor map.

        Raises:
            PathNotFoundError: If the goal cannot be reached.
        """
        dist: Dict[Point, int] = {start: 0}
        previous: Dict[Point, Point] = {}
        heap: List[Tuple[int, Point]] = [(0, start)]
        while heap:
            cost_so_far, node = heapq.heappop(heap)
            if node == goal:
                break
            if cost_so_far > dist.get(node, math.inf):
                continue
            for neighbor in self._neighbors(node):
                if not self._edge_allowed(node, neighbor, start, goal):
                    continue
                step_cost = (self.STREET_COST if self._is_street_edge(node, neighbor)
                             else self.DRIVEWAY_COST)
                new_cost = cost_so_far + step_cost
                if new_cost < dist.get(neighbor, math.inf):
                    dist[neighbor] = new_cost
                    previous[neighbor] = node
                    heapq.heappush(heap, (new_cost, neighbor))
        if goal not in dist:
            raise PathNotFoundError(f"no route from {start} to {goal}")
        return previous
