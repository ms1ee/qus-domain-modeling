"""Grid-based path planning restricted to the street network.

Streets are the grid lines where ``x`` or ``y`` is a multiple of 100.
Restaurants and customers sit on street intersections (both coordinates are
multiples of 100). Routes are built from axis-aligned segments only, so every
movement is either straight or a right-angle turn.
"""

import math
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from config import CELL_SIZE, MAP_SIZE

Point = Tuple[int, int]


class PathPlanner:
    """Compute street-constrained routes between map points.

    The planner is stateless apart from the map geometry; congestion is
    supplied per call through an ``occupancy`` mapping so that riders can
    avoid crowded corners (conflict avoidance without blocking).
    """

    def __init__(self, map_size: int = MAP_SIZE, cell_size: int = CELL_SIZE) -> None:
        self.map_size = map_size
        self.cell_size = cell_size

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def is_intersection(self, point: Point) -> bool:
        """Return True if both coordinates are multiples of the cell size."""
        x, y = point
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def is_on_road(self, point: Point) -> bool:
        """Return True if the point lies on a street (grid line)."""
        x, y = point
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def in_bounds(self, point: Point) -> bool:
        """Return True if the point lies inside the map."""
        x, y = point
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    @staticmethod
    def manhattan(a: Point, b: Point) -> int:
        """Return the Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _street_neighbours(self, point: Point) -> List[Point]:
        """Return the two intersections bounding a point lying on a street."""
        x, y = point
        cs = self.cell_size
        if x % cs == 0 and y % cs != 0:
            low = (y // cs) * cs
            high = min(low + cs, self.map_size)
            return [(x, low), (x, high)]
        if y % cs == 0 and x % cs != 0:
            low = (x // cs) * cs
            high = min(low + cs, self.map_size)
            return [(low, y), (high, y)]
        return []

    @staticmethod
    def _dedupe(start: Point, points: Iterable[Point]) -> List[Point]:
        """Remove consecutive duplicate waypoints."""
        result: List[Point] = []
        previous = start
        for point in points:
            if point != previous:
                result.append(point)
                previous = point
        return result

    # ------------------------------------------------------------------
    # Route computation
    # ------------------------------------------------------------------
    def plan(
        self,
        start: Sequence[int],
        goal: Sequence[int],
        occupancy: Optional[Dict[Point, int]] = None,
    ) -> List[Point]:
        """Plan a street-constrained route from ``start`` to ``goal``.

        Special cases handled:
          * Start equals goal: empty route.
          * Goal directly above/below/left/right of the start: a single
            straight segment along the street.
          * Start not on an intersection: the rider first moves along its
            street to the nearest reachable intersection.
          * Otherwise an L-shaped route with a right-angle turn is produced;
            the corner with the lower congestion count is preferred.

        Args:
            start: Current rider position (must lie on a street).
            goal: Target position (must be a street intersection).
            occupancy: Optional mapping of point -> number of riders there.

        Returns:
            List of waypoints after ``start`` ending with ``goal``. The list
            is empty if no movement is required.

        Raises:
            ValueError: If the start is off-street or the goal is not an
                intersection.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if not self.is_on_road(start):
            raise ValueError(f"start {start} is not on a street")
        if not self.is_intersection(goal):
            raise ValueError(f"goal {goal} is not a street intersection")
        if start == goal:
            return []
        if start[0] == goal[0] or start[1] == goal[1]:
            # Special case: directly above/below or beside the target.
            return [goal]

        waypoints: List[Point] = []
        origin = start
        if not self.is_intersection(start):
            candidates = self._street_neighbours(start)
            origin = min(candidates, key=lambda p: self.manhattan(p, goal))
            waypoints.append(origin)
            if origin[0] == goal[0] or origin[1] == goal[1]:
                waypoints.append(goal)
                return self._dedupe(start, waypoints)

        occupancy = occupancy or {}
        corner_h = (goal[0], origin[1])   # horizontal first
        corner_v = (origin[0], goal[1])   # vertical first
        if occupancy.get(corner_v, 0) < occupancy.get(corner_h, 0):
            corner = corner_v
        else:
            corner = corner_h
        waypoints.extend([corner, goal])
        return self._dedupe(start, waypoints)

    def route_length(self, start: Sequence[int], waypoints: Iterable[Sequence[int]]) -> int:
        """Return the total Manhattan length of a waypoint chain.

        Args:
            start: Starting point of the chain.
            waypoints: Ordered waypoints following the start.

        Returns:
            Sum of segment lengths in map units.
        """
        total = 0
        current = (int(start[0]), int(start[1]))
        for point in waypoints:
            point = (int(point[0]), int(point[1]))
            total += self.manhattan(current, point)
            current = point
        return total

    def dense_path(
        self,
        start: Sequence[int],
        waypoints: Iterable[Sequence[int]],
        step: int = 25,
    ) -> List[Point]:
        """Expand a waypoint chain into evenly spaced points for drawing.

        Args:
            start: Starting point.
            waypoints: Ordered waypoints.
            step: Maximum distance between consecutive sampled points.

        Returns:
            List of integer points beginning with ``start``.
        """
        current = (int(start[0]), int(start[1]))
        points: List[Point] = [current]
        for waypoint in waypoints:
            target = (int(waypoint[0]), int(waypoint[1]))
            distance = self.manhattan(current, target)
            count = max(1, math.ceil(distance / step))
            for i in range(1, count + 1):
                t = i / count
                points.append((
                    round(current[0] + (target[0] - current[0]) * t),
                    round(current[1] + (target[1] - current[1]) * t),
                ))
            current = target
        return points


def random_road_point(rng: Optional[random.Random] = None) -> Point:
    """Return a random integer point located on a street.

    Args:
        rng: Optional random generator (defaults to the ``random`` module).

    Returns:
        ``(x, y)`` where one coordinate is a street line (multiple of 100)
        and the other is a random integer within the map.
    """
    rng = rng or random
    line = rng.randrange(0, MAP_SIZE // CELL_SIZE + 1) * CELL_SIZE
    other = rng.randint(0, MAP_SIZE)
    if rng.random() < 0.5:
        return line, other
    return other, line
