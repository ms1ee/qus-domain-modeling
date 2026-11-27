"""Grid-based path planning for riders.

Routes prefer streets: a rider first snaps onto the nearest vertical street,
travels along vertical streets to the nearest horizontal street next to the
goal, follows that street horizontally, and makes a short final approach to
the target. Riders never block each other, so no deadlock can arise.
"""

from typing import List, Optional, Tuple

from grid import CELL_SIZE, Grid, nearest_street_line

Point = Tuple[int, int]


class PathPlanner:
    """Plans and executes right-angle routes on the grid.

    Attributes:
        grid: The grid the planner operates on.
    """

    def __init__(self, grid: Optional[Grid] = None) -> None:
        """Create a planner.

        Args:
            grid: Optional grid instance; a default 8x8 grid is created otherwise.
        """
        self.grid = grid if grid is not None else Grid()

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Compute the waypoint list from ``start`` to ``goal``.

        Every consecutive pair of points shares either the x or the y
        coordinate, so each leg is a straight street segment or a final
        approach segment.

        Args:
            start: Current position.
            goal: Target position.

        Returns:
            Ordered waypoints, excluding ``start`` and ending at ``goal``.
            An empty list means the rider is already at the goal.
        """
        sx, sy = start
        gx, gy = goal
        waypoints: List[Point] = []
        cx, cy = sx, sy

        # Special case: an off-street rider first snaps onto a vertical street.
        if cx % CELL_SIZE != 0:
            cx = nearest_street_line(cx)
            waypoints.append((cx, cy))

        if cx == gx:
            # Directly above or below the target: straight movement.
            waypoints.append((gx, gy))
        else:
            street_y = nearest_street_line(gy)
            waypoints.append((cx, street_y))
            waypoints.append((gx, street_y))
            waypoints.append((gx, gy))

        return _remove_repeats(start, waypoints)

    def step(
        self, x: int, y: int, route: List[Point], speed: int
    ) -> Tuple[int, int, List[Point]]:
        """Advance along ``route`` by at most ``speed`` units.

        Args:
            x: Current X coordinate.
            y: Current Y coordinate.
            route: Remaining waypoints.
            speed: Maximum Manhattan distance to travel this tick.

        Returns:
            Tuple ``(new_x, new_y, remaining_route)``.
        """
        remaining = int(speed)
        pending = list(route)
        if remaining <= 0:
            return x, y, pending
        while remaining > 0 and pending:
            tx, ty = pending[0]
            dx = tx - x
            dy = ty - y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                x, y = tx, ty
                remaining -= dist
                pending.pop(0)
            else:
                if dx != 0:
                    x += remaining if dx > 0 else -remaining
                else:
                    y += remaining if dy > 0 else -remaining
                remaining = 0
        return x, y, pending


def _remove_repeats(start: Point, points: List[Point]) -> List[Point]:
    """Drop consecutive duplicate waypoints, including repeats of ``start``.

    Args:
        start: Starting point.
        points: Candidate waypoints.

    Returns:
        Filtered waypoint list.
    """
    result: List[Point] = []
    prev = start
    for point in points:
        if point != prev:
            result.append(point)
            prev = point
    return result
