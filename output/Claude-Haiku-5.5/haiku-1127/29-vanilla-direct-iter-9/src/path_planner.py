"""Grid-based path planning for the 800x800 dispatch map.

The map is an 8x8 grid of 100x100 cells. Streets lie on grid lines, i.e. points
where ``x`` or ``y`` is a multiple of 100. Restaurants and customers are placed
at cell centres (50, 150, ..., 750). Routes are Manhattan routes made of at most
two axis-aligned segments (one right-angle turn). Between the two possible
corners the planner prefers the one whose segments run along streets.

Every waypoint is reached by monotone axis-aligned movement, so a rider always
makes progress towards its target and cannot deadlock.
"""

from typing import List, Sequence, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = 8


class PathPlanner:
    """Stateless helper providing grid-based route planning and stepping."""

    @staticmethod
    def cell_center(value: int) -> int:
        """Convert a coordinate into the centre of its grid cell.

        Implements ``center = (value // 100) * 100 + 50``. Values equal to the
        map edge (800) are clamped into the last cell.

        Args:
            value: Input coordinate, expected in the range 0-800.

        Returns:
            The centre coordinate of the containing cell.
        """
        clamped = max(0, min(MAP_SIZE - 1, int(value)))
        return (clamped // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def cell_of(x: int, y: int) -> Point:
        """Return the (column, row) grid index that contains a point.

        Args:
            x: X coordinate, 0-800.
            y: Y coordinate, 0-800.

        Returns:
            Tuple ``(col, row)`` with both values in the range 0-7.
        """
        col = max(0, min(GRID_CELLS - 1, int(x) // CELL_SIZE))
        row = max(0, min(GRID_CELLS - 1, int(y) // CELL_SIZE))
        return col, row

    @staticmethod
    def is_on_street(x: int, y: int) -> bool:
        """Return True when a point lies on a street (grid line)."""
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def is_straight(start: Point, goal: Point) -> bool:
        """Return True when the goal is directly above/below or left/right.

        This is the special case in which the rider moves along a single axis.
        """
        return start[0] == goal[0] or start[1] == goal[1]

    @classmethod
    def plan(cls, start: Point, goal: Point) -> List[Point]:
        """Plan a route from ``start`` to ``goal``.

        The result is a list of waypoints ending at ``goal``. An empty list is
        returned when the start already equals the goal. A straight route
        returns only the goal. Otherwise the route contains one corner followed
        by the goal. The corner is chosen so that the segments lie along streets
        whenever possible; ties prefer horizontal-first movement.

        Args:
            start: Current position ``(x, y)``.
            goal: Target position ``(x, y)``.

        Returns:
            Ordered list of waypoints ``[(x, y), ...]``.
        """
        sx, sy = start
        gx, gy = goal
        if (sx, sy) == (gx, gy):
            return []
        if cls.is_straight(start, goal):
            return [(gx, gy)]

        corner_h = (gx, sy)  # horizontal segment at y=sy, vertical at x=gx
        corner_v = (sx, gy)  # vertical segment at x=sx, horizontal at y=gy
        score_h = int(sy % CELL_SIZE == 0) + int(gx % CELL_SIZE == 0)
        score_v = int(sx % CELL_SIZE == 0) + int(gy % CELL_SIZE == 0)
        corner = corner_h if score_h >= score_v else corner_v
        return [corner, (gx, gy)]

    @staticmethod
    def advance(
        x: int, y: int, waypoints: Sequence[Point], speed: int
    ) -> Tuple[Point, List[Point]]:
        """Move up to ``speed`` units along the planned waypoints.

        Movement along each segment is axis-aligned; when a diagonal offset
        occurs the x axis is handled before the y axis.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            waypoints: Remaining waypoints, next target first.
            speed: Maximum distance (units) travelled this tick.

        Returns:
            A tuple ``((new_x, new_y), remaining_waypoints)``.
        """
        remaining = list(waypoints)
        budget = max(0, int(speed))
        while budget > 0 and remaining:
            tx, ty = remaining[0]
            if (x, y) == (tx, ty):
                remaining.pop(0)
                continue
            if x != tx:
                step = min(abs(tx - x), budget)
                x += step if tx > x else -step
                budget -= step
            if budget > 0 and y != ty:
                step = min(abs(ty - y), budget)
                y += step if ty > y else -step
                budget -= step
            if (x, y) == (tx, ty):
                remaining.pop(0)
        return (x, y), remaining
