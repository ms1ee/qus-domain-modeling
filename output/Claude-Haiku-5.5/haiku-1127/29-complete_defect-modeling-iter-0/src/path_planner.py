"""Grid-based path planning for the 8x8 city map.

The map is an 800x800 coordinate system divided into an 8x8 grid of
100x100 cells. Each cell is addressed by integer indices ``(gx, gy)`` in the
range ``0..7``. Riders always travel between cell centers using right-angle
moves along streets, so every route is a sequence of axis-aligned steps.
"""

import heapq
import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_CELLS = 8
CELL_HALF = CELL_SIZE // 2

STEP_COST = 1.0
TURN_COST = 0.1
OCCUPIED_COST = 0.5
DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0))
NO_DIRECTION = -1


def axis_cell(value):
    """Convert one coordinate into a grid cell index.

    Values are clamped into the valid range so that the boundary value 800
    maps to the last cell.

    Args:
        value: Coordinate in units (0-800).

    Returns:
        Cell index in ``0..GRID_CELLS-1``.
    """
    index = int(value) // CELL_SIZE
    return min(max(index, 0), GRID_CELLS - 1)


def cell_center_coord(value):
    """Return the center coordinate of the cell containing ``value``.

    Implements ``center = (value // 100) * 100 + 50``.

    Args:
        value: Coordinate in units (0-800).

    Returns:
        Integer center coordinate of the containing cell.
    """
    return axis_cell(value) * CELL_SIZE + CELL_HALF


def cell_of(x, y):
    """Return the grid cell indices containing point ``(x, y)``.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        Tuple ``(gx, gy)``.
    """
    return axis_cell(x), axis_cell(y)


def cell_center(gx, gy):
    """Return the center point of grid cell ``(gx, gy)``.

    Args:
        gx: Horizontal cell index.
        gy: Vertical cell index.

    Returns:
        Tuple ``(x, y)`` in map units.
    """
    return gx * CELL_SIZE + CELL_HALF, gy * CELL_SIZE + CELL_HALF


def manhattan(a, b):
    """Return the Manhattan distance between two points.

    Args:
        a: Tuple ``(x, y)``.
        b: Tuple ``(x, y)``.

    Returns:
        Integer distance in map units.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def straight_line_case(a, b):
    """Return True when two cells share a row or column.

    This is the special case where the target is directly above, below,
    left or right of the rider; movement is then a single straight line.

    Args:
        a: Cell tuple ``(gx, gy)``.
        b: Cell tuple ``(gx, gy)``.

    Returns:
        True if the cells are aligned on a street.
    """
    return a[0] == b[0] or a[1] == b[1]


class Grid:
    """Rectangular grid of cells used for planning and display.

    Attributes:
        width: Number of columns.
        height: Number of rows.
        cell_size: Size of one cell in map units.
    """

    def __init__(self, width=GRID_CELLS, height=GRID_CELLS, cell_size=CELL_SIZE):
        """Create a grid.

        Args:
            width: Number of columns.
            height: Number of rows.
            cell_size: Cell edge length in map units.
        """
        self.width = width
        self.height = height
        self.cell_size = cell_size

    def in_bounds(self, gx, gy):
        """Return True if the cell index lies inside the grid."""
        return 0 <= gx < self.width and 0 <= gy < self.height

    def neighbors(self, gx, gy):
        """Yield the in-bounds 4-neighbours of a cell."""
        for dx, dy in DIRECTIONS:
            nx, ny = gx + dx, gy + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def cells(self):
        """Return a list of all cell indices in row-major order."""
        return [(gx, gy) for gy in range(self.height) for gx in range(self.width)]

    def center(self, gx, gy):
        """Return the map coordinates of a cell center."""
        return cell_center(gx, gy)


@dataclass
class Route:
    """A planned route over grid cells.

    Attributes:
        waypoints: Ordered list of grid cell tuples ``(gx, gy)``.
        total_distance: Length of the route in map units.
    """

    waypoints: list
    total_distance: int

    def travel_ticks(self, speed):
        """Return the number of ticks needed to travel the route.

        Args:
            speed: Rider speed in units per tick (must be positive).

        Returns:
            Integer tick count, rounded up.
        """
        if speed <= 0:
            raise ValueError("speed must be positive")
        return -(-self.total_distance // speed)


class PathPlanner:
    """Grid-based route planner.

    Uses Dijkstra's algorithm over ``(cell, incoming direction)`` states.
    Straight movement along streets is preferred (turns carry a small cost),
    and cells occupied by other riders carry a penalty so that riders avoid
    congestion and path conflicts without deadlocking.

    Attributes:
        grid: The Grid the planner operates on.
    """

    def __init__(self, grid=None):
        """Create a planner.

        Args:
            grid: Optional Grid; defaults to the 8x8 city grid.
        """
        self.grid = grid or Grid()

    def plan_route(self, start, goal, occupied=None):
        """Plan a right-angle route between two grid cells.

        Args:
            start: Start cell ``(gx, gy)``.
            goal: Goal cell ``(gx, gy)``.
            occupied: Optional iterable of cells occupied by other riders.

        Returns:
            Route object whose waypoints start at ``start`` and end at ``goal``.

        Raises:
            ValueError: If start or goal lies outside the grid.
            RuntimeError: If no route can be found (should not happen).
        """
        occupied = set(occupied or ())
        if not self.grid.in_bounds(*start) or not self.grid.in_bounds(*goal):
            raise ValueError(f"cells {start} / {goal} are outside the grid")
        if start == goal:
            return Route([start], 0)

        start_key = (start, NO_DIRECTION)
        best = {start_key: 0.0}
        previous = {}
        heap = [(0.0, 0, start_key)]
        counter = 1
        end_key = None

        while heap:
            cost, _, key = heapq.heappop(heap)
            if cost > best.get(key, math.inf):
                continue
            cell, direction = key
            if cell == goal:
                end_key = key
                break
            for new_direction, (dx, dy) in enumerate(DIRECTIONS):
                nxt = (cell[0] + dx, cell[1] + dy)
                if not self.grid.in_bounds(*nxt):
                    continue
                step = STEP_COST
                if direction != NO_DIRECTION and direction != new_direction:
                    step += TURN_COST
                if nxt in occupied and nxt != goal:
                    step += OCCUPIED_COST
                next_key = (nxt, new_direction)
                new_cost = cost + step
                if new_cost < best.get(next_key, math.inf):
                    best[next_key] = new_cost
                    previous[next_key] = key
                    heapq.heappush(heap, (new_cost, counter, next_key))
                    counter += 1

        if end_key is None:
            raise RuntimeError(f"no route from {start} to {goal}")

        cells = []
        key = end_key
        while key is not None:
            cells.append(key[0])
            key = previous.get(key)
        cells.reverse()
        total = (len(cells) - 1) * CELL_SIZE
        logger.debug("Planned route %s -> %s (%d units)", start, goal, total)
        return Route(cells, total)
