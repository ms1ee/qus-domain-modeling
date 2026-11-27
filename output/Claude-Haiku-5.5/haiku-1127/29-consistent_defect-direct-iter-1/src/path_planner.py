"""Grid-based path planning on the 800x800 street map.

The map is an 8x8 grid of 100x100 cells. Lines whose x or y coordinate is a
multiple of 100 are streets, and points where both coordinates are multiples
of 100 are intersections. Restaurants and customers are snapped to
intersections, so every route is a sequence of right-angle turns along
streets. Riders never block each other (they may share a street), which
means no path-conflict deadlock can arise from waiting.
"""

import math
from typing import List, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
MAX_PATH_STEPS = 10000

Point = Tuple[int, int]


def snap_coordinate(value: int) -> int:
    """Clamp a coordinate to the map and move it to its cell's top-left corner.

    Args:
        value: Raw coordinate value.

    Returns:
        Coordinate in the range 0-800 that is a multiple of 100.
    """
    clamped = min(max(int(value), 0), MAP_SIZE)
    return (clamped // CELL_SIZE) * CELL_SIZE


class PathPlanner:
    """Computes street-following waypoints between map points."""

    @staticmethod
    def snap_point(x: int, y: int) -> Point:
        """Snap a raw point to the top-left corner of its grid cell.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Tuple ``(x, y)`` of snapped coordinates.
        """
        return (snap_coordinate(x), snap_coordinate(y))

    @staticmethod
    def is_street(x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line).

        Args:
            x: x coordinate.
            y: y coordinate.
        """
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_intersection(x: int, y: int) -> bool:
        """Return True if the point is a street intersection.

        Args:
            x: x coordinate.
            y: y coordinate.
        """
        return x % CELL_SIZE == 0 and y % CELL_SIZE == 0

    @staticmethod
    def manhattan(a: Point, b: Point) -> int:
        """Return the Manhattan distance between two points.

        Args:
            a: First point.
            b: Second point.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def euclidean(a: Point, b: Point) -> float:
        """Return the Euclidean distance between two points.

        Args:
            a: First point.
            b: Second point.
        """
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @classmethod
    def next_waypoint(cls, position: Point, target: Point) -> Tuple[Point, bool]:
        """Compute the next axis-aligned waypoint on the way to a target.

        Movement prefers streets: a rider on a horizontal street moves along
        it until it is directly above or below the target, then turns onto
        the vertical street. A rider on a vertical street moves along it
        until it reaches the target's row, then turns onto the horizontal
        street.

        Args:
            position: Current ``(x, y)`` position.
            target: Destination ``(x, y)`` point.

        Returns:
            A tuple ``(waypoint, special_case)``. ``special_case`` is True when
            the rider is directly above or below the target and moves straight
            toward it.
        """
        x, y = position
        tx, ty = target
        if (x, y) == (tx, ty):
            return (tx, ty), False
        if y % CELL_SIZE == 0:
            if x != tx:
                return (tx, y), False
            # Directly above/below the target: special straight-line movement.
            return (x, ty), True
        if y != ty:
            return (x, ty), x == tx
        return (tx, y), False

    @classmethod
    def trace(cls, start: Point, target: Point) -> List[Point]:
        """Return the list of corner points from ``start`` to ``target``.

        Args:
            start: Starting point.
            target: Destination point.

        Returns:
            List of points starting with ``start`` and ending with ``target``.
        """
        pos = (int(start[0]), int(start[1]))
        goal = (int(target[0]), int(target[1]))
        path = [pos]
        for _ in range(MAX_PATH_STEPS):
            if pos == goal:
                break
            waypoint, _ = cls.next_waypoint(pos, goal)
            if waypoint == pos:
                break
            path.append(waypoint)
            pos = waypoint
        return path

    @classmethod
    def route(cls, start: Point, targets: List[Point]) -> List[Point]:
        """Build a continuous route through an ordered list of targets.

        Args:
            start: Starting point.
            targets: Ordered destinations to visit.

        Returns:
            Combined list of route points (no duplicate joints).
        """
        points: List[Point] = [(int(start[0]), int(start[1]))]
        for target in targets:
            leg = cls.trace(points[-1], target)
            points.extend(leg[1:])
        return points

    @staticmethod
    def path_length(points: List[Point]) -> int:
        """Return the total street length of a list of route points.

        Args:
            points: Ordered route points.
        """
        return sum(
            PathPlanner.manhattan(a, b) for a, b in zip(points, points[1:])
        )
