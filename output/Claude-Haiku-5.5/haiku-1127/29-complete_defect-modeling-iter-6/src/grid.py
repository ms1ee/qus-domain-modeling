"""Grid coordinate system for the 800x800 delivery map.

The map is an 8x8 grid of 100x100 unit cells. Streets are the grid lines
where an x or y coordinate is a multiple of 100. Order locations are
converted to cell centres using ``center = (value // 100) * 100 + 50``.
"""

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIMENSION = MAP_SIZE // CELL_SIZE  # 8 x 8 = 64 cells
MIN_COORDINATE = 0
MAX_COORDINATE = MAP_SIZE


class GridCell:
    """A single 100x100 cell of the map.

    Attributes:
        grid_x: Column index (0-7).
        grid_y: Row index (0-7).
        center_x: X coordinate of the cell centre.
        center_y: Y coordinate of the cell centre.
        is_street: Always False for cell interiors; streets are the grid
            lines that bound the cells.
    """

    def __init__(self, grid_x: int, grid_y: int) -> None:
        """Create a cell and compute its centre point.

        Args:
            grid_x: Column index of the cell.
            grid_y: Row index of the cell.
        """
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.center_x = grid_x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = grid_y * CELL_SIZE + CELL_SIZE // 2
        self.is_street = False


class Grid:
    """The 8x8 grid of cells covering the map."""

    def __init__(self, map_size: int = MAP_SIZE,
                 cell_size: int = CELL_SIZE) -> None:
        """Build the grid.

        Args:
            map_size: Width and height of the map in units.
            cell_size: Width and height of one cell in units.

        Raises:
            ValueError: If the map size is not a multiple of the cell size.
        """
        if cell_size <= 0 or map_size % cell_size != 0:
            raise ValueError("map_size must be a multiple of cell_size")
        self.map_size = map_size
        self.cell_size = cell_size
        self.dimension = map_size // cell_size
        self.cells = [[GridCell(gx, gy) for gy in range(self.dimension)]
                      for gx in range(self.dimension)]

    def cell_index(self, value: int) -> int:
        """Return the grid index containing a coordinate (clamped to the map).

        Args:
            value: A coordinate along one axis.

        Returns:
            Index in ``range(dimension)``. The map edge 800 maps to the last
            cell.
        """
        index = int(value) // self.cell_size
        return min(max(index, 0), self.dimension - 1)

    def cell_at(self, x: int, y: int) -> GridCell:
        """Return the cell that contains the point (x, y)."""
        return self.cells[self.cell_index(x)][self.cell_index(y)]

    def is_street_point(self, x: int, y: int) -> bool:
        """Return True if (x, y) lies on a street (a grid line)."""
        return x % self.cell_size == 0 or y % self.cell_size == 0

    def is_intersection(self, x: int, y: int) -> bool:
        """Return True if (x, y) is a street crossing point."""
        return x % self.cell_size == 0 and y % self.cell_size == 0


def to_cell_center(value: int) -> int:
    """Convert a raw coordinate to the centre of its grid cell.

    Implements ``center = (value // 100) * 100 + 50``. Values at the map edge
    (800) are placed in the last cell so the centre stays within the map.

    Args:
        value: Raw coordinate in the range 0-800.

    Returns:
        The cell centre coordinate along the same axis.
    """
    index = min(max(int(value), 0) // CELL_SIZE, GRID_DIMENSION - 1)
    return index * CELL_SIZE + CELL_SIZE // 2


def validate_coordinate(value, label: str = "coordinate") -> int:
    """Check that a value is an integer within the map range.

    Args:
        value: The value to check.
        label: Name used in error messages.

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer, got {value!r}")
    if not MIN_COORDINATE <= value <= MAX_COORDINATE:
        raise ValueError(
            f"{label} {value} is outside the range "
            f"{MIN_COORDINATE}-{MAX_COORDINATE}")
    return value
