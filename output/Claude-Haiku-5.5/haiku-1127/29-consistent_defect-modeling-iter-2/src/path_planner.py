"""Grid-based path planning for riders.

Riders travel only along streets (grid lines). Movement prefers horizontal
travel along the current street until the target column is reached, then
vertical travel along the target column. Multi-stop routes are produced as a
continuous polyline of right-angle turns.
"""

import math

from grid_map import GridMap


class PathPlanner:
    """Pathfinding helper operating on a :class:`GridMap`."""

    def __init__(self, grid=None):
        """Create a planner.

        Args:
            grid: Optional :class:`GridMap`; a default 800/100 map is used
                when omitted.
        """
        self.grid = grid if grid is not None else GridMap()

    @staticmethod
    def _step_toward(value, target, speed):
        """Move ``value`` toward ``target`` by at most ``speed`` units."""
        diff = target - value
        if abs(diff) <= speed:
            return target
        return value + speed if diff > 0 else value - speed

    def next_position(self, x, y, target_x, target_y, speed):
        """Compute the next position of a rider for one tick.

        Rules:
            * On a horizontal street (``y`` on a grid line) that is not yet in
              the target column, move horizontally toward the target column.
            * Otherwise move vertically toward the target row. This covers the
              case of being directly above/below the target (special case).

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            target_x: Target x coordinate.
            target_y: Target y coordinate.
            speed: Maximum distance to move this tick.

        Returns:
            Tuple ``(new_x, new_y, special_case)`` where ``special_case`` is
            True when the rider is directly above or below the target.

        Raises:
            ValueError: If ``speed`` is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        if x == target_x and y == target_y:
            return x, y, False

        cell = self.grid.cell_size
        if y % cell == 0 and x != target_x:
            return self._step_toward(x, target_x, speed), y, False

        new_y = self._step_toward(y, target_y, speed)
        special = x == target_x and new_y != target_y
        return x, new_y, special

    def _segment(self, start, end):
        """Return the right-angle polyline points from ``start`` to ``end``.

        The returned list excludes ``start`` and ends with ``end``.
        """
        if start == end:
            return []
        if start[0] == end[0] or start[1] == end[1]:
            return [end]
        cell = self.grid.cell_size
        if start[1] % cell == 0:
            corner = (end[0], start[1])
        else:
            corner = (start[0], end[1])
        return [corner, end]

    def plan_route(self, start, stops):
        """Plan a continuous route from ``start`` through each stop in order.

        Args:
            start: ``(x, y)`` starting position.
            stops: Iterable of ``(x, y)`` destinations (e.g. restaurant then
                customer).

        Returns:
            List of ``(x, y)`` points beginning with ``start``.
        """
        route = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            stop = tuple(stop)
            route.extend(self._segment(current, stop))
            current = stop
        return route

    @staticmethod
    def route_length(route):
        """Return the total Manhattan length of a polyline route."""
        total = 0
        for a, b in zip(route, route[1:]):
            total += abs(b[0] - a[0]) + abs(b[1] - a[1])
        return total

    @staticmethod
    def estimate_ticks(distance, speed):
        """Return the number of ticks needed to cover ``distance``."""
        if speed <= 0:
            raise ValueError("speed must be positive")
        return int(math.ceil(distance / speed))
