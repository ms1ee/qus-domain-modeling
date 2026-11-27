"""Grid-based path planning for riders on the 8x8 street grid.

Routes are built from axis-aligned segments. When two corner choices exist
the planner prefers the corner whose segments run along streets, i.e. lines
where x or y is a multiple of CELL_SIZE. A rider that is directly above or
below its target simply moves in a straight line (special case).
"""

from typing import List, Tuple

from config import CELL_SIZE, GRID_SIZE

Point = Tuple[int, int]


class PathPlanner:
    """Computes routes and single-tick movement along the street grid."""

    @staticmethod
    def to_cell_center(x: int, y: int) -> Point:
        """Convert a raw coordinate to the centre point of its grid cell.

        Uses ``center = (grid // 100) * 100 + 50``. Out-of-range values are
        clamped to the map boundary.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Tuple ``(center_x, center_y)``.
        """
        max_index = GRID_SIZE - 1
        gx = min(max(int(x), 0) // CELL_SIZE, max_index)
        gy = min(max(int(y), 0) // CELL_SIZE, max_index)
        half = CELL_SIZE // 2
        return (gx * CELL_SIZE + half, gy * CELL_SIZE + half)

    @staticmethod
    def is_street_point(point: Point) -> bool:
        """Return True if the point lies on a street (grid line).

        Args:
            point: Coordinate tuple.
        """
        x, y = point
        return x % CELL_SIZE == 0 or y % CELL_SIZE == 0

    @staticmethod
    def manhattan(a: Point, b: Point) -> int:
        """Return the Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Build an axis-aligned waypoint list from ``start`` to ``goal``.

        Args:
            start: Starting coordinate.
            goal: Destination coordinate.

        Returns:
            Waypoints including both endpoints. A single-element list is
            returned when start equals goal.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return [start]

        sx, sy = start
        gx, gy = goal
        # Directly above/below or left/right of the target: straight line.
        if sx == gx or sy == gy:
            return [start, goal]

        horizontal_corner = (gx, sy)  # move along x first
        vertical_corner = (sx, gy)  # move along y first

        # Count how many of the two segments travel along a street.
        h_score = int(sy % CELL_SIZE == 0) + int(gx % CELL_SIZE == 0)
        v_score = int(sx % CELL_SIZE == 0) + int(gy % CELL_SIZE == 0)
        corner = vertical_corner if v_score > h_score else horizontal_corner
        return [start, corner, goal]

    def route_length(self, start: Point, goal: Point) -> int:
        """Return the total length of the planned route in coordinate units."""
        path = self.plan(start, goal)
        return sum(self.manhattan(a, b) for a, b in zip(path, path[1:]))

    def next_position(self, start: Point, goal: Point, budget: int) -> Point:
        """Advance from ``start`` towards ``goal`` by at most ``budget`` units.

        Every step moves monotonically towards the goal, so the rider never
        oscillates and always converges.

        Args:
            start: Current coordinate.
            goal: Target coordinate.
            budget: Maximum number of coordinate units to travel.

        Returns:
            The new coordinate after movement.
        """
        pos = (int(start[0]), int(start[1]))
        remaining = int(budget)
        for waypoint in self.plan(pos, goal)[1:]:
            while remaining > 0 and pos != waypoint:
                dx = waypoint[0] - pos[0]
                dy = waypoint[1] - pos[1]
                if dx != 0:
                    step = min(abs(dx), remaining)
                    pos = (pos[0] + step if dx > 0 else pos[0] - step, pos[1])
                else:
                    step = min(abs(dy), remaining)
                    pos = (pos[0], pos[1] + step if dy > 0 else pos[1] - step)
                remaining -= step
            if remaining <= 0:
                break
        return pos
