"""Grid geometry helpers for the 8x8 food delivery map.

The map is an 800x800 coordinate system divided into 8x8 cells of 100x100
units. Streets run along the grid lines (x or y multiple of 100).
Cell centers are located at ``cell * 100 + 50``.
"""

from typing import Tuple

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = 8
CELL_CENTER_OFFSET = 50
COORD_MIN = 0
COORD_MAX = MAP_SIZE

Point = Tuple[int, int]


def validate_coordinate(value: object, name: str = "coordinate") -> int:
    """Validate that ``value`` is an integer within the map range.

    Args:
        value: The value to validate.
        name: Human readable name used in error messages.

    Returns:
        The validated integer.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if value < COORD_MIN or value > COORD_MAX:
        raise ValueError(
            f"{name} must be between {COORD_MIN} and {COORD_MAX}, got {value}"
        )
    return value


def cell_index(value: int) -> int:
    """Return the grid cell index (0-7) containing a coordinate.

    Coordinates on the far edge (800) are clamped into the last cell.

    Args:
        value: A coordinate in units.

    Returns:
        The cell index along one axis.
    """
    index = value // CELL_SIZE
    return min(max(index, 0), GRID_DIM - 1)


def to_grid_center(x: int, y: int) -> Point:
    """Convert a map coordinate to the center of its grid cell.

    Uses ``center = (cell // 100) * 100 + 50`` on each axis.

    Args:
        x: X coordinate in units.
        y: Y coordinate in units.

    Returns:
        The ``(center_x, center_y)`` tuple.
    """
    return (
        cell_index(x) * CELL_SIZE + CELL_CENTER_OFFSET,
        cell_index(y) * CELL_SIZE + CELL_CENTER_OFFSET,
    )


def manhattan(a: Point, b: Point) -> int:
    """Return the Manhattan distance between two points.

    Args:
        a: First point.
        b: Second point.

    Returns:
        The sum of absolute coordinate differences.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_street_x(x: int) -> bool:
    """Return True if a vertical line at ``x`` is a street."""
    return x % CELL_SIZE == 0


def is_street_y(y: int) -> bool:
    """Return True if a horizontal line at ``y`` is a street."""
    return y % CELL_SIZE == 0
