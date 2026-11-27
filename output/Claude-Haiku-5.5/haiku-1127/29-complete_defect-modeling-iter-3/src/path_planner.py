"""Grid-based path planning and map geometry.

The map is 800x800 units divided into an 8x8 grid of 100x100 cells. Every
cell is addressed by its centre point (``col * 100 + 50``). The centre lines
of the cells form the street network, so every centre point is a street
intersection and all movement is axis-aligned along those streets.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[int, int]

MAP_SIZE = 800
GRID_SIZE = 8
CELL_SIZE = 100


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point ``(x, y)``.
        b: Second point ``(x, y)``.

    Returns:
        Sum of absolute coordinate differences.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class GridCell:
    """A single cell of the 8x8 grid.

    Attributes:
        row: Row index (0-7), derived from the y coordinate.
        col: Column index (0-7), derived from the x coordinate.
        center_x: X coordinate of the cell centre.
        center_y: Y coordinate of the cell centre.
        is_street: Whether the cell centre lies on the street network.
    """

    row: int
    col: int
    center_x: int
    center_y: int
    is_street: bool = True


class GridMap:
    """The 8x8 grid map owned by the system manager."""

    def __init__(self, rows: int = GRID_SIZE, cols: int = GRID_SIZE,
                 map_size: int = MAP_SIZE) -> None:
        """Create the grid and populate all cells.

        Args:
            rows: Number of grid rows.
            cols: Number of grid columns.
            map_size: Width and height of the coordinate system.
        """
        self.rows = rows
        self.cols = cols
        self.map_size = map_size
        self.cells: List[List[GridCell]] = [
            [
                GridCell(
                    row=r,
                    col=c,
                    center_x=c * CELL_SIZE + CELL_SIZE // 2,
                    center_y=r * CELL_SIZE + CELL_SIZE // 2,
                )
                for c in range(cols)
            ]
            for r in range(rows)
        ]

    def cell_at(self, x: int, y: int) -> GridCell:
        """Return the grid cell containing the given coordinate.

        Args:
            x: X coordinate (0-800).
            y: Y coordinate (0-800).

        Returns:
            The matching :class:`GridCell`.
        """
        row = PathPlanner.to_cell_index(y)
        col = PathPlanner.to_cell_index(x)
        return self.cells[row][col]


@dataclass
class Route:
    """A planned route made of axis-aligned waypoints.

    Attributes:
        total_distance: Total Manhattan length of the route.
        waypoints: Ordered list of points, starting at the origin.
    """

    total_distance: int = 0
    waypoints: List[Point] = field(default_factory=list)


class PathPlanner:
    """Computes street-following routes on the grid."""

    def __init__(self, grid_size: int = GRID_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create a planner.

        Args:
            grid_size: Number of cells along each axis.
            cell_size: Side length of one cell in coordinate units.
        """
        self.grid_size = grid_size
        self.cell_size = cell_size

    @staticmethod
    def to_cell_index(value: int) -> int:
        """Convert a coordinate to a grid index, clamped to 0-7.

        Args:
            value: Coordinate value (0-800).

        Returns:
            Cell index along one axis.
        """
        return max(0, min(int(value) // CELL_SIZE, GRID_SIZE - 1))

    @staticmethod
    def to_cell_center(value: int) -> int:
        """Convert a coordinate to the centre coordinate of its cell.

        Uses ``center = (value // 100) * 100 + 50``; values at or beyond the
        map edge are clamped into the last cell.

        Args:
            value: Coordinate value (0-800).

        Returns:
            Centre coordinate of the containing cell.
        """
        return PathPlanner.to_cell_index(value) * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def cell_center_point(point: Point) -> Point:
        """Return the cell centre point for an ``(x, y)`` coordinate pair.

        Args:
            point: Coordinate pair.

        Returns:
            Centre point of the containing cell.
        """
        return (PathPlanner.to_cell_center(point[0]),
                PathPlanner.to_cell_center(point[1]))

    def plan(self, start: Point, goal: Point) -> List[Point]:
        """Plan the waypoints from ``start`` to ``goal`` along streets.

        Cases:
            * identical points: no movement;
            * same x or same y (goal directly above/below or beside the
              rider): a single straight street segment;
            * otherwise: a right-angle turn at the corner ``(goal_x, start_y)``.

        Args:
            start: Current position.
            goal: Destination point.

        Returns:
            Waypoints to visit in order, excluding the start point.
        """
        sx, sy = start
        gx, gy = goal
        if (sx, sy) == (gx, gy):
            return []
        if sx == gx or sy == gy:
            return [(gx, gy)]
        return [(gx, sy), (gx, gy)]

    def build_route(self, start: Point, restaurant: Point, customer: Point) -> Route:
        """Build the continuous route start -> restaurant -> customer.

        Args:
            start: Rider's current position.
            restaurant: Restaurant cell centre.
            customer: Customer cell centre.

        Returns:
            A :class:`Route` including the start point as first waypoint.
        """
        waypoints: List[Point] = [start]
        total = 0
        current = start
        for leg_goal in (restaurant, customer):
            for point in self.plan(current, leg_goal):
                total += manhattan(current, point)
                waypoints.append(point)
                current = point
        return Route(total_distance=total, waypoints=waypoints)
