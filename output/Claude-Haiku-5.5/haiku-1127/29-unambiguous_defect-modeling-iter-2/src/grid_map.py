"""Grid map definitions and coordinate helpers.

The map is an 800x800 coordinate system divided into an 8x8 grid of 100x100
cells. Grid lines (x or y multiple of 100) are streets. Restaurant and
customer locations are the centres of cells (for example x = 50, 150, ...).
All coordinates are integers in the range 0-800.
"""

from typing import Dict, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = 8
CELL_HALF = CELL_SIZE // 2

Point = Tuple[int, int]


def clamp_coordinate(value) -> int:
    """Convert a value to an int and clamp it to the map range 0-800.

    Args:
        value (int | float | str): Raw coordinate.

    Returns:
        int: Clamped integer coordinate.
    """
    return max(0, min(MAP_SIZE, int(value)))


def cell_index(value) -> int:
    """Return the grid index (0-7) of the cell containing a coordinate.

    Args:
        value (int): Coordinate along one axis.

    Returns:
        int: Cell index between 0 and GRID_DIMENSION - 1.
    """
    return min(clamp_coordinate(value) // CELL_SIZE, GRID_DIMENSION - 1)


def to_grid_center(x, y) -> Point:
    """Transform arbitrary coordinates into the centre of their grid cell.

    Implements ``center_x = (grid_x // 100) * 100 + 50``.

    Args:
        x (int): X coordinate (0-800, out-of-range values are clamped).
        y (int): Y coordinate (0-800, out-of-range values are clamped).

    Returns:
        tuple[int, int]: Cell centre coordinates.
    """
    return (cell_index(x) * CELL_SIZE + CELL_HALF,
            cell_index(y) * CELL_SIZE + CELL_HALF)


def cell_corner(x, y) -> Point:
    """Return the bottom-left street intersection of the cell containing a point.

    Args:
        x (int): X coordinate.
        y (int): Y coordinate.

    Returns:
        tuple[int, int]: Intersection coordinates (both multiples of 100).
    """
    return cell_index(x) * CELL_SIZE, cell_index(y) * CELL_SIZE


def is_on_street(x, y) -> bool:
    """Return True if the point lies on a street (grid line).

    Args:
        x (int): X coordinate.
        y (int): Y coordinate.

    Returns:
        bool: True when x or y is a multiple of 100.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def is_cell_center(x, y) -> bool:
    """Return True if the point is the centre of a grid cell.

    Args:
        x (int): X coordinate.
        y (int): Y coordinate.

    Returns:
        bool: True for restaurant/customer location points.
    """
    return x % CELL_SIZE == CELL_HALF and y % CELL_SIZE == CELL_HALF


def manhattan(a, b) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a (tuple[int, int]): First point.
        b (tuple[int, int]): Second point.

    Returns:
        int: |ax - bx| + |ay - by|.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class GridCell:
    """One 100x100 cell of the map.

    Attributes:
        grid_x (int): Column index (0-7).
        grid_y (int): Row index (0-7).
        centerX (int): X coordinate of the cell centre.
        centerY (int): Y coordinate of the cell centre.
        isRoad (bool): True, the cell is bounded by streets.
        isLocation (bool): True, the centre can hold a restaurant/customer.
    """

    def __init__(self, grid_x: int, grid_y: int):
        """Create a cell at the given grid index.

        Args:
            grid_x (int): Column index (0-7).
            grid_y (int): Row index (0-7).
        """
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.centerX = grid_x * CELL_SIZE + CELL_HALF
        self.centerY = grid_y * CELL_SIZE + CELL_HALF
        self.isRoad = True
        self.isLocation = True


class GridMap:
    """The 8x8 grid of cells representing the 800x800 city.

    Attributes:
        mapSize (int): Map side length in units.
        cellSize (int): Side length of one cell in units.
        gridDimension (int): Number of cells per row/column.
        cells (dict): Mapping (grid_x, grid_y) -> GridCell.
    """

    def __init__(self):
        """Build all 64 cells of the map."""
        self.mapSize = MAP_SIZE
        self.cellSize = CELL_SIZE
        self.gridDimension = GRID_DIMENSION
        self.cells: Dict[Point, GridCell] = {
            (gx, gy): GridCell(gx, gy)
            for gx in range(GRID_DIMENSION)
            for gy in range(GRID_DIMENSION)
        }

    def get_cell(self, x, y) -> GridCell:
        """Return the cell containing the given coordinate.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.

        Returns:
            GridCell: The containing cell.
        """
        return self.cells[(cell_index(x), cell_index(y))]
