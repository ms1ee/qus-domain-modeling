"""Grid model of the 8x8 city map (800x800 units, 100-unit cells).

Streets run along the grid lines (coordinates that are multiples of 100).
Restaurants and customers are snapped to the centres of the cells, i.e.
coordinates of the form 100 * k + 50.
"""

from dataclasses import dataclass
from typing import List, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
LATTICE_STEP = 50  # routing resolution (half a cell)

Point = Tuple[int, int]


def snap_to_center(value: int, cell_size: int = CELL_SIZE,
                   map_size: int = MAP_SIZE) -> int:
    """Convert a coordinate into the centre of its grid cell.

    Implements ``center = (grid // cell) * cell + cell // 2`` with clamping so
    that the boundary value (for example 800) maps to the last cell.

    Args:
        value: Input coordinate (0 - map_size).
        cell_size: Size of one grid cell.
        map_size: Size of the whole map.

    Returns:
        The integer coordinate of the cell centre along that axis.
    """
    dimension = map_size // cell_size
    index = min(max(int(value) // cell_size, 0), dimension - 1)
    return index * cell_size + cell_size // 2


def cell_index(x: int, y: int, cell_size: int = CELL_SIZE,
               map_size: int = MAP_SIZE) -> Tuple[int, int]:
    """Return the (grid_x, grid_y) index of the cell containing a point.

    Args:
        x: X coordinate.
        y: Y coordinate.
        cell_size: Size of one grid cell.
        map_size: Size of the whole map.

    Returns:
        Tuple of grid indices, clamped to the valid grid range.
    """
    dimension = map_size // cell_size
    gx = min(max(int(x) // cell_size, 0), dimension - 1)
    gy = min(max(int(y) // cell_size, 0), dimension - 1)
    return gx, gy


def is_street_point(x: int, y: int, cell_size: int = CELL_SIZE) -> bool:
    """Return True if the point lies on a street (a grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.
        cell_size: Size of one grid cell.
    """
    return x % cell_size == 0 or y % cell_size == 0


@dataclass
class GridCell:
    """One 100x100 block of the grid.

    ``is_street`` is True for cells on the outer ring of the city, which are
    bordered by the main streets.
    """

    grid_x: int
    grid_y: int
    center_x: int
    center_y: int
    is_street: bool


class GridMap:
    """The 8x8 grid of cells covering the 800x800 coordinate system."""

    def __init__(self, map_size: int = MAP_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Build the grid.

        Args:
            map_size: Width and height of the map in units.
            cell_size: Width and height of one cell in units.

        Raises:
            ValueError: If the sizes are not positive or do not divide evenly.
        """
        if map_size <= 0 or cell_size <= 0 or map_size % cell_size != 0:
            raise ValueError("map_size must be a positive multiple of cell_size")
        self.width = map_size
        self.height = map_size
        self.cell_size = cell_size
        self.dimension = map_size // cell_size
        self.cells: List[List[GridCell]] = []
        last = self.dimension - 1
        for gx in range(self.dimension):
            column: List[GridCell] = []
            for gy in range(self.dimension):
                column.append(GridCell(
                    grid_x=gx,
                    grid_y=gy,
                    center_x=gx * cell_size + cell_size // 2,
                    center_y=gy * cell_size + cell_size // 2,
                    is_street=gx in (0, last) or gy in (0, last),
                ))
            self.cells.append(column)

    def cell_at(self, x: int, y: int) -> GridCell:
        """Return the cell containing the point (x, y)."""
        gx, gy = cell_index(x, y, self.cell_size, self.width)
        return self.cells[gx][gy]

    def contains(self, x: int, y: int) -> bool:
        """Return True if (x, y) lies inside the map boundaries."""
        return 0 <= x <= self.width and 0 <= y <= self.height

    def snap_point(self, x: int, y: int) -> Point:
        """Snap a point to the centre of its grid cell."""
        return (snap_to_center(x, self.cell_size, self.width),
                snap_to_center(y, self.cell_size, self.height))
