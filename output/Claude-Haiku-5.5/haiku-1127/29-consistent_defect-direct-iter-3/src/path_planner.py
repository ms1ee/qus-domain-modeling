"""Grid-based path planning on the 800x800 street map.

Streets are the lines where ``x`` or ``y`` is a multiple of 100. Riders move
along streets with right-angle turns only. Restaurants and customers sit at
street intersections (points whose coordinates are both multiples of 100).
"""

import math
from typing import List, Tuple

from config import CELL_SIZE, GRID_CELLS, MAP_SIZE

Point = Tuple[int, int]


class PathPlanner:
    """Static helper class implementing street-following pathfinding.

    The planner always stays on streets: when travelling along a horizontal
    street it only changes ``x``; when travelling along a vertical street it
    only changes ``y``. At an intersection it prefers horizontal movement
    first, producing a deterministic right-angle route. Because the route is
    deterministic and riders never block each other, no deadlock can occur.
    """

    @staticmethod
    def snap(value: int) -> int:
        """Convert a raw coordinate to the top-left corner of its grid cell.

        Values are clamped to [0, MAP_SIZE]. Values at or beyond the map edge
        map to the edge intersection (800).

        Args:
            value: Raw coordinate.

        Returns:
            The snapped coordinate, a multiple of ``CELL_SIZE``.
        """
        clamped = max(0, min(int(value), MAP_SIZE))
        cell = min(clamped // CELL_SIZE, GRID_CELLS)
        return cell * CELL_SIZE

    @classmethod
    def snap_point(cls, x: int, y: int) -> Point:
        """Snap both coordinates of a point to grid corners.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Tuple ``(x, y)`` of snapped coordinates.
        """
        return cls.snap(x), cls.snap(y)

    @staticmethod
    def is_street(x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_intersection(x: int, y: int) -> bool:
        """Return True if the point is a street intersection."""
        return x % CELL_SIZE == 0 and y % CELL_SIZE == 0

    @staticmethod
    def manhattan(a: Point, b: Point) -> int:
        """Return the Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a: Point, b: Point) -> float:
        """Return the Euclidean distance between two points."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def next_position(x: int, y: int, tx: int, ty: int, speed: int) -> Point:
        """Compute the position after one tick of movement toward a target.

        Movement rules:
          * If the rider is directly above or below the target (same x), it
            moves only vertically.
          * If the rider is directly left or right of the target (same y), it
            moves only horizontally.
          * If the rider is on a vertical street, it keeps moving vertically.
          * Otherwise (horizontal street or intersection) it moves horizontally
            first.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum distance to move this tick (units).

        Returns:
            The new ``(x, y)`` position; never overshoots the target.

        Raises:
            ValueError: If ``speed`` is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        if x == tx and y == ty:
            return x, y

        if x == tx:
            axis = "y"
        elif y == ty:
            axis = "x"
        else:
            on_vertical = x % CELL_SIZE == 0
            on_horizontal = y % CELL_SIZE == 0
            axis = "y" if (on_vertical and not on_horizontal) else "x"

        if axis == "x":
            delta = tx - x
            step = min(speed, abs(delta))
            return (x + step if delta > 0 else x - step), y
        delta = ty - y
        step = min(speed, abs(delta))
        return x, (y + step if delta > 0 else y - step)

    @classmethod
    def plan_route(cls, start: Point, end: Point) -> List[Point]:
        """Plan a right-angle street route from ``start`` to ``end``.

        Args:
            start: Starting point.
            end: Destination point.

        Returns:
            List of corner points beginning with ``start`` and ending with
            ``end``. A route with no movement returns ``[start]``.
        """
        points: List[Point] = [start]
        x, y = start
        guard = 0
        while (x, y) != end and guard < 4:
            x, y = cls.next_position(x, y, end[0], end[1], MAP_SIZE * 2)
            points.append((x, y))
            guard += 1
        return points

    @classmethod
    def plan_trip(cls, rider_pos: Point, restaurant: Point, customer: Point) -> List[Point]:
        """Plan a continuous route: rider -> restaurant -> customer.

        This is the multi-destination path used for the route map. The two
        legs are joined without duplicating the restaurant point.

        Args:
            rider_pos: Current rider position.
            restaurant: Restaurant grid point.
            customer: Customer grid point.

        Returns:
            Ordered list of corner points for the whole trip.
        """
        to_restaurant = cls.plan_route(rider_pos, restaurant)
        to_customer = cls.plan_route(restaurant, customer)
        return to_restaurant + to_customer[1:]

    @staticmethod
    def route_length(points: List[Point]) -> int:
        """Return the total street length of a route of corner points."""
        total = 0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            total += abs(ax - bx) + abs(ay - by)
        return total

    @staticmethod
    def estimate_ticks(distance: int, speed: int) -> int:
        """Estimate the number of ticks needed to cover a distance.

        Args:
            distance: Route length in units.
            speed: Speed in units per tick (must be positive).

        Returns:
            Ceiling of ``distance / speed``; 0 for zero distance.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        if distance <= 0:
            return 0
        return (distance + speed - 1) // speed
