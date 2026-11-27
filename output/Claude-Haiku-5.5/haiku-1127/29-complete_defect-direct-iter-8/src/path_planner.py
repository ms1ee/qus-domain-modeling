"""Grid-based path planning for the food delivery simulator.

The map is an 8x8 grid of 100x100 unit cells (800x800 units). Locations are
represented by cell-center points, computed as
``center = (value // 100) * 100 + 50``. Movement is always axis-aligned
(along streets) and uses right-angle turns.
"""

import logging
from typing import Iterable, List, Optional, Sequence, Set, Tuple

GRID_SIZE = 8
CELL_SIZE = 100
MAP_SIZE = GRID_SIZE * CELL_SIZE

Point = Tuple[int, int]

logger = logging.getLogger("dispatch.path")


def clamp_coordinate(value: int) -> int:
    """Clamp a coordinate into the valid map range ``[0, MAP_SIZE]``.

    Args:
        value: Raw integer coordinate.

    Returns:
        The clamped coordinate.
    """
    return max(0, min(MAP_SIZE, int(value)))


def grid_index(value: int) -> int:
    """Return the grid index (0-7) of a coordinate.

    Coordinates equal to ``MAP_SIZE`` (800) belong to the last cell.

    Args:
        value: Raw integer coordinate.

    Returns:
        Grid index in ``range(GRID_SIZE)``.
    """
    return min(clamp_coordinate(value) // CELL_SIZE, GRID_SIZE - 1)


def to_cell_center(value: int) -> int:
    """Convert one coordinate to the center of its grid cell.

    Args:
        value: Raw integer coordinate in range 0-800.

    Returns:
        ``(value // 100) * 100 + 50`` with boundary clamping.
    """
    return grid_index(value) * CELL_SIZE + CELL_SIZE // 2


def to_cell_point(x: int, y: int) -> Point:
    """Convert a raw (x, y) pair to the center point of its grid cell.

    Args:
        x: Raw x coordinate.
        y: Raw y coordinate.

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    return to_cell_center(x), to_cell_center(y)


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan (street-grid) distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathPlanner:
    """Pathfinding logic for riders on the street grid.

    All methods are stateless; the class groups the grid-based algorithm
    and its special-case handling.
    """

    @staticmethod
    def is_special_case(start: Point, goal: Point) -> bool:
        """Return True when the goal is directly above or below the start.

        Such targets are reached by a single straight vertical movement.

        Args:
            start: Current position.
            goal: Target position.

        Returns:
            True if both points share an x coordinate and differ in y.
        """
        return start[0] == goal[0] and start[1] != goal[1]

    @staticmethod
    def plan(start: Point, goal: Point,
             occupied: Optional[Iterable[Point]] = None) -> List[Point]:
        """Plan waypoints from ``start`` to ``goal`` along streets.

        Straight targets (same row or column) are reached directly. Otherwise
        a single right-angle corner is used. When both possible corners are
        available the planner prefers the corner that is not occupied by
        another rider, which reduces path conflicts.

        Args:
            start: Current position (cell-center point).
            goal: Target position (cell-center point).
            occupied: Positions currently held by other riders.

        Returns:
            List of waypoints excluding ``start`` and ending at ``goal``.
            Empty list when already at the goal.
        """
        if start == goal:
            return []
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return [goal]

        blocked: Set[Point] = set(occupied or ())
        horizontal_first = (gx, sy)
        vertical_first = (sx, gy)
        if horizontal_first in blocked and vertical_first not in blocked:
            corner = vertical_first
        else:
            corner = horizontal_first
        return [corner, goal]

    @staticmethod
    def full_route(start: Point, stops: Sequence[Point],
                   occupied: Optional[Iterable[Point]] = None) -> List[Point]:
        """Build a continuous route visiting ``stops`` in order.

        Args:
            start: Starting position.
            stops: Ordered destinations (e.g. restaurant then customer).
            occupied: Positions held by other riders.

        Returns:
            List of points beginning with ``start``.
        """
        occupied_set = set(occupied or ())
        points: List[Point] = [start]
        current = start
        for stop in stops:
            points.extend(PathPlanner.plan(current, stop, occupied_set))
            current = stop
        return points

    @staticmethod
    def route_length(points: Sequence[Point]) -> int:
        """Return the total street length of a route.

        Args:
            points: Consecutive route points.

        Returns:
            Sum of Manhattan distances between consecutive points.
        """
        return sum(manhattan(a, b) for a, b in zip(points, points[1:]))

    @staticmethod
    def step_towards(pos: Point, path: Sequence[Point],
                     speed: int) -> Tuple[Point, List[Point], int]:
        """Advance a position along a waypoint path by up to ``speed`` units.

        This is a pure function: the caller stores the returned position and
        remaining path.

        Args:
            pos: Current position.
            path: Remaining waypoints.
            speed: Maximum movement distance this tick.

        Returns:
            Tuple ``(new_position, remaining_path, distance_moved)``.
        """
        x, y = pos
        remaining: List[Point] = list(path)
        budget = max(0, int(speed))
        moved = 0
        while budget > 0 and remaining:
            tx, ty = remaining[0]
            dx = tx - x
            dy = ty - y
            if dx == 0 and dy == 0:
                remaining.pop(0)
                continue
            if dx != 0:
                step = min(budget, abs(dx))
                x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                y += step if dy > 0 else -step
            budget -= step
            moved += step
            if (x, y) == (tx, ty):
                remaining.pop(0)
        return (x, y), remaining, moved
