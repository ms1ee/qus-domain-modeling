"""Grid-based path planning for riders on the street network.

The city is an 800x800 unit map divided into 8x8 cells of 100x100 units.
Streets are the grid lines where the x or y coordinate is a multiple of
100. Restaurants and customers sit on intersections (both coordinates are
multiples of 100). Riders always travel along streets.
"""

import logging
from typing import List, Sequence, Tuple

Point = Tuple[int, int]

CELL_SIZE = 100
MAP_SIZE = 800

logger = logging.getLogger(__name__)


class PathPlanner:
    """Plans axis-aligned routes that follow the street grid.

    Every planned route contains at most one right-angle turn. Each leg is
    either horizontal or vertical, so a rider never leaves the streets.

    Special cases:
        * Target directly above/below/left/right of the rider: a straight
          single-leg route is used.
        * Rider already at the target: an empty route is returned.

    Deadlock avoidance: riders never block one another. Each rider's
    movement depends only on its own route, so no circular wait can form.
    """

    @staticmethod
    def is_on_street(point: Sequence[int]) -> bool:
        """Return True if ``point`` lies on a street (grid line)."""
        x, y = int(point[0]), int(point[1])
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_intersection(point: Sequence[int]) -> bool:
        """Return True if ``point`` is a grid intersection."""
        x, y = int(point[0]), int(point[1])
        return x % CELL_SIZE == 0 and y % CELL_SIZE == 0

    @staticmethod
    def is_special_case(start: Sequence[int], goal: Sequence[int]) -> bool:
        """Return True when ``goal`` is directly above, below, left or right
        of ``start`` (a straight-line route)."""
        return start[0] == goal[0] or start[1] == goal[1]

    @classmethod
    def plan(cls, start: Sequence[int], goal: Sequence[int]) -> List[Point]:
        """Plan a street route from ``start`` to ``goal``.

        The returned list contains the waypoints after ``start`` (the corner
        point, when a turn is needed, followed by ``goal``). An empty list is
        returned when start and goal coincide.

        Args:
            start: Current (x, y) position.
            goal: Destination (x, y) position.

        Returns:
            List of (x, y) waypoints, ending with ``goal``.
        """
        sx, sy = int(start[0]), int(start[1])
        gx, gy = int(goal[0]), int(goal[1])
        if (sx, sy) == (gx, gy):
            return []
        if sx == gx or sy == gy:
            # Special case: directly above/below or left/right of the target.
            return [(gx, gy)]
        if sy % CELL_SIZE == 0:
            # Rider is on a horizontal street: travel horizontally first.
            corner = (gx, sy)
        elif sx % CELL_SIZE == 0:
            # Rider is on a vertical street: travel vertically first.
            corner = (sx, gy)
        else:
            # Should not happen, because riders always stay on streets.
            logger.warning("Off-street start %s; using fallback corner", start)
            corner = (gx, sy)
        return [corner, (gx, gy)]

    @classmethod
    def plan_route(cls, start: Sequence[int], stops: Sequence[Sequence[int]]) -> List[Point]:
        """Plan a continuous route through several destinations in order.

        Consecutive legs are chained so that the end of one leg is the start
        of the next. Duplicate waypoints are removed.

        Args:
            start: Starting (x, y) position.
            stops: Ordered list of (x, y) destinations.

        Returns:
            Combined list of waypoints.
        """
        route: List[Point] = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            stop_point = (int(stop[0]), int(stop[1]))
            for waypoint in cls.plan(current, stop_point):
                if not route or route[-1] != waypoint:
                    route.append(waypoint)
            current = stop_point
        return route

    @staticmethod
    def route_length(start: Sequence[int], route: Sequence[Sequence[int]]) -> int:
        """Return the total travelled Manhattan length of ``route``.

        Args:
            start: Starting (x, y) position.
            route: Waypoints produced by ``plan``.

        Returns:
            Total distance in units.
        """
        total = 0
        cx, cy = int(start[0]), int(start[1])
        for wx, wy in route:
            total += abs(wx - cx) + abs(wy - cy)
            cx, cy = wx, wy
        return total

    @staticmethod
    def trace_points(start: Sequence[int], route: Sequence[Sequence[int]]) -> List[Point]:
        """Return every integer point along ``route``, excluding ``start``.

        Args:
            start: Starting (x, y) position.
            route: Waypoints produced by ``plan`` or ``plan_route``.

        Returns:
            List of integer (x, y) points along the route.
        """
        points: List[Point] = []
        cx, cy = int(start[0]), int(start[1])
        for wx, wy in route:
            if cy == wy and cx != wx:
                step = 1 if wx > cx else -1
                points.extend((x, cy) for x in range(cx + step, wx + step, step))
            elif cx == wx and cy != wy:
                step = 1 if wy > cy else -1
                points.extend((cx, y) for y in range(cy + step, wy + step, step))
            cx, cy = wx, wy
        return points
