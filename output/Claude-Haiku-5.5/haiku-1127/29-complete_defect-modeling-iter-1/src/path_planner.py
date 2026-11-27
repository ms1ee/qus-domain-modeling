"""Grid-based path planning for the 800x800 map (8x8 cells of 100 units).

Cell centers sit at ``50 + 100 * k``. The street network runs through these
center lines, so every grid node lies on a street and every movement is an
axis-aligned (horizontal or vertical) step with right-angle turns.
"""

from typing import Iterable, List, Optional, Sequence, Set, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8
CELL_HALF = CELL_SIZE // 2


def cell_center(value: int) -> int:
    """Convert a 0-800 coordinate into the center of its grid cell.

    Implements ``center = (value // 100) * 100 + 50``. Values at or beyond
    the map edge (e.g. 800) are clamped into the last cell.

    Args:
        value: Integer coordinate in the range 0-800.

    Returns:
        The cell-center coordinate along that axis.
    """
    index = int(value) // CELL_SIZE
    index = min(max(index, 0), GRID_DIM - 1)
    return index * CELL_SIZE + CELL_HALF


def snap_to_grid(x: int, y: int) -> Point:
    """Snap an (x, y) map coordinate to its grid cell center.

    Args:
        x: Horizontal coordinate (0-800).
        y: Vertical coordinate (0-800).

    Returns:
        Tuple ``(center_x, center_y)``.
    """
    return cell_center(x), cell_center(y)


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan (street-network) distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_street_point(x: int, y: int) -> bool:
    """Return True when the point lies on a street (grid line).

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        True if x or y aligns with a street center line.
    """
    return (x - CELL_HALF) % CELL_SIZE == 0 or (y - CELL_HALF) % CELL_SIZE == 0


def path_length(start: Point, waypoints: Sequence[Point]) -> int:
    """Compute the total Manhattan length of a waypoint sequence.

    Args:
        start: Starting point.
        waypoints: Ordered waypoints following ``start``.

    Returns:
        Total length in units.
    """
    total = 0
    current = start
    for point in waypoints:
        total += manhattan(current, point)
        current = point
    return total


class PathPlanner:
    """Plans street-following routes between grid points.

    Rules:
        * Same row or column (directly above/below/left/right of the target):
          a straight-line special case is used.
        * Otherwise a single right-angle turn is used. The planner prefers the
          horizontal-first corner, but when ``avoid_conflicts`` is enabled and
          that corner is occupied by another rider, it switches to the
          vertical-first corner to avoid path conflicts and deadlocks.
    """

    def __init__(self, avoid_conflicts: bool = True) -> None:
        """Create a planner.

        Args:
            avoid_conflicts: Whether to reroute around occupied corners.
        """
        self.avoid_conflicts = avoid_conflicts

    @staticmethod
    def is_special_case(start: Point, goal: Point) -> bool:
        """Return True when the goal is directly above/below/left/right.

        Args:
            start: Current position.
            goal: Target position.

        Returns:
            True for a straight-line (special) movement.
        """
        return start != goal and (start[0] == goal[0] or start[1] == goal[1])

    def plan(
        self,
        start: Point,
        goal: Point,
        occupied: Optional[Iterable[Point]] = None,
    ) -> List[Point]:
        """Plan a route from ``start`` to ``goal``.

        Args:
            start: Current position.
            goal: Destination grid point.
            occupied: Positions currently held by other riders.

        Returns:
            List of waypoints to visit in order, excluding ``start`` and
            ending at ``goal``. Empty when already at the goal.
        """
        if start == goal:
            return []
        sx, sy = start
        gx, gy = goal
        if sx == gx or sy == gy:
            return [goal]

        occupied_set: Set[Point] = set(occupied) if occupied else set()
        horizontal_corner = (gx, sy)
        vertical_corner = (sx, gy)
        corner = horizontal_corner
        if (
            self.avoid_conflicts
            and horizontal_corner in occupied_set
            and vertical_corner not in occupied_set
        ):
            corner = vertical_corner
        return [corner, goal]

    def plan_route(
        self,
        start: Point,
        stops: Sequence[Point],
        occupied: Optional[Iterable[Point]] = None,
    ) -> List[Point]:
        """Plan a continuous multi-destination route through ``stops``.

        Args:
            start: Starting position.
            stops: Ordered destinations (e.g. restaurant then customer).
            occupied: Positions currently held by other riders.

        Returns:
            Concatenated waypoint list for the whole trip.
        """
        occupied_list = list(occupied) if occupied else []
        route: List[Point] = []
        current = start
        for stop in stops:
            leg = self.plan(current, stop, occupied_list)
            route.extend(leg)
            current = stop
        return route
