"""Grid-based path planning along streets.

Movement always follows the street network: horizontal moves first, then
vertical moves. A target lying directly above, below, left or right of the
rider is reached by a straight-line move (the special case). Riders never
block one another, and every move is monotone toward its target, so no
deadlock can occur.
"""

import math

import grid


class PathPlanner:
    """Static helpers for route computation and movement along streets."""

    @staticmethod
    def step_towards(x, y, tx, ty, budget):
        """Advance a point along the street grid by at most ``budget`` units.

        The horizontal leg is walked first, then the vertical leg. If the
        horizontal leg ends mid-tick, the remaining budget continues onto the
        vertical leg, so turns are right angles.

        Args:
            x: Current horizontal coordinate.
            y: Current vertical coordinate.
            tx: Target horizontal coordinate.
            ty: Target vertical coordinate.
            budget: Maximum distance to travel this tick.

        Returns:
            Tuple ``(new_x, new_y, leftover_budget)``.
        """
        while budget > 0 and (x, y) != (tx, ty):
            if x != tx:
                step = min(budget, abs(tx - x))
                x += step if tx > x else -step
            else:
                step = min(budget, abs(ty - y))
                y += step if ty > y else -step
            budget -= step
        return x, y, budget

    @staticmethod
    def is_straight_line(start, end):
        """Return True if ``end`` is directly above/below or left/right of ``start``.

        Args:
            start: Tuple ``(x, y)``.
            end: Tuple ``(x, y)``.
        """
        return start[0] == end[0] or start[1] == end[1]

    @staticmethod
    def plan_route(start, end):
        """Return the corner points of a street route from start to end.

        Straight-line targets (special case) produce a two-point route.
        Otherwise a single right-angle corner is inserted, horizontal first.

        Args:
            start: Tuple ``(x, y)``.
            end: Tuple ``(x, y)``.

        Returns:
            List of corner points beginning with ``start``.
        """
        points = [tuple(start)]
        sx, sy = start
        ex, ey = end
        if sx != ex and sy != ey:
            points.append((ex, sy))
        if points[-1] != (ex, ey):
            points.append((ex, ey))
        return points

    @staticmethod
    def plan_multi_route(start, stops):
        """Return a continuous route from start through several stops.

        Args:
            start: Tuple ``(x, y)`` of the starting point.
            stops: Iterable of tuples ``(x, y)`` visited in order.

        Returns:
            List of corner points with consecutive duplicates removed.
        """
        points = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            stop = tuple(stop)
            for point in PathPlanner.plan_route(current, stop)[1:]:
                if point != points[-1]:
                    points.append(point)
            current = stop
        return points

    @staticmethod
    def route_length(points):
        """Return the total Manhattan length of a corner-point route.

        Args:
            points: List of tuples ``(x, y)``.
        """
        return sum(
            grid.manhattan(a, b) for a, b in zip(points, points[1:])
        )

    @staticmethod
    def ticks_needed(distance, speed):
        """Return the number of ticks needed to cover a distance.

        Args:
            distance: Distance in map units.
            speed: Speed in units per tick (must be positive).

        Raises:
            ValueError: If speed is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        return int(math.ceil(distance / speed))
