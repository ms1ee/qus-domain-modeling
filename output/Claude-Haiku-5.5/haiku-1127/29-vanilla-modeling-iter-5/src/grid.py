"""Grid coordinate system for the simulated 800x800 map.

The map is split into an 8x8 grid of 100x100 cells. Input coordinates are
converted to the center point of their cell. Points whose x or y coordinate
is a multiple of 100 lie on a street.
"""

from dataclasses import dataclass
from typing import List, Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE  # 8


def is_valid_coordinate(value: object) -> bool:
    """Return True when ``value`` is an integer in the range 0..MAP_SIZE.

    Args:
        value: Candidate coordinate.

    Returns:
        Validity flag.
    """
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAP_SIZE


def validate_point(x: object, y: object) -> None:
    """Raise ``ValueError`` if either coordinate is outside the map.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Raises:
        ValueError: If a coordinate is not an integer in range.
    """
    if not is_valid_coordinate(x) or not is_valid_coordinate(y):
        raise ValueError(
            f"coordinates must be integers in the range 0-{MAP_SIZE}, got ({x}, {y})"
        )


def cell_index(value: int) -> int:
    """Return the grid index (0..7) of a coordinate, clamping the edge value.

    Args:
        value: Coordinate in map units.

    Returns:
        Index of the grid cell along that axis.
    """
    return min(max(int(value) // CELL_SIZE, 0), GRID_DIM - 1)


def cell_center(value: int) -> int:
    """Return the center coordinate of the cell containing ``value``.

    Implements ``center = (value // 100) * 100 + 50`` with edge clamping.

    Args:
        value: Coordinate in map units.

    Returns:
        Center coordinate of the containing cell.
    """
    return cell_index(value) * CELL_SIZE + CELL_SIZE // 2


def to_grid_center(x: int, y: int) -> Tuple[int, int]:
    """Convert an input point to the center of its grid cell.

    Args:
        x: Input X coordinate (0-800).
        y: Input Y coordinate (0-800).

    Returns:
        Tuple ``(center_x, center_y)``.

    Raises:
        ValueError: If the coordinates are invalid.
    """
    validate_point(x, y)
    return cell_center(x), cell_center(y)


def is_street_point(x: int, y: int) -> bool:
    """Return True if the point lies on a street (grid line).

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True when x or y is a multiple of the cell size.
    """
    return x % CELL_SIZE == 0 or y % CELL_SIZE == 0


def nearest_street_line(value: float) -> int:
    """Return the nearest grid line coordinate to ``value``.

    Args:
        value: Coordinate in map units.

    Returns:
        Nearest multiple of CELL_SIZE within the map bounds.
    """
    line = int(round(value / CELL_SIZE)) * CELL_SIZE
    return min(max(line, 0), MAP_SIZE)


@dataclass
class GridCell:
    """A single cell of the 8x8 grid.

    Attributes:
        grid_x: Column index (0-7).
        grid_y: Row index (0-7).
        center_x: X coordinate of the cell center.
        center_y: Y coordinate of the cell center.
        is_street: Whether the cell center lies on a road.
    """

    grid_x: int
    grid_y: int
    center_x: int
    center_y: int
    is_street: bool


class Grid:
    """The 800x800 map partitioned into 64 cells.

    Attributes:
        map_size: Map side length in units.
        cell_size: Cell side length in units.
        dim: Number of cells per row/column.
        cells: All grid cells in row-major order.
    """

    def __init__(self, map_size: int = MAP_SIZE, cell_size: int = CELL_SIZE) -> None:
        """Create the grid.

        Args:
            map_size: Map side length in units.
            cell_size: Cell side length in units.
        """
        self.map_size = map_size
        self.cell_size = cell_size
        self.dim = map_size // cell_size
        self.cells: List[GridCell] = []
        for gy in range(self.dim):
            for gx in range(self.dim):
                center_x = gx * cell_size + cell_size // 2
                center_y = gy * cell_size + cell_size // 2
                self.cells.append(
                    GridCell(gx, gy, center_x, center_y, is_street_point(center_x, center_y))
                )

    def cell_at(self, x: int, y: int) -> GridCell:
        """Return the cell containing the point ``(x, y)``.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            The matching GridCell.
        """
        gx = min(max(x // self.cell_size, 0), self.dim - 1)
        gy = min(max(y // self.cell_size, 0), self.dim - 1)
        return self.cells[gy * self.dim + gx]
