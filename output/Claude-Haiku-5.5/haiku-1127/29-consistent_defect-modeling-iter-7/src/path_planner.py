"""Grid-based path planning for the food delivery simulator.

The city is an 800x800 unit map divided into an 8x8 grid of 100x100 cells.
Streets run along the grid lines (a coordinate that is a multiple of 100).
Restaurant and customer locations sit on grid corners, so every route can be
expressed as straight street segments joined by right-angle turns.

Riders never block each other: they may share streets, which avoids
deadlocks by construction. Path conflicts are resolved by always preferring
the route whose legs both lie on streets.
"""

import math
from typing import List, Tuple

Point = Tuple[int, int]

DEFAULT_GRID_SIZE = 8
DEFAULT_CELL_SIZE = 100
DEFAULT_MAP_SIZE = DEFAULT_GRID_SIZE * DEFAULT_CELL_SIZE


def snap_to_cell(value: int, cell_size: int = DEFAULT_CELL_SIZE,
                 map_size: int = DEFAULT_MAP_SIZE) -> int:
    """Snap a coordinate to the top-left corner of its grid cell.

    Example: ``150 -> 100`` and ``799 -> 700``. Results are clamped to the map.

    Args:
        value: Raw coordinate.
        cell_size: Size of one grid cell in units.
        map_size: Size of the map in units.

    Returns:
        The snapped integer coordinate in ``[0, map_size]``.
    """
    snapped = (int(value) // cell_size) * cell_size
    return max(0, min(snapped, map_size))


class PathPlanner:
    """Plans street-following routes and single movement steps.

    Attributes:
        grid_size: Number of grid cells per side (8).
        cell_size: Size of a grid cell in units (100).
        map_size: Total map size in units.
    """

    def __init__(self, grid_size: int = DEFAULT_GRID_SIZE,
                 cell_size: int = DEFAULT_CELL_SIZE) -> None:
        """Create a planner for a square grid.

        Args:
            grid_size: Number of cells per side.
            cell_size: Size of each cell in units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.map_size = grid_size * cell_size

    def is_on_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (a grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x: int, y: int) -> bool:
        """Return True if the point is a grid intersection."""
        return x % self.cell_size == 0 and y % self.cell_size == 0

    def is_within_map(self, x: int, y: int) -> bool:
        """Return True if the point lies inside the map bounds."""
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def _leg_is_street(self, start: Point, end: Point) -> bool:
        """Return True if a straight leg runs along a street line."""
        if start[1] == end[1]:
            return start[1] % self.cell_size == 0
        if start[0] == end[0]:
            return start[0] % self.cell_size == 0
        return False

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Plan a street-following route from ``start`` to ``goal``.

        Straight routes are returned as two points. Otherwise an L-shaped
        route with one right-angle turn is produced. When both L-shapes are
        possible, the one whose legs both lie on streets is preferred, and
        horizontal-first is used as the tie breaker.

        Args:
            start: Starting point.
            goal: Destination point.

        Returns:
            List of waypoints including ``start`` and ``goal``.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return [start]
        if start[0] == goal[0] or start[1] == goal[1]:
            return [start, goal]

        corner_h = (goal[0], start[1])
        corner_v = (start[0], goal[1])
        score_h = (self._leg_is_street(start, corner_h)
                   + self._leg_is_street(corner_h, goal))
        score_v = (self._leg_is_street(start, corner_v)
                   + self._leg_is_street(corner_v, goal))
        corner = corner_v if score_v > score_h else corner_h
        return [start, corner, goal]

    def next_step(self, x: int, y: int, goal_x: int, goal_y: int,
                  budget: int) -> Tuple[int, int, int]:
        """Compute one movement step toward a goal along streets.

        Special cases:
            * Target directly above/below: moves purely vertically.
            * Target directly left/right: moves purely horizontally.
            * Otherwise horizontal movement is preferred on horizontal
              streets, and vertical movement on vertical streets.

        Args:
            x: Current x coordinate.
            y: Current y coordinate.
            goal_x: Target x coordinate.
            goal_y: Target y coordinate.
            budget: Maximum distance that may be covered this tick.

        Returns:
            Tuple ``(new_x, new_y, distance_used)``.
        """
        dx = goal_x - x
        dy = goal_y - y
        if (dx == 0 and dy == 0) or budget <= 0:
            return x, y, 0

        c = self.cell_size
        if dx != 0 and y % c == 0:
            horizontal = True
        elif dy != 0 and x % c == 0:
            horizontal = False
        elif dx != 0:
            horizontal = True
        else:
            horizontal = False

        if horizontal:
            step = min(budget, abs(dx))
            return x + (1 if dx > 0 else -1) * step, y, step
        step = min(budget, abs(dy))
        return x, y + (1 if dy > 0 else -1) * step, step

    @staticmethod
    def route_length(points: List[Point]) -> int:
        """Return the total Manhattan length of a polyline route."""
        total = 0
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            total += abs(bx - ax) + abs(by - ay)
        return total

    @staticmethod
    def estimate_ticks(distance: float, speed: int) -> int:
        """Return the number of ticks needed to cover ``distance``.

        Args:
            distance: Distance in units.
            speed: Speed in units per tick (must be positive).

        Returns:
            Ceiling of ``distance / speed``.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        return max(0, math.ceil(distance / speed))
