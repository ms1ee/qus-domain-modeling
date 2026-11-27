"""Grid-based path planning for riders.

Routes always travel along streets: a rider on a horizontal street moves
horizontally first, otherwise it moves vertically first. Right-angle turns
happen at street intersections, and straight-line movement is used when the
rider is directly above or below its target.
"""

import math
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

from grid import Grid

Point = Tuple[int, int]


@dataclass
class Route:
    """A planned path made of connected waypoints.

    Attributes:
        waypoints: Ordered corner points from start to final destination.
        total_distance: Manhattan length of the route in units.
        estimated_time: Estimated number of ticks needed to traverse it.
    """

    waypoints: List[Point] = field(default_factory=list)
    total_distance: int = 0
    estimated_time: int = 0


def _move_toward(current: int, target: int, step: int) -> int:
    """Move a single coordinate toward a target by at most ``step``.

    Args:
        current: Current coordinate value.
        target: Target coordinate value.
        step: Maximum movement magnitude.

    Returns:
        int: New coordinate value, never overshooting the target.
    """
    if current < target:
        return min(current + step, target)
    if current > target:
        return max(current - step, target)
    return current


def _unique_consecutive(points: Sequence[Point]) -> List[Point]:
    """Remove consecutive duplicate points from a list.

    Args:
        points: Sequence of points.

    Returns:
        List[Point]: Points with consecutive duplicates removed.
    """
    result: List[Point] = []
    for point in points:
        if not result or result[-1] != point:
            result.append(point)
    return result


class PathPlanner:
    """Computes street-following routes and per-tick movement steps."""

    def __init__(self, grid: Grid = None):
        """Create a planner.

        Args:
            grid: Grid description to use. A default 800x800 grid is created
                when omitted.
        """
        self.grid = grid or Grid()
        self.algorithm = "street-first-manhattan"

    def next_step(
        self, x: int, y: int, target_x: int, target_y: int, speed: int
    ) -> Tuple[int, int, bool]:
        """Advance one tick toward a target along the street network.

        Args:
            x: Current X coordinate.
            y: Current Y coordinate.
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
            speed: Maximum units to move this tick.

        Returns:
            Tuple[int, int, bool]: New (x, y) and whether the target was reached.
        """
        if x == target_x and y == target_y:
            return x, y, True
        step = max(1, int(speed))
        if self.grid.is_horizontal_street(y) and x != target_x:
            x = _move_toward(x, target_x, step)
        elif y != target_y:
            y = _move_toward(y, target_y, step)
        else:
            x = _move_toward(x, target_x, step)
        return x, y, (x == target_x and y == target_y)

    def plan(self, start: Point, goal: Point, speed: int = 1) -> Route:
        """Plan a single-leg street route from start to goal.

        Args:
            start: Starting point.
            goal: Destination point (a grid location).
            speed: Rider speed used for the time estimate.

        Returns:
            Route: Waypoints, Manhattan distance and estimated ticks.
        """
        sx, sy = start
        gx, gy = goal
        if self.grid.is_horizontal_street(sy) and sx != gx:
            corner = (gx, sy)
        else:
            corner = (sx, gy)
        waypoints = _unique_consecutive([start, corner, goal])
        distance = abs(gx - sx) + abs(gy - sy)
        return Route(
            waypoints=waypoints,
            total_distance=distance,
            estimated_time=math.ceil(distance / max(1, speed)),
        )

    def plan_multi(self, start: Point, stops: Sequence[Point], speed: int = 1) -> Route:
        """Plan a continuous route visiting several stops in order.

        Args:
            start: Starting point.
            stops: Ordered destinations (e.g. restaurant then customer).
            speed: Rider speed used for the time estimate.

        Returns:
            Route: Combined route across all legs.
        """
        waypoints: List[Point] = [start]
        total = 0
        current = start
        for stop in stops:
            leg = self.plan(current, stop, speed)
            waypoints.extend(leg.waypoints[1:])
            total += leg.total_distance
            current = stop
        waypoints = _unique_consecutive(waypoints)
        return Route(
            waypoints=waypoints,
            total_distance=total,
            estimated_time=math.ceil(total / max(1, speed)),
        )
