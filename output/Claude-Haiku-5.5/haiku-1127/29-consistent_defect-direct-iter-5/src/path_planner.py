"""Grid-based path planning for the food delivery simulator.

The city is an 800x800 unit map divided into 8x8 cells of 100x100 units.
Grid lines (coordinates that are multiples of 100) are streets. Restaurant
and customer locations sit on integer-hundred points, which are street
intersections. Riders always move along streets: horizontally or vertically,
turning at right angles only at intersections.

Route convention (shared by movement and route drawing so they never
disagree): when moving from a point ``a`` to a point ``b``, the rider goes
horizontally first if ``a`` lies on a horizontal street (``a.y % 100 == 0``),
otherwise vertically first.
"""

import logging
import math

logger = logging.getLogger(__name__)

CELL_SIZE = 100
MAP_SIZE = 800


def _step_towards(current, target, speed):
    """Move ``current`` toward ``target`` by at most ``speed`` units.

    Args:
        current: Current coordinate value.
        target: Target coordinate value.
        speed: Maximum step size (positive integer).

    Returns:
        The new coordinate value, never overshooting ``target``.
    """
    delta = target - current
    if abs(delta) <= speed:
        return target
    return current + speed if delta > 0 else current - speed


class PathPlanner:
    """Pathfinding logic for riders on the street grid.

    All methods are stateless; the class groups the grid-based algorithm,
    the special-case handling and the multi-destination route construction.
    """

    @staticmethod
    def snap_point(x, y):
        """Convert raw coordinates to the top-left corner of their grid cell.

        Each coordinate ``v`` becomes ``(v // 100) * 100`` and is clamped to
        the map range [0, 800]. Values outside the map are clamped, so the
        result is always a valid integer-hundred point.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Tuple ``(snapped_x, snapped_y)`` of integers.
        """
        def snap(value):
            cell = int(value) // CELL_SIZE * CELL_SIZE
            return max(0, min(MAP_SIZE, cell))

        return snap(x), snap(y)

    @staticmethod
    def manhattan(a, b):
        """Return the Manhattan (street) distance between two points.

        Args:
            a: Tuple ``(x, y)``.
            b: Tuple ``(x, y)``.

        Returns:
            Integer distance ``|ax - bx| + |ay - by|``.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a, b):
        """Return the straight-line distance ``sqrt(dx^2 + dy^2)``.

        Args:
            a: Tuple ``(x, y)``.
            b: Tuple ``(x, y)``.

        Returns:
            Float Euclidean distance.
        """
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def is_on_street(point):
        """Return True if the point lies on a street (grid line).

        Args:
            point: Tuple ``(x, y)``.

        Returns:
            True when ``x`` or ``y`` is a multiple of the cell size.
        """
        return point[0] % CELL_SIZE == 0 or point[1] % CELL_SIZE == 0

    @staticmethod
    def corner_point(start, end):
        """Return the right-angle corner used when travelling ``start`` to ``end``.

        Args:
            start: Tuple ``(x, y)`` where the leg begins.
            end: Tuple ``(x, y)`` where the leg finishes.

        Returns:
            Tuple ``(x, y)`` of the turning point. It equals ``start`` or
            ``end`` when the two points are already aligned.
        """
        if start[1] % CELL_SIZE == 0:
            return end[0], start[1]
        return start[0], end[1]

    @staticmethod
    def next_position(x, y, target_x, target_y, speed):
        """Advance a rider one tick toward a target along the streets.

        Special cases handled:
          * Target directly above/below (same x): move vertically only.
          * Target directly left/right (same y): move horizontally only.
          * General case: follow the route convention (see module docstring).

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            target_x: Target x coordinate.
            target_y: Target y coordinate.
            speed: Movement budget for this tick (units/tick, positive).

        Returns:
            Tuple ``(new_x, new_y, arrived)`` where ``arrived`` is True when
            the rider stands exactly on the target after this step.

        Raises:
            ValueError: If ``speed`` is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be a positive integer")
        if x == target_x and y == target_y:
            return x, y, True

        if y == target_y:
            new_x, new_y = _step_towards(x, target_x, speed), y
        elif x == target_x:
            new_x, new_y = x, _step_towards(y, target_y, speed)
        elif y % CELL_SIZE == 0:
            new_x, new_y = _step_towards(x, target_x, speed), y
        else:
            new_x, new_y = x, _step_towards(y, target_y, speed)

        arrived = new_x == target_x and new_y == target_y
        return new_x, new_y, arrived

    @classmethod
    def build_route(cls, start, stops):
        """Build the ordered list of route points through several stops.

        Used for multi-destination paths, e.g. start -> restaurant -> customer.

        Args:
            start: Tuple ``(x, y)`` where the rider currently is.
            stops: Iterable of ``(x, y)`` destinations, visited in order.

        Returns:
            List of ``(x, y)`` points starting with ``start``, including the
            right-angle corners between consecutive points.
        """
        current = tuple(start)
        points = [current]
        for stop in stops:
            stop = tuple(stop)
            corner = cls.corner_point(current, stop)
            if corner != current and corner != stop:
                points.append(corner)
            if stop != points[-1]:
                points.append(stop)
            current = stop
        return points

    @classmethod
    def route_length(cls, points):
        """Return the total street length of a route.

        Args:
            points: List of ``(x, y)`` route points.

        Returns:
            Integer total Manhattan length of consecutive segments.
        """
        return sum(cls.manhattan(a, b) for a, b in zip(points, points[1:]))

    @classmethod
    def estimate_ticks(cls, points, speed):
        """Estimate the number of ticks needed to travel a route.

        Args:
            points: List of ``(x, y)`` route points.
            speed: Rider speed in units per tick (positive).

        Returns:
            Integer number of ticks (rounded up).

        Raises:
            ValueError: If ``speed`` is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be a positive integer")
        return int(math.ceil(cls.route_length(points) / speed))
