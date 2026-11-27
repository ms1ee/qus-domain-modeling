"""Grid-based path planning on the 8x8 street grid.

Streets are the grid lines at multiples of 100. Cell centers (x and y both
ending in 50) are never on a street, so every route ends with a short
off-street leg into the target cell. Routes are made of axis-aligned legs
(right-angle turns only). Riders never block each other, so no deadlock can
occur; path conflicts are resolved by allowing riders to share positions.
"""

import math
from dataclasses import dataclass, field
from itertools import product

from config import CELL_SIZE, GRID_SIZE, MAP_SIZE

Point = tuple


def manhattan(a, b) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: ``(x, y)`` point.
        b: ``(x, y)`` point.

    Returns:
        int: ``|ax - bx| + |ay - by|``.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_street_point(point, cell_size: int = CELL_SIZE) -> bool:
    """Return True when a point lies on a street (grid line).

    Args:
        point: ``(x, y)`` point.
        cell_size: Size of a grid cell.

    Returns:
        bool: True if x or y is a multiple of the cell size.
    """
    return point[0] % cell_size == 0 or point[1] % cell_size == 0


@dataclass
class GridCell:
    """One cell of the 8x8 grid map.

    Attributes:
        grid_x: Column index (0-7).
        grid_y: Row index (0-7).
        center_x: X coordinate of the cell center.
        center_y: Y coordinate of the cell center.
        is_street: Whether the cell center lies on a street line.
    """

    grid_x: int
    grid_y: int
    center_x: int
    center_y: int
    is_street: bool = False


@dataclass
class Route:
    """A planned route from a start point through a list of waypoints.

    Attributes:
        start: Starting ``(x, y)`` point.
        waypoints: Ordered list of ``(x, y)`` points ending at the destination.
    """

    start: Point
    waypoints: list = field(default_factory=list)

    @property
    def total_distance(self) -> int:
        """Total Manhattan length of the route in units.

        Returns:
            int: Sum of leg lengths.
        """
        total = 0
        current = tuple(self.start)
        for point in self.waypoints:
            total += manhattan(current, point)
            current = point
        return total

    def estimated_ticks(self, speed: int) -> int:
        """Estimate the number of ticks needed to traverse the route.

        Args:
            speed: Rider speed in units per tick (must be positive).

        Returns:
            int: Ceiling of ``total_distance / speed``.

        Raises:
            ValueError: If speed is not positive.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        return (self.total_distance + speed - 1) // speed


class PathPlanner:
    """Computes right-angle, street-preferring routes on the grid.

    Attributes:
        grid_size: Number of cells per axis (8).
        cell_size: Size of each cell in units (100).
        map_size: Total map size in units (800).
    """

    def __init__(self, grid_size: int = GRID_SIZE, cell_size: int = CELL_SIZE):
        """Create a planner for the given grid geometry.

        Args:
            grid_size: Number of cells per axis.
            cell_size: Size of each cell in units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.map_size = grid_size * cell_size

    def is_street(self, point) -> bool:
        """Return True if the point lies on a street of this planner's grid.

        Args:
            point: ``(x, y)`` point.

        Returns:
            bool: Whether the point is on a street line.
        """
        return is_street_point(point, self.cell_size)

    def grid_cells(self) -> list:
        """Build the list of all grid cells (64 for an 8x8 grid).

        Returns:
            list[GridCell]: Cells in row-major order.
        """
        half = self.cell_size // 2
        cells = []
        for gx, gy in product(range(self.grid_size), repeat=2):
            cx = gx * self.cell_size + half
            cy = gy * self.cell_size + half
            cells.append(GridCell(gx, gy, cx, cy, self.is_street((cx, cy))))
        return cells

    def plan(self, start, goal) -> list:
        """Plan the waypoints from ``start`` to ``goal``.

        Straight-line moves are used when both points share an x or y
        coordinate (a rider directly above or below the target). Otherwise a
        single right-angle corner is chosen, preferring the leg that runs
        along a street.

        Args:
            start: Current ``(x, y)`` position.
            goal: Destination ``(x, y)`` position.

        Returns:
            list: Waypoints ending at ``goal``; empty if already there.
        """
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return []
        if start[0] == goal[0] or start[1] == goal[1]:
            return [goal]

        # Horizontal-first corner leaves start along y = start.y.
        horizontal_corner = (goal[0], start[1])
        # Vertical-first corner leaves start along x = start.x.
        vertical_corner = (start[0], goal[1])

        def score(index, corner):
            leg_on_street = (start[1] % self.cell_size == 0 if index == 0
                             else start[0] % self.cell_size == 0)
            return (not leg_on_street, not self.is_street(corner), index)

        candidates = [(horizontal_corner, 0), (vertical_corner, 1)]
        corner, _ = min(candidates, key=lambda item: score(item[1], item[0]))
        return [corner, goal]

    def plan_route(self, start, stops) -> Route:
        """Plan a continuous route through several destinations in order.

        Used for the restaurant-then-customer path of an order.

        Args:
            start: Starting ``(x, y)`` position.
            stops: Ordered list of ``(x, y)`` destinations.

        Returns:
            Route: Combined route through all stops.
        """
        waypoints = []
        current = (int(start[0]), int(start[1]))
        for stop in stops:
            waypoints.extend(self.plan(current, stop))
            current = (int(stop[0]), int(stop[1]))
        return Route(start=(int(start[0]), int(start[1])), waypoints=waypoints)
