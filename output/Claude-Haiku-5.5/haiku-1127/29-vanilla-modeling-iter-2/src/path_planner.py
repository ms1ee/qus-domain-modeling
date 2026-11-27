"""Grid-based path planning for the 800x800 delivery map.

The map is an 8x8 grid of 100x100 cells. Points whose x or y coordinate is a
multiple of 100 lie on streets. Routes are orthogonal (horizontal and vertical
segments only) and prefer corners that lie on a street. Straight movement is
used whenever the start and goal share an x or y coordinate.

Riders move independently and never block each other, so the planner cannot
create circular waits; this is the mechanism that avoids deadlocks.
"""

import math
from typing import List, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8
STREET_SPACING = 100


def clamp_coordinate(value: int) -> int:
    """Clamp a coordinate into the valid map range 0-800.

    Args:
        value: Raw coordinate.

    Returns:
        The integer coordinate limited to ``[0, MAP_SIZE]``.
    """
    return max(0, min(MAP_SIZE, int(value)))


def cell_index(value: int) -> int:
    """Return the grid index (0-7) of the cell containing a coordinate.

    The coordinate 800 (the map edge) belongs to the last cell.

    Args:
        value: Coordinate in map units.

    Returns:
        Grid index along one axis.
    """
    value = clamp_coordinate(value)
    return min(value // CELL_SIZE, GRID_DIM - 1)


def cell_center(value: int) -> int:
    """Convert a coordinate to the centre of its grid cell.

    Implements ``center = (grid // 100) * 100 + 50``, with the map edge
    clamped into the last cell.

    Args:
        value: Coordinate in map units.

    Returns:
        Centre coordinate of the containing cell.
    """
    return cell_index(value) * CELL_SIZE + CELL_SIZE // 2


def is_street_point(point: Point) -> bool:
    """Return True if the point lies on a street grid line.

    Args:
        point: ``(x, y)`` coordinate.

    Returns:
        True when x or y is a multiple of 100.
    """
    x, y = point
    return x % STREET_SPACING == 0 or y % STREET_SPACING == 0


def euclidean(a: Point, b: Point) -> float:
    """Return the Euclidean distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        ``sqrt((ax - bx)^2 + (ay - by)^2)``.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan (street) distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


class PathPlanner:
    """Plans orthogonal, street-preferring routes and advances riders along them.

    Attributes:
        algorithm_name: Human-readable name of the algorithm.
        map_size: Size of the square map in units.
    """

    algorithm_name = "street-first orthogonal routing"

    def __init__(self, map_size: int = MAP_SIZE) -> None:
        """Create a planner for a square map.

        Args:
            map_size: Width and height of the map in units.
        """
        self.map_size = map_size

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Plan a route from ``start`` to ``goal``.

        Straight routes are used when start and goal share a coordinate
        (directly above/below or beside each other). Otherwise a single
        right-angle corner is chosen, preferring the corner on a street.

        Args:
            start: Current position.
            goal: Destination.

        Returns:
            Waypoints to visit in order, excluding ``start`` and including
            ``goal``.
        """
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return [(gx, gy)]
        corner_horizontal_first = (gx, sy)
        corner_vertical_first = (sx, gy)
        if (is_street_point(corner_vertical_first)
                and not is_street_point(corner_horizontal_first)):
            corner = corner_vertical_first
        else:
            corner = corner_horizontal_first
        return [corner, (gx, gy)]

    def plan_route(self, start: Point, pickup: Point, dropoff: Point) -> List[Point]:
        """Plan a continuous route: start -> restaurant -> customer.

        Args:
            start: Rider position.
            pickup: Restaurant location.
            dropoff: Customer location.

        Returns:
            Concatenated waypoints for the whole trip.
        """
        return self.plan(start, pickup) + self.plan(pickup, dropoff)

    def path_length(self, start: Point, waypoints: Sequence[Point]) -> int:
        """Return the total travelled length along waypoints.

        Args:
            start: Starting position.
            waypoints: Waypoints returned by :meth:`plan`.

        Returns:
            Sum of segment lengths in map units.
        """
        total = 0
        current = start
        for point in waypoints:
            total += manhattan(current, point)
            current = point
        return total

    def advance(self, x: int, y: int, waypoints: Sequence[Point],
                speed: int) -> Tuple[int, int, int]:
        """Move up to ``speed`` units along the waypoints.

        Each segment is axis-aligned. When the current y equals the target y
        the rider moves horizontally, otherwise vertically.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            waypoints: Route to follow.
            speed: Movement budget for this tick.

        Returns:
            Tuple ``(new_x, new_y, distance_used)``.
        """
        pos_x, pos_y = x, y
        budget = max(0, int(speed))
        used = 0
        for target_x, target_y in waypoints:
            while budget > 0 and (pos_x, pos_y) != (target_x, target_y):
                if pos_y == target_y:
                    step = min(budget, abs(target_x - pos_x))
                    pos_x += _sign(target_x - pos_x) * step
                else:
                    step = min(budget, abs(target_y - pos_y))
                    pos_y += _sign(target_y - pos_y) * step
                budget -= step
                used += step
            if budget <= 0:
                break
        return pos_x, pos_y, used
