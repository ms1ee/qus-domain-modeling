"""Grid-based path planning for the 800x800 map.

Coordinate model:
    * The map spans 0..800 on both axes with 100-unit cells (8x8 cells).
    * Points whose x or y is a multiple of 100 lie on a street.
    * Points where both coordinates are multiples of 100 are intersections
      (restaurant and customer locations are always intersections).
    * Riders may stand anywhere on a street, including mid-block positions
      that are multiples of 50.
"""

import random


class PathPlanner:
    """Plans street-following routes on the grid.

    The planner prefers streets: every route segment keeps the traveller on
    a grid line, and moves are either purely horizontal or purely vertical.
    """

    prefers_streets = True
    MAP_SIZE = 800
    CELL_SIZE = 100
    SPAWN_STEP = 50

    @staticmethod
    def is_on_street(x, y):
        """Return True if the point ``(x, y)`` lies on a street grid line."""
        return x % PathPlanner.CELL_SIZE == 0 or y % PathPlanner.CELL_SIZE == 0

    @staticmethod
    def next_step(x, y, tx, ty):
        """Return the next single-unit position moving from ``(x, y)`` to ``(tx, ty)``.

        The rule keeps the traveller on streets:
            * On a vertical street (x is a multiple of 100) move vertically
              until the target's y is reached ("directly above or below" case).
            * Otherwise move horizontally along the current horizontal street.
            * Finally move vertically along the target's vertical street.

        Args:
            x, y: Current position.
            tx, ty: Target position (an intersection).

        Returns:
            Tuple ``(nx, ny)`` of the next position. Returns ``(x, y)`` when
            already at the target.
        """
        if (x, y) == (tx, ty):
            return x, y
        cell = PathPlanner.CELL_SIZE
        if x % cell == 0 and y != ty:
            return x, y + (1 if ty > y else -1)
        if x != tx:
            return x + (1 if tx > x else -1), y
        return x, y + (1 if ty > y else -1)

    def plan(self, start, goal):
        """Plan a street-following route from ``start`` to ``goal``.

        Args:
            start: Tuple ``(x, y)`` of the start point.
            goal: Tuple ``(x, y)`` of the destination intersection.

        Returns:
            List of waypoints (tuples) including ``start`` and ``goal``.
        """
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return self._dedupe([tuple(start), tuple(goal)])
        if sx % self.CELL_SIZE == 0:
            corner = (sx, gy)
        else:
            corner = (gx, sy)
        return self._dedupe([tuple(start), corner, tuple(goal)])

    def plan_route(self, start, stops):
        """Plan a continuous route through several destinations in order.

        Args:
            start: Starting point ``(x, y)``.
            stops: Ordered list of destination points.

        Returns:
            List of waypoints covering the whole multi-stop route.
        """
        points = [tuple(start)]
        current = tuple(start)
        for stop in stops:
            segment = self.plan(current, stop)
            points.extend(segment[1:])
            current = tuple(stop)
        return points

    @staticmethod
    def path_length(points):
        """Return the total Manhattan length of a waypoint list."""
        total = 0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            total += abs(bx - ax) + abs(by - ay)
        return total

    @staticmethod
    def estimate_ticks(distance, speed):
        """Return the number of ticks needed to cover ``distance`` at ``speed``.

        Args:
            distance: Route length in map units.
            speed: Rider speed in units per tick.

        Returns:
            Integer number of ticks (ceiling division), 0 if distance is 0.
        """
        if speed <= 0 or distance <= 0:
            return 0
        return -(-distance // speed)

    @staticmethod
    def random_road_point(rng=random):
        """Return a random integer point located on a road.

        Args:
            rng: Random number generator exposing ``random``, ``randint``
                and ``randrange``.

        Returns:
            Tuple ``(x, y)`` on a street.
        """
        step = PathPlanner.SPAWN_STEP
        cell = PathPlanner.CELL_SIZE
        max_block = PathPlanner.MAP_SIZE // cell
        if rng.random() < 0.5:
            return rng.randint(0, max_block) * cell, rng.randrange(0, PathPlanner.MAP_SIZE + 1, step)
        return rng.randrange(0, PathPlanner.MAP_SIZE + 1, step), rng.randint(0, max_block) * cell

    @staticmethod
    def _dedupe(points):
        """Remove consecutive duplicate waypoints."""
        result = []
        for point in points:
            if not result or result[-1] != point:
                result.append(point)
        return result
