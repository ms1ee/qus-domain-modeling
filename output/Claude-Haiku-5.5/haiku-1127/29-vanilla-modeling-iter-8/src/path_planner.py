"""Grid-based path planning for the 800x800 map.

The map is divided into an 8x8 grid of 100x100 cells. Grid lines (where x
or y is a multiple of 100) are streets. Routes are built from axis-aligned
segments, preferring corners that keep each segment on a street.
"""

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100


@dataclass
class Route:
    """A connected sequence of waypoints.

    Attributes:
        waypoints: Ordered list of points, starting at the origin.
        total_distance: Total travelled distance (Manhattan length of the
            axis-aligned segments).
    """

    waypoints: List[Point] = field(default_factory=list)
    total_distance: float = 0.0


class PathPlanner:
    """Computes axis-aligned, street-prioritising paths on the grid."""

    cell_size: int = CELL_SIZE
    map_size: int = MAP_SIZE

    @staticmethod
    def is_on_street(coord_x: int, coord_y: int) -> bool:
        """Return True if the point lies on a street (grid line)."""
        return coord_x % CELL_SIZE == 0 or coord_y % CELL_SIZE == 0

    @classmethod
    def plan_path(cls, start: Point, goal: Point) -> List[Point]:
        """Plan an axis-aligned path from ``start`` to ``goal``.

        The returned list excludes ``start`` and ends with ``goal``.
        Two L-shaped candidates are considered; the one whose segments
        lie on more streets is chosen. Points on the same row or column
        are connected by a single straight segment (special case).

        Args:
            start: Current position (x, y).
            goal: Destination position (x, y).

        Returns:
            Waypoints to visit in order. Empty if already at the goal.
        """
        if start == goal:
            return []
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return [goal]

        corner_h = (gx, sy)  # horizontal segment first
        corner_v = (sx, gy)  # vertical segment first
        score_h = int(sy % CELL_SIZE == 0) + int(gx % CELL_SIZE == 0)
        score_v = int(sx % CELL_SIZE == 0) + int(gy % CELL_SIZE == 0)
        corner = corner_h if score_h >= score_v else corner_v
        return [corner, goal]

    @classmethod
    def build_route(cls, origin: Point, stops: Sequence[Point]) -> Route:
        """Build a continuous route visiting ``stops`` in order.

        Args:
            origin: Starting position of the rider.
            stops: Successive destinations (e.g. restaurant, customer).

        Returns:
            A Route whose waypoints begin with ``origin``.
        """
        waypoints: List[Point] = [tuple(origin)]
        total = 0.0
        current = tuple(origin)
        for stop in stops:
            for point in cls.plan_path(current, tuple(stop)):
                total += abs(point[0] - current[0]) + abs(point[1] - current[1])
                waypoints.append(point)
                current = point
        return Route(waypoints=waypoints, total_distance=float(total))
