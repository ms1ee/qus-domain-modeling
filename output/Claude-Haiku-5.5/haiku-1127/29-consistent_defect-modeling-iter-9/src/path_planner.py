"""Grid-based path planning for riders.

Routes follow streets: every leg is axis-aligned and the planner prefers
the L-shaped corner that keeps the first leg on a street. Riders may share
street segments; they never block each other, which rules out deadlock.
"""

import logging
from typing import List, Optional, Sequence, Tuple

from grid_map import GridMap

logger = logging.getLogger("dispatch.path")

Point = Tuple[int, int]


class PathPlanner:
    """Computes and advances street-constrained routes."""

    def __init__(self, grid_map: Optional[GridMap] = None) -> None:
        """Create a planner bound to a grid map.

        Args:
            grid_map: Map to plan on; defaults to the 8x8 city grid.
        """
        self.grid = grid_map or GridMap()
        self.grid_size = self.grid.grid_dimension
        self.cell_size = self.grid.cell_size

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Plan a route from start to goal, excluding the start point.

        Special cases:
            * start == goal: empty route.
            * goal directly above/below or left/right of start: straight line.
            * otherwise: one right-angle corner, chosen to keep the first
              leg on a street.

        Args:
            start: Current (x, y) position.
            goal: Destination (x, y) position.

        Returns:
            List of waypoints ending at goal (empty if already there).
        """
        sx, sy = start
        gx, gy = goal
        if (sx, sy) == (gx, gy):
            return []
        if sx == gx or sy == gy:
            return [(gx, gy)]
        cs = self.cell_size
        horizontal_first_ok = sy % cs == 0
        vertical_first_ok = sx % cs == 0
        if horizontal_first_ok or not vertical_first_ok:
            corner = (gx, sy)
        else:
            corner = (sx, gy)
        return [corner, (gx, gy)]

    def plan_sequence(self, start: Point, destinations: Sequence[Point]) -> List[Point]:
        """Plan a continuous route visiting several destinations.

        Destinations are visited nearest-first (Manhattan distance), which
        minimises backtracking for multi-stop trips.

        Args:
            start: Starting (x, y) position.
            destinations: Points to visit.

        Returns:
            Concatenated waypoint list.
        """
        path: List[Point] = []
        current = start
        remaining = list(destinations)
        while remaining:
            nxt = min(remaining, key=lambda d: abs(d[0] - current[0]) + abs(d[1] - current[1]))
            remaining.remove(nxt)
            path.extend(self.plan(current, nxt))
            current = nxt
        return path

    def advance(self, position: Point, path: Sequence[Point], speed: int) -> Tuple[Point, List[Point]]:
        """Move along a planned path by up to ``speed`` units.

        Args:
            position: Current (x, y) position.
            path: Remaining waypoints.
            speed: Maximum movement in units for this tick.

        Returns:
            Tuple (new_position, remaining_waypoints).
        """
        x, y = position
        remaining_speed = int(speed)
        waypoints = list(path)
        while remaining_speed > 0 and waypoints:
            tx, ty = waypoints[0]
            if (x, y) == (tx, ty):
                waypoints.pop(0)
                continue
            if x != tx and y != ty:
                # Defensive: insert a corner so movement stays on streets.
                waypoints.insert(0, (tx, y))
                continue
            if y == ty:
                step = min(abs(tx - x), remaining_speed)
                x += step if tx > x else -step
            else:
                step = min(abs(ty - y), remaining_speed)
                y += step if ty > y else -step
            remaining_speed -= step
        return (x, y), waypoints

    @staticmethod
    def route_length(start: Point, path: Sequence[Point]) -> int:
        """Return the total travelled length of a waypoint path.

        Args:
            start: Starting position.
            path: Waypoints in order.
        """
        total = 0
        current = start
        for point in path:
            total += abs(point[0] - current[0]) + abs(point[1] - current[1])
            current = point
        return total
