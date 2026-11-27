"""Grid-based path planning for riders.

Paths are built from axis-aligned segments (right-angle turns only). When
two L-shaped routes are possible, the planner prefers the one whose segments
lie on streets (grid lines). A target lying directly above or below (or left
or right of) the rider is reached by a straight-line movement.
"""

import logging
from typing import List

from grid import Point, is_street_x, is_street_y, manhattan

logger = logging.getLogger(__name__)


class PathPlanner:
    """Compute waypoint routes on the 800x800 grid."""

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Plan a route from ``start`` to ``goal``.

        The returned list excludes ``start`` and always ends with ``goal``
        (unless the two points are identical, in which case it is empty).

        Args:
            start: Current position.
            goal: Destination position.

        Returns:
            Ordered list of waypoints to visit.
        """
        if start == goal:
            return []
        start_x, start_y = start
        goal_x, goal_y = goal
        # Special case: target directly above/below or left/right.
        if start_x == goal_x or start_y == goal_y:
            return [goal]
        corners = [(goal_x, start_y), (start_x, goal_y)]
        best = max(
            corners,
            key=lambda corner: self._street_score(start, corner, goal),
        )
        logger.debug("Planned route %s -> %s via %s", start, goal, best)
        return [best, goal]

    @classmethod
    def _segment_on_street(cls, a: Point, b: Point) -> bool:
        """Return True if the axis-aligned segment ``a``-``b`` is a street."""
        if a[1] == b[1]:
            return is_street_y(a[1])
        if a[0] == b[0]:
            return is_street_x(a[0])
        return False

    def _street_score(self, start: Point, corner: Point, goal: Point) -> int:
        """Score a candidate corner by the number of street segments."""
        return int(self._segment_on_street(start, corner)) + int(
            self._segment_on_street(corner, goal)
        )

    @staticmethod
    def path_length(points: List[Point]) -> int:
        """Return the total Manhattan length of a polyline.

        Args:
            points: Ordered points, including the starting point.

        Returns:
            Total travelled distance in units.
        """
        total = 0
        for first, second in zip(points, points[1:]):
            total += manhattan(first, second)
        return total

    @staticmethod
    def is_on_street(point: Point) -> bool:
        """Return True if the point lies on a street (grid line)."""
        return is_street_x(point[0]) or is_street_y(point[1])
