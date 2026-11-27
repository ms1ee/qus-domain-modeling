"""Grid-based path planning and step-wise movement.

Routes are Manhattan (axis-aligned) polylines. The planner prefers routes
that travel along streets (grid lines) and handles the special case where
the target lies directly above, below or beside the start point by moving
in a straight line. Riders do not block each other, so no path conflicts or
deadlocks can occur in the tick-based model.
"""

import logging
import math
from typing import List, Sequence, Tuple

from grid import CELL_SIZE, Grid

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of value."""
    return (value > 0) - (value < 0)


def _path_length(start: Point, waypoints: Sequence[Point]) -> int:
    """Return the Manhattan length of a polyline starting at ``start``."""
    total = 0
    current = start
    for point in waypoints:
        total += abs(point[0] - current[0]) + abs(point[1] - current[1])
        current = point
    return total


class Route:
    """A planned route from a start point through a list of waypoints.

    Attributes:
        start: Starting point (x, y).
        waypoints: Ordered list of corner/end points (x, y).
        speed: Speed used to estimate the duration, in units per tick.
        total_distance: Total Manhattan length of the route.
        estimated_ticks: Number of ticks needed at the given speed.
    """

    def __init__(self, start: Point, waypoints: Sequence[Point],
                 speed: int) -> None:
        """Create a route and compute its distance and duration.

        Args:
            start: Starting point.
            waypoints: Points to visit in order.
            speed: Movement speed in units per tick.
        """
        self.start = (int(start[0]), int(start[1]))
        self.waypoints: List[Point] = [(int(p[0]), int(p[1]))
                                       for p in waypoints]
        self.speed = int(speed)
        self.total_distance = float(_path_length(self.start, self.waypoints))
        if self.speed > 0:
            self.estimated_ticks = int(math.ceil(self.total_distance /
                                                 self.speed))
        else:
            self.estimated_ticks = 0


class PathPlanner:
    """Computes routes and moves riders along them on the grid."""

    def __init__(self, grid: Grid = None) -> None:
        """Create a planner.

        Args:
            grid: Grid used for street checks. A default 8x8 grid is created
                if none is given.
        """
        self.grid = grid if grid is not None else Grid()

    def plan(self, start: Point, goal: Point, speed: int) -> Route:
        """Plan a route from start to goal.

        Special cases:
            * Start equals goal: empty route.
            * Goal directly above/below or beside the start (same x or y):
              straight-line movement with a single waypoint.
            * Otherwise: an L-shaped route with two candidate corners. The
              corner whose legs run along streets for the greatest length is
              chosen; ties keep the horizontal-first corner.

        Args:
            start: Current position of the rider.
            goal: Target point (restaurant or customer cell centre).
            speed: Rider speed in units per tick.

        Returns:
            A Route object.
        """
        sx, sy = start
        gx, gy = goal
        if (sx, sy) == (gx, gy):
            return Route(start, [], speed)
        if sx == gx or sy == gy:
            # Directly above/below or beside the target: straight movement.
            return Route(start, [(gx, gy)], speed)
        corner_a = (gx, sy)  # horizontal first
        corner_b = (sx, gy)  # vertical first
        cost_a = (self.off_street_length(start, corner_a) +
                  self.off_street_length(corner_a, goal))
        cost_b = (self.off_street_length(start, corner_b) +
                  self.off_street_length(corner_b, goal))
        corner = corner_a if cost_a <= cost_b else corner_b
        logger.debug("Planned route %s -> %s via %s", start, goal, corner)
        return Route(start, [corner, (gx, gy)], speed)

    def off_street_length(self, a: Point, b: Point) -> int:
        """Return the length of an axis-aligned segment that is off-street.

        A horizontal segment is on a street when its y is a grid line; a
        vertical segment is on a street when its x is a grid line.
        """
        ax, ay = a
        bx, by = b
        if ay == by:
            return 0 if ay % CELL_SIZE == 0 else abs(bx - ax)
        if ax == bx:
            return 0 if ax % CELL_SIZE == 0 else abs(by - ay)
        return abs(bx - ax) + abs(by - ay)

    @staticmethod
    def step(x: int, y: int, waypoints: Sequence[Point],
             speed: int) -> Tuple[int, int, List[Point], int]:
        """Move up to ``speed`` units along a list of waypoints.

        Movement inside each segment is horizontal first, then vertical.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            waypoints: Remaining waypoints (not modified).
            speed: Maximum distance to move this tick.

        Returns:
            Tuple ``(new_x, new_y, remaining_waypoints, distance_moved)``.
        """
        remaining = [(int(p[0]), int(p[1])) for p in waypoints]
        budget = int(speed)
        moved = 0
        while budget > 0 and remaining:
            tx, ty = remaining[0]
            if (x, y) == (tx, ty):
                remaining.pop(0)
                continue
            dx = tx - x
            dy = ty - y
            mx = min(budget, abs(dx))
            x += mx * _sign(dx)
            budget -= mx
            moved += mx
            my = min(budget, abs(dy))
            y += my * _sign(dy)
            budget -= my
            moved += my
            if (x, y) == (tx, ty):
                remaining.pop(0)
        return x, y, remaining, moved
