"""Grid-based path planning for riders on the 800x800 street map.

Coordinate conventions
----------------------
* The map spans 0..800 on both axes and is divided into 8x8 cells of
  100 units each.
* Streets lie on the grid lines: a point is on a street when its x or y
  coordinate is a multiple of 100.
* Restaurants and customers are placed on cell corners (multiples of 100),
  i.e. on street intersections, so every route can follow the streets.

Movement rule
-------------
A rider on a horizontal street moves horizontally toward the target until the
x coordinates align, then turns onto the vertical street and moves vertically.
A rider on a vertical street does the mirror image. Because every move keeps
the rider on a street, the planner never leaves the road network. Riders do
not block each other, so no deadlock can occur; they may share a street.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = MAP_SIZE // CELL_SIZE
UNLIMITED_BUDGET = 10 ** 9


def clamp_to_cell_corner(value: int) -> int:
    """Convert a raw coordinate to the top-left corner of its grid cell.

    Values are first clamped into the map (0..799 cell index range), so an
    input of 150 maps to 100, and 850 maps to 700.

    Args:
        value: Raw coordinate.

    Returns:
        Multiple of 100 in the range 0..700.
    """
    index = min(max(int(value), 0) // CELL_SIZE, GRID_CELLS - 1)
    return index * CELL_SIZE


def snap_point(pos: Sequence[int]) -> Point:
    """Snap an ``(x, y)`` pair to grid cell corners.

    Args:
        pos: Sequence of exactly two integers.

    Returns:
        Tuple ``(x, y)`` of snapped coordinates.

    Raises:
        ValueError: If ``pos`` does not contain exactly two values.
    """
    if len(pos) != 2:
        raise ValueError(f"a point needs exactly 2 coordinates, got {len(pos)}")
    return (clamp_to_cell_corner(pos[0]), clamp_to_cell_corner(pos[1]))


def is_street_point(x: int, y: int) -> bool:
    """Return True when ``(x, y)`` lies on a street (grid line)."""
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def manhattan(a: Sequence[int], b: Sequence[int]) -> int:
    """Return the Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def route_length(points: Sequence[Point]) -> int:
    """Return the total travelled length along a polyline of points."""
    return sum(manhattan(a, b) for a, b in zip(points, points[1:]))


def estimate_ticks(distance: int, speed: int) -> int:
    """Return the number of ticks needed to cover ``distance`` at ``speed``.

    Args:
        distance: Distance in map units.
        speed: Speed in units per tick (must be positive).

    Returns:
        Ceiling of ``distance / speed``.
    """
    if speed <= 0:
        raise ValueError("speed must be positive")
    return int(math.ceil(distance / speed))


class PathPlanner:
    """Pathfinding logic for street-constrained rider movement."""

    @staticmethod
    def next_position(x: int, y: int, tx: int, ty: int, budget: int) -> Tuple[int, int, int]:
        """Advance one straight segment toward the target along the streets.

        Special cases handled:
            * Target directly above or below: the rider moves vertically only.
            * Target directly left or right: the rider moves horizontally only.
            * Rider already at the target: no movement.

        Args:
            x, y: Current rider position.
            tx, ty: Target position (grid corner).
            budget: Maximum distance that may be covered this call.

        Returns:
            Tuple ``(new_x, new_y, used)`` where ``used`` is the distance moved.
        """
        if (x, y) == (tx, ty) or budget <= 0:
            return x, y, 0

        if y % CELL_SIZE == 0:
            # On a horizontal street: slide along it until x aligns with target.
            horizontal = x != tx
        else:
            # On a vertical street: slide along it until y aligns with target.
            horizontal = y == ty

        if horizontal:
            dist = abs(tx - x)
            step = min(budget, dist)
            direction = 1 if tx > x else -1
            return x + direction * step, y, step

        dist = abs(ty - y)
        step = min(budget, dist)
        direction = 1 if ty > y else -1
        return x, y + direction * step, step

    @staticmethod
    def plan_route(start: Point, targets: Sequence[Point]) -> List[Point]:
        """Build the full street route visiting ``targets`` in order.

        This is the multi-destination path used for the continuous route from
        the rider's position to the restaurant and then to the customer.

        Args:
            start: Starting position.
            targets: Ordered list of destination points.

        Returns:
            List of corner points, starting with ``start``.
        """
        points: List[Point] = [(int(start[0]), int(start[1]))]
        x, y = points[0]
        for tx, ty in targets:
            while (x, y) != (tx, ty):
                nx, ny, used = PathPlanner.next_position(x, y, tx, ty, UNLIMITED_BUDGET)
                if used == 0:
                    break
                x, y = nx, ny
                points.append((x, y))
        return points

    @staticmethod
    def route_length(points: Sequence[Point]) -> int:
        """Return the total length of a route polyline."""
        return route_length(points)
