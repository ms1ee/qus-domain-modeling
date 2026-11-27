"""Grid-based path planning for riders.

Routes are sequences of axis-aligned waypoints. For every pair of points the
planner evaluates the two right-angle (L-shaped) candidates and prefers the
one whose segments run along streets (grid lines). Straight-line movement is
used when start and goal share an x or y coordinate, which covers the
"directly above or below" special case.
"""

import logging
from dataclasses import dataclass, field

from grid_map import CELL_SIZE, GridMap, Point

logger = logging.getLogger(__name__)


@dataclass
class Route:
    """A planned path.

    Attributes:
        waypoints: Ordered list of Points, starting with the origin.
        total_length: Total Manhattan length of the path in map units.
    """

    waypoints: list = field(default_factory=list)
    total_length: float = 0.0


def _segment_length(a, b):
    """Return the Manhattan length of an axis-aligned segment."""
    return abs(a.x - b.x) + abs(a.y - b.y)


def _segment_on_street(a, b):
    """Return True if the axis-aligned segment a-b lies on a street."""
    if a.x == b.x:
        return a.x % CELL_SIZE == 0
    if a.y == b.y:
        return a.y % CELL_SIZE == 0
    return False


def _pairs(points):
    """Yield consecutive point pairs of a list."""
    return zip(points, points[1:])


class PathPlanner:
    """Plans routes on the grid, favouring street segments."""

    def __init__(self, grid_map=None):
        """Create a planner.

        Args:
            grid_map: Optional GridMap used for bounds checks.
        """
        self.grid_map = grid_map or GridMap()

    def plan(self, start, goal):
        """Plan a route from ``start`` to ``goal``.

        Args:
            start: Origin Point.
            goal: Destination Point.

        Returns:
            A Route. If the points coincide the route has one waypoint and
            zero length.

        Raises:
            ValueError: If either point lies outside the map.
        """
        for point in (start, goal):
            if not self.grid_map.is_valid(point.x, point.y):
                raise ValueError(
                    f"point ({point.x}, {point.y}) is outside the map")

        if start == goal:
            return Route(waypoints=[start], total_length=0.0)

        if start.x == goal.x or start.y == goal.y:
            candidates = [[start, goal]]
        else:
            candidates = [
                [start, Point(goal.x, start.y), goal],
                [start, Point(start.x, goal.y), goal],
            ]

        best = max(candidates, key=self._route_score)
        total = sum(_segment_length(a, b) for a, b in _pairs(best))
        logger.debug("Planned route %s -> %s with length %s",
                     start, goal, total)
        return Route(waypoints=list(best), total_length=float(total))

    def plan_multi(self, start, destinations):
        """Plan a continuous route through several destinations in order.

        Args:
            start: Origin Point.
            destinations: Ordered list of Points to visit.

        Returns:
            A Route covering all legs.
        """
        waypoints = [start]
        total = 0.0
        current = start
        for destination in destinations:
            leg = self.plan(current, destination)
            waypoints.extend(leg.waypoints[1:])
            total += leg.total_length
            current = destination
        return Route(waypoints=waypoints, total_length=total)

    @staticmethod
    def _route_score(points):
        """Score a candidate route: more street length is better.

        Ties are resolved in favour of the shorter total length, which is
        identical for all L-shaped candidates, so the first candidate wins.
        """
        street = sum(_segment_length(a, b) for a, b in _pairs(points)
                     if _segment_on_street(a, b))
        total = sum(_segment_length(a, b) for a, b in _pairs(points))
        return (street, -total)
