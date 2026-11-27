"""Coordinate helpers and the Location value object.

The map is ``map_size`` x ``map_size`` units, split into square cells of
``cell_size`` units. Input coordinates are integers in ``[0, map_size]``.
Each coordinate maps to a cell index, and each cell index maps to the center
coordinate ``index * cell_size + cell_size // 2``.
"""

from dataclasses import dataclass
from typing import Tuple

from settings import CONFIG


def grid_dimensions() -> int:
    """Return the number of grid cells along one axis (8 by default)."""
    return CONFIG["map_size"] // CONFIG["cell_size"]


def validate_coordinate(value, name: str = "coordinate") -> int:
    """Validate that a coordinate is an integer within the map range.

    Args:
        value: Candidate coordinate value.
        name: Label used in error messages.

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if not 0 <= value <= CONFIG["map_size"]:
        raise ValueError(
            f"{name} must be within 0-{CONFIG['map_size']}, got {value}"
        )
    return value


def to_grid_index(value: int) -> int:
    """Convert a coordinate to its grid cell index, clamped to the map.

    Args:
        value: Integer coordinate.

    Returns:
        Cell index in ``[0, dimensions - 1]``.
    """
    index = value // CONFIG["cell_size"]
    return min(index, grid_dimensions() - 1)


def cell_center(index: int) -> int:
    """Return the center coordinate of a grid cell index.

    Args:
        index: Grid cell index along one axis.

    Returns:
        ``index * cell_size + cell_size // 2``.
    """
    cell = CONFIG["cell_size"]
    return index * cell + cell // 2


@dataclass(frozen=True)
class Location:
    """A point on the map together with its grid cell.

    Attributes:
        x: X coordinate in map units.
        y: Y coordinate in map units.
        grid_x: Grid column index of the cell containing the point.
        grid_y: Grid row index of the cell containing the point.
    """

    x: int
    y: int
    grid_x: int
    grid_y: int

    @classmethod
    def from_xy(cls, x: int, y: int) -> "Location":
        """Build a location from validated map coordinates.

        Raises:
            ValueError: If either coordinate is invalid.
        """
        x = validate_coordinate(x, "x")
        y = validate_coordinate(y, "y")
        return cls(x, y, to_grid_index(x), to_grid_index(y))

    @classmethod
    def from_node(cls, col: int, row: int) -> "Location":
        """Build the location at the center of a grid node."""
        return cls(cell_center(col), cell_center(row), col, row)

    @property
    def node(self) -> Tuple[int, int]:
        """Grid node as a ``(col, row)`` tuple."""
        return (self.grid_x, self.grid_y)

    @property
    def center(self) -> Tuple[int, int]:
        """Center point of the containing grid cell as ``(x, y)``."""
        return (cell_center(self.grid_x), cell_center(self.grid_y))

    def __str__(self) -> str:
        return f"({self.x},{self.y})"
