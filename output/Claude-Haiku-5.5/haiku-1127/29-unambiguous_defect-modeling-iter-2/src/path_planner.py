"""Grid-based path planning for riders.

Riders travel along streets (grid lines where x or y is a multiple of 100).
A route is a list of axis-aligned waypoints. Only the final approach into a
restaurant/customer cell and the exit from a cell leave the streets.
Riders never block each other, so no deadlock can occur on the street
network; the planner therefore only needs to guarantee axis-aligned legs.
"""

import logging
from typing import List, Optional, Sequence

from grid_map import (CELL_SIZE, GridMap, Point, cell_corner, is_on_street,
                      to_grid_center, manhattan)

logger = logging.getLogger(__name__)


class PathPlanner:
    """Plans street-first, axis-aligned routes on the 8x8 grid.

    Attributes:
        grid_map (GridMap): The map the planner navigates.
        preferStreets (bool): When True, the planner prefers horizontal
            streets whenever the rider is standing on one.
    """

    def __init__(self, grid_map: Optional[GridMap] = None,
                 preferStreets: bool = True):
        """Create a planner.

        Args:
            grid_map (GridMap | None): Map to navigate; a new one is built
                when omitted.
            preferStreets (bool): Street preference flag.
        """
        self.grid_map = grid_map if grid_map is not None else GridMap()
        self.preferStreets = preferStreets

    def plan(self, start: Sequence[int], goal: Sequence[int]) -> List[Point]:
        """Compute waypoints from ``start`` to the centre of ``goal``'s cell.

        The start point is not included in the result. Every waypoint is
        reached by an axis-aligned move. Special cases handled:

        * Start and goal in the same cell: a direct two-leg move inside the
          cell (no detour onto the streets).
        * Start inside a cell (off street): first exit to the cell's corner.
        * Goal is directly above/below the start in the same column: the
          axis-aligned legs reduce to a single vertical movement.

        Args:
            start (tuple[int, int]): Current position of the rider.
            goal (tuple[int, int]): Target location (any point; it is
                snapped to its cell centre).

        Returns:
            list[tuple[int, int]]: Ordered waypoints, possibly empty when
            the rider is already at the target.
        """
        start = (int(start[0]), int(start[1]))
        goal_center = to_grid_center(goal[0], goal[1])
        if start == goal_center:
            return []

        goal_corner = cell_corner(goal_center[0], goal_center[1])
        waypoints: List[Point] = []

        if not is_on_street(start[0], start[1]):
            if cell_corner(start[0], start[1]) == goal_corner:
                # Same cell: move inside the cell only.
                waypoints.append((goal_center[0], start[1]))
                waypoints.append(goal_center)
                return self._compact(start, waypoints)
            if start[0] == goal_center[0]:
                # Directly above or below the target: straight movement.
                waypoints.append(goal_center)
                return self._compact(start, waypoints)
            start_corner = cell_corner(start[0], start[1])
            waypoints.append((start[0], start_corner[1]))
            waypoints.append(start_corner)
            current = start_corner
        else:
            current = start

        if self.preferStreets and current[1] % CELL_SIZE == 0:
            # On a horizontal street: run along it, then turn onto the
            # vertical street of the goal corner.
            waypoints.append((goal_corner[0], current[1]))
        else:
            # On a vertical street: run along it, then turn onto the
            # horizontal street of the goal corner.
            waypoints.append((current[0], goal_corner[1]))
        waypoints.append(goal_corner)
        waypoints.append((goal_center[0], goal_corner[1]))
        waypoints.append(goal_center)
        return self._compact(start, waypoints)

    @staticmethod
    def _compact(start: Point, points: List[Point]) -> List[Point]:
        """Remove consecutive duplicate waypoints.

        Args:
            start (tuple[int, int]): Starting point (excluded from output).
            points (list[tuple[int, int]]): Raw waypoints.

        Returns:
            list[tuple[int, int]]: Waypoints without repeats.
        """
        result: List[Point] = []
        previous = start
        for point in points:
            if point != previous:
                result.append(point)
                previous = point
        return result

    @staticmethod
    def route_length(start: Sequence[int], waypoints: Sequence[Point]) -> int:
        """Return the total travelled length of a route.

        Args:
            start (tuple[int, int]): Starting point of the route.
            waypoints (list[tuple[int, int]]): Route waypoints.

        Returns:
            int: Sum of Manhattan distances between consecutive points.
        """
        total = 0
        previous = (int(start[0]), int(start[1]))
        for point in waypoints:
            total += manhattan(previous, point)
            previous = point
        return total
