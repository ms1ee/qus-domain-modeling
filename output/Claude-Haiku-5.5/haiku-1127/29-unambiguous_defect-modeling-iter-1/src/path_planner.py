"""Grid-based path planning.

Routes always follow streets: movement is axis-aligned, and when a rider must
change direction the corner is chosen so that the whole path lies on a
street. Straight segments (rider directly above/below or beside the target)
are handled as a special case.
"""

import logging

from grid_map import MapGrid

logger = logging.getLogger(__name__)


class PathPlanner:
    """Plans street-following routes and computes per-tick movement."""

    def __init__(self, grid=None):
        """Create a planner.

        Args:
            grid: Optional MapGrid describing the street layout.
        """
        self.grid = grid if grid is not None else MapGrid()

    def plan(self, start, target):
        """Plan a street-following path from start to target.

        Args:
            start: (x, y) current position, which must lie on a street.
            target: (x, y) destination intersection.

        Returns:
            List of corner points ending with target (start excluded). Empty
            if start equals target.
        """
        sx, sy = start
        tx, ty = target
        if (sx, sy) == (tx, ty):
            return []
        # Special case: directly above/below or beside the target.
        if sx == tx or sy == ty:
            return [(tx, ty)]
        cell = self.grid.cell_size
        horizontal_first = (tx, sy)
        vertical_first = (sx, ty)
        if sy % cell == 0 and self.grid.is_road(tx, sy):
            corner = horizontal_first
        elif sx % cell == 0 and self.grid.is_road(sx, ty):
            corner = vertical_first
        else:
            logger.warning("No street-only corner from %s to %s", start, target)
            corner = horizontal_first
        return [corner, (tx, ty)]

    def plan_route(self, start, stops):
        """Plan a route visiting several stops in order.

        Args:
            start: (x, y) starting position.
            stops: Ordered list of (x, y) destinations.

        Returns:
            List of points beginning with start, containing every corner and
            stop of the route.
        """
        points = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            stop = tuple(stop)
            points.extend(self.plan(current, stop))
            current = stop
        return points

    def step_toward(self, x, y, tx, ty, speed):
        """Advance a position along the planned route by at most speed units.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum distance to travel this tick.

        Returns:
            New (x, y) position after the movement.
        """
        if speed <= 0:
            return x, y
        budget = speed
        cur_x, cur_y = x, y
        for corner_x, corner_y in self.plan((x, y), (tx, ty)):
            while budget > 0 and (cur_x, cur_y) != (corner_x, corner_y):
                if cur_x != corner_x:
                    step = min(abs(corner_x - cur_x), budget)
                    cur_x += step if corner_x > cur_x else -step
                else:
                    step = min(abs(corner_y - cur_y), budget)
                    cur_y += step if corner_y > cur_y else -step
                budget -= step
            if budget <= 0:
                break
        return cur_x, cur_y

    @staticmethod
    def route_length(points):
        """Return the total Manhattan length of a point sequence.

        Args:
            points: List of (x, y) points.

        Returns:
            Sum of segment lengths as an integer.
        """
        total = 0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            total += abs(bx - ax) + abs(by - ay)
        return total
