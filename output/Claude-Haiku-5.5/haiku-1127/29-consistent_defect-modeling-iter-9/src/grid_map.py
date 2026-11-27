"""Grid map definitions for the 800x800 food delivery city.

The city is an 8x8 grid of 100x100 cells. Streets are the grid lines
(coordinates that are multiples of 100). Restaurants and customers are
located at street intersections (both coordinates multiples of 100).
"""

import logging

logger = logging.getLogger("dispatch.grid")

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = 8
DISPLAY_STEP = 50  # Resolution of the ASCII map in units per character node.


class GridMap:
    """Models the 8x8 cell city grid and its street network."""

    def __init__(self, map_size: int = MAP_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create a grid map.

        Args:
            map_size: Side length of the square map in units.
            cell_size: Side length of one grid cell in units.
        """
        self.map_size = int(map_size)
        self.cell_size = int(cell_size)
        self.grid_dimension = self.map_size // self.cell_size

    def clamp(self, value: float) -> int:
        """Clamp a coordinate into the valid map range.

        Args:
            value: Raw coordinate value.

        Returns:
            Integer coordinate within [0, map_size].
        """
        return max(0, min(self.map_size, int(value)))

    def snap(self, x: float, y: float) -> tuple:
        """Convert a point to the top-left corner of its grid cell.

        Args:
            x: Raw x coordinate.
            y: Raw y coordinate.

        Returns:
            Tuple (x, y) of integers, both multiples of cell_size.
        """
        cs = self.cell_size
        return (self.clamp(x) // cs) * cs, (self.clamp(y) // cs) * cs

    def center_of_cell(self, grid_x: int, grid_y: int) -> tuple:
        """Return the center point of the cell containing (grid_x, grid_y).

        Uses center_x = (grid_x // 100) * 100 + 50 (generalised to cell_size).

        Args:
            grid_x: x coordinate inside the cell.
            grid_y: y coordinate inside the cell.

        Returns:
            Tuple (center_x, center_y).
        """
        cs = self.cell_size
        half = cs // 2
        return (int(grid_x) // cs) * cs + half, (int(grid_y) // cs) * cs + half

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if the point lies on the map.

        Args:
            x: x coordinate.
            y: y coordinate.
        """
        return 0 <= x <= self.map_size and 0 <= y <= self.map_size

    def is_street(self, x: int, y: int) -> bool:
        """Return True if the point lies on a street (grid line).

        Args:
            x: x coordinate.
            y: y coordinate.
        """
        if not self.in_bounds(x, y):
            return False
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x: int, y: int) -> bool:
        """Return True if the point is a street intersection.

        Args:
            x: x coordinate.
            y: y coordinate.
        """
        return x % self.cell_size == 0 and y % self.cell_size == 0 and self.in_bounds(x, y)

    def cell_of(self, x: float, y: float) -> tuple:
        """Return the (row, col) grid cell index for a point.

        Args:
            x: x coordinate.
            y: y coordinate.
        """
        limit = self.grid_dimension - 1
        col = min(self.clamp(x) // self.cell_size, limit)
        row = min(self.clamp(y) // self.cell_size, limit)
        return row, col
