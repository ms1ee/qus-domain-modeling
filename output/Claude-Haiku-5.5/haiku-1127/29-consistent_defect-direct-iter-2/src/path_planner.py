"""Grid-based path planning for riders on the 800x800 street map.

The map is divided into 100x100 unit cells. Streets are the grid lines where
either the x or the y coordinate is a multiple of 100. Riders prefer to travel
along streets, using right-angle turns between straight segments.
"""

from typing import List, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100


def is_on_street(x: int, y: int) -> bool:
    """Return True if the point lies on a street (grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True when ``x`` or ``y`` is aligned with a grid line.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def _clamp(value: int) -> int:
    """Clamp a coordinate into the map bounds."""
    return max(0, min(MAP_SIZE, value))


class PathPlanner:
    """Computes routes and per-tick movement steps on the street grid."""

    @staticmethod
    def plan(start: Point, end: Point) -> List[Point]:
        """Plan a street-following route between two points.

        The route moves horizontally first (along the street through the
        start point), then turns at a right angle towards the end point.

        Args:
            start: Starting coordinate.
            end: Destination coordinate.

        Returns:
            List of waypoints including both endpoints.
        """
        sx, sy = start
        ex, ey = end
        if sx == ex or sy == ey:
            return [(sx, sy), (ex, ey)]
        return [(sx, sy), (ex, sy), (ex, ey)]

    @classmethod
    def plan_route(cls, points: Sequence[Point]) -> List[Point]:
        """Plan a continuous route through several destinations in order.

        Args:
            points: Ordered list of coordinates to visit, e.g.
                ``[rider_position, restaurant, customer]``.

        Returns:
            Concatenated list of waypoints with duplicate joints removed.
        """
        if not points:
            return []
        route: List[Point] = [(int(points[0][0]), int(points[0][1]))]
        for nxt in points[1:]:
            target = (int(nxt[0]), int(nxt[1]))
            segment = cls.plan(route[-1], target)
            route.extend(segment[1:])
        return route

    @staticmethod
    def route_length(route: Sequence[Point]) -> int:
        """Return the total Manhattan length of a route.

        Args:
            route: Waypoints of the route.

        Returns:
            Sum of Manhattan distances between consecutive waypoints.
        """
        return sum(
            abs(b[0] - a[0]) + abs(b[1] - a[1])
            for a, b in zip(route, route[1:])
        )

    @staticmethod
    def next_position(x: int, y: int, tx: int, ty: int,
                      speed: int) -> Tuple[int, int, bool]:
        """Compute the new position after moving up to ``speed`` units.

        Movement rules:
            * If the rider is directly above or below the target (same x), it
              moves vertically and the special-case flag is set.
            * If the rider is on a horizontal street, it moves horizontally.
            * Otherwise it moves vertically along the current vertical street.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            tx: Target x coordinate.
            ty: Target y coordinate.
            speed: Maximum distance travelled this tick.

        Returns:
            Tuple ``(new_x, new_y, special_case)``.
        """
        special = False
        remaining = max(0, int(speed))
        while remaining > 0 and (x, y) != (tx, ty):
            if x == tx:
                special = True
                step = min(remaining, abs(ty - y))
                y += step if ty > y else -step
                remaining -= step
            elif y % CELL_SIZE == 0 or y == ty:
                step = min(remaining, abs(tx - x))
                x += step if tx > x else -step
                remaining -= step
            else:
                step = min(remaining, abs(ty - y))
                y += step if ty > y else -step
                remaining -= step
        return _clamp(x), _clamp(y), special
