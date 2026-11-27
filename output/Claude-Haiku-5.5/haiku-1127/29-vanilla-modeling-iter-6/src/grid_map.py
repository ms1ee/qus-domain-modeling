"""Grid coordinate system for the 800x800 dispatch map.

The map is divided into an 8x8 grid of 100x100 unit cells. Grid lines
(coordinates that are multiples of 100) form the street network. Cell
centers (coordinates such as 50, 150, ..., 750) are the restaurant and
customer locations after coordinate conversion.
"""

from dataclasses import dataclass

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = 8


@dataclass(frozen=True)
class Point:
    """An immutable integer coordinate on the map.

    Attributes:
        x: Horizontal coordinate (0-800).
        y: Vertical coordinate (0-800).
    """

    x: int
    y: int


@dataclass(frozen=True)
class GridCell:
    """One cell of the 8x8 grid.

    Attributes:
        grid_x: Column index of the cell (0-7).
        grid_y: Row index of the cell (0-7).
        center_x: Horizontal coordinate of the cell center.
        center_y: Vertical coordinate of the cell center.
    """

    grid_x: int
    grid_y: int
    center_x: int
    center_y: int


def is_valid_coordinate(value):
    """Check whether ``value`` is an integer within the map range.

    Args:
        value: Candidate coordinate.

    Returns:
        True if ``value`` is an int (not bool) between 0 and 800 inclusive.
    """
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= MAP_SIZE
    )


def clamp_cell_index(value):
    """Return the grid cell index for a coordinate, clamped to the map.

    Args:
        value: Coordinate in map units.

    Returns:
        Cell index in the range 0..GRID_DIMENSION-1.
    """
    index = value // CELL_SIZE
    return max(0, min(GRID_DIMENSION - 1, index))


def to_cell_center(value):
    """Convert a coordinate to the center of its grid cell along one axis.

    Implements ``center = (value // 100) * 100 + 50`` with clamping so that
    the boundary value 800 maps to the center of the last cell (750).

    Args:
        value: Coordinate in map units (0-800).

    Returns:
        The center coordinate of the containing cell.
    """
    return clamp_cell_index(value) * CELL_SIZE + CELL_SIZE // 2


def to_cell_center_point(x, y):
    """Convert a coordinate pair to the center point of its grid cell.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        A Point located at the center of the containing cell.
    """
    return Point(to_cell_center(x), to_cell_center(y))


def is_street_point(x, y):
    """Return True if the point lies on a street (a grid line).

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.

    Returns:
        True when x or y is a multiple of the cell size.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


class GridMap:
    """Represents the 8x8 grid of cells and the street network.

    Attributes:
        map_size: Side length of the map in units.
        cell_size: Side length of one cell in units.
        dimension: Number of cells per row and column.
        cells: List of all GridCell objects in row-major order.
    """

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE,
                 dimension=GRID_DIMENSION):
        """Build the grid and pre-compute all cell centers.

        Args:
            map_size: Side length of the map in units.
            cell_size: Side length of one cell in units.
            dimension: Number of cells per row and column.
        """
        self.map_size = map_size
        self.cell_size = cell_size
        self.dimension = dimension
        self.cells = []
        for grid_y in range(dimension):
            for grid_x in range(dimension):
                self.cells.append(
                    GridCell(
                        grid_x=grid_x,
                        grid_y=grid_y,
                        center_x=grid_x * cell_size + cell_size // 2,
                        center_y=grid_y * cell_size + cell_size // 2,
                    )
                )

    def cell_at(self, x, y):
        """Return the cell containing the point (x, y).

        Args:
            x: Horizontal coordinate.
            y: Vertical coordinate.

        Returns:
            The GridCell that contains the point (boundaries are clamped).
        """
        grid_x = max(0, min(self.dimension - 1, x // self.cell_size))
        grid_y = max(0, min(self.dimension - 1, y // self.cell_size))
        return self.cells[grid_y * self.dimension + grid_x]

    def is_valid(self, x, y):
        """Return True if (x, y) lies inside the map bounds.

        Args:
            x: Horizontal coordinate.
            y: Vertical coordinate.
        """
        return (is_valid_coordinate(x) and is_valid_coordinate(y)
                and x <= self.map_size and y <= self.map_size)

    def is_street(self, x, y):
        """Return True if (x, y) lies on the street network.

        Args:
            x: Horizontal coordinate.
            y: Vertical coordinate.
        """
        return is_street_point(x, y)
